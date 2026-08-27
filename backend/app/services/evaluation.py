from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.evaluation import EvaluationSnapshotModel


@dataclass(frozen=True, slots=True)
class EvaluationBlocked(Exception):
    code: str


class EvaluationService:
    async def evaluate(
        self,
        session: AsyncSession,
        observation_id: UUID,
        cost_profile_id: UUID,
    ) -> EvaluationSnapshotModel:
        return await self._evaluate_loaded(session, observation_id, cost_profile_id)

    async def _evaluate_loaded(
        self,
        session: AsyncSession,
        observation_id: UUID,
        cost_profile_id: UUID,
    ) -> EvaluationSnapshotModel:
        from datetime import UTC, datetime

        from sqlalchemy import select

        from app.db.models.listing import ListingObservationModel, RawListingModel
        from app.db.models.market import CostProfileModel, MarketComparableModel
        from app.db.models.product import ProductModel
        from app.domain.enums import (
            ComparableStatus,
            ConfidenceLevel,
            Marketplace,
            Recommendation,
        )
        from app.domain.finance import (
            FeeProfile,
            FinancialInputs,
            RiskInputs,
            calculate_financials,
        )
        from app.domain.market import ComparableEvidence, MarketEstimationConfig, estimate_market
        from app.domain.scoring import (
            EvaluationPolicy,
            GateMetrics,
            RecommendationInputs,
            ScoreInputs,
            calculate_score,
            recommend,
        )
        from app.services.max_purchase import solve_max_purchase_price

        observation = await session.scalar(
            select(ListingObservationModel).where(ListingObservationModel.id == observation_id)
        )
        if observation is None:
            raise EvaluationBlocked(code="OBSERVATION_NOT_FOUND")
        if observation.product_id is None or observation.model_match_confidence_bps < 5000:
            raise EvaluationBlocked(code="AMBIGUOUS_PRODUCT")

        cost_profile = await session.scalar(
            select(CostProfileModel).where(CostProfileModel.id == cost_profile_id)
        )
        if cost_profile is None:
            raise EvaluationBlocked(code="COST_PROFILE_NOT_FOUND")

        product = await session.scalar(
            select(ProductModel).where(ProductModel.id == observation.product_id)
        )
        if product is None:
            raise EvaluationBlocked(code="PRODUCT_NOT_FOUND")

        raw = await session.scalar(
            select(RawListingModel).where(RawListingModel.id == observation.raw_listing_id)
        )
        if raw is None:
            raise EvaluationBlocked(code="RAW_LISTING_NOT_FOUND")

        comparables = (
            await session.scalars(
                select(MarketComparableModel).where(
                    MarketComparableModel.product_id == observation.product_id
                )
            )
        ).all()

        now = datetime.now(UTC)
        evidence = [
            ComparableEvidence(
                id=str(row.id),
                product_id=row.product_id,
                status=row.status,
                condition=row.condition,
                item_price_cents=row.item_price_cents,
                shipping_cents=row.shipping_cents,
                occurred_at=row.occurred_at,
                variant_match_confidence_bps=row.variant_match_confidence_bps,
                observation_count=row.observation_count,
                sold_through_bps=row.sold_through_bps,
            )
            for row in comparables
        ]
        market = estimate_market(evidence, now, MarketEstimationConfig())

        fee_config = cost_profile.configuration
        fee = FeeProfile(
            platform_fee_bps=int(fee_config.get("platform_fee_bps", 0)),
            fixed_fee_cents=int(fee_config.get("fixed_fee_cents", 0)),
            fee_vat_bps=int(fee_config.get("fee_vat_bps", 0)),
            fee_vat_recoverable=bool(fee_config.get("fee_vat_recoverable", True)),
        )
        risk = RiskInputs(
            return_probability_bps=int(fee_config.get("return_probability_bps", 0)),
            expected_return_cost_cents=int(fee_config.get("expected_return_cost_cents", 0)),
            defect_probability_bps=int(fee_config.get("defect_probability_bps", 0)),
            expected_defect_loss_cents=int(fee_config.get("expected_defect_loss_cents", 0)),
            fraud_probability_bps=int(fee_config.get("fraud_probability_bps", 0)),
            expected_fraud_loss_cents=int(fee_config.get("expected_fraud_loss_cents", 0)),
        )

        asking_landed = observation.asking_price_cents + observation.shipping_cents

        def _build_inputs(resale_cents: int, purchase_cents: int) -> FinancialInputs:
            return FinancialInputs(
                resale_item_price_cents=resale_cents,
                buyer_shipping_cents=0,
                purchase_price_cents=purchase_cents,
                outbound_shipping_cents=int(fee_config.get("outbound_shipping_cents", 0)),
                packaging_cents=int(fee_config.get("packaging_cents", 0)),
                refurbishment_cents=int(fee_config.get("refurbishment_cents", 0)),
                travel_cents=int(fee_config.get("travel_cents", 0)),
                labor_cents=int(fee_config.get("labor_cents", 0)),
                advertising_cents=int(fee_config.get("advertising_cents", 0)),
                fee=fee,
                risk=risk,
                tax_profile=cost_profile.tax_profile,
                recoverable_input_vat_cents=int(fee_config.get("recoverable_input_vat_cents", 0)),
                margin_scheme_supplier_eligible=bool(
                    fee_config.get("margin_scheme_supplier_eligible", False)
                ),
            )

        policy = EvaluationPolicy(
            minimum_expected_profit_cents=int(fee_config.get("minimum_expected_profit_cents", 1500)),
            minimum_roi_bps=int(fee_config.get("minimum_roi_bps", 1500)),
            minimum_downside_profit_cents=int(fee_config.get("minimum_downside_profit_cents", 0)),
            risk_saturation_bps=int(fee_config.get("risk_saturation_bps", 2000)),
        )

        expected_financials = calculate_financials(
            _build_inputs(market.expected_item_price_cents, asking_landed)
        )
        downside_financials = calculate_financials(
            _build_inputs(market.downside_item_price_cents, asking_landed)
        )

        def _evaluate_at(purchase_cents: int) -> GateMetrics:
            result = calculate_financials(
                _build_inputs(market.downside_item_price_cents, purchase_cents)
            )
            return GateMetrics(
                expected_profit_cents=result.contribution_profit_cents,
                downside_profit_cents=result.contribution_profit_cents,
                roi_bps=result.roi_bps,
            )

        maximum_purchase = solve_max_purchase_price(
            market.downside_item_price_cents, policy, _evaluate_at
        )
        viable = maximum_purchase >= 0

        recommendation_inputs = RecommendationInputs(
            asking_landed_cents=asking_landed,
            maximum_purchase_price_cents=max(0, maximum_purchase),
            confidence=market.confidence,
            stale=market.stale,
            ambiguous=False,
            blocking_risk=False,
            viable_purchase_price=viable,
        )
        recommendation = recommend(recommendation_inputs)

        score_inputs = ScoreInputs(
            expected_profit_cents=expected_financials.contribution_profit_cents,
            roi_bps=expected_financials.roi_bps,
            liquidity_bps=market.liquidity_bps,
            confidence=market.confidence,
            risk_reserve_cents=expected_financials.risk_reserve_cents,
            expected_sale_receipts_cents=expected_financials.sale_receipts_cents,
        )
        score = calculate_score(score_inputs, policy)

        exact_sold_count = sum(
            1
            for row in comparables
            if row.status is ComparableStatus.SOLD
            and row.variant_match_confidence_bps == 10000
        )

        reasons: list[str] = []
        if exact_sold_count > 0:
            reasons.append(f"{exact_sold_count} exact sold comparables")
        if viable and asking_landed <= maximum_purchase:
            reasons.append("asking cost is within maximum purchase price")
        if market.stale:
            reasons.append("market data is stale")
        if market.confidence is ConfidenceLevel.LOW:
            reasons.append("low market confidence")

        snapshot = EvaluationSnapshotModel(
            observation_id=observation.id,
            cost_profile_id=cost_profile.id,
            cost_profile_version=cost_profile.version,
            risk_rule_versions={},
            comparable_ids=list(market.comparable_ids),
            input_snapshot={
                "asking_price_cents": observation.asking_price_cents,
                "shipping_cents": observation.shipping_cents,
                "source": raw.source.value,
            },
            downside_resale_cents=market.downside_item_price_cents,
            expected_resale_cents=market.expected_item_price_cents,
            optimistic_resale_cents=market.optimistic_item_price_cents,
            expected_profit_cents=expected_financials.contribution_profit_cents,
            downside_profit_cents=downside_financials.contribution_profit_cents,
            expected_roi_bps=expected_financials.roi_bps,
            maximum_purchase_price_cents=max(0, maximum_purchase),
            liquidity_bps=market.liquidity_bps,
            market_confidence=market.confidence,
            risk_reserve_cents=expected_financials.risk_reserve_cents,
            risk_severity="LOW",
            score=score,
            recommendation=recommendation,
            reasons=reasons,
        )
        session.add(snapshot)
        await session.commit()
        return snapshot
