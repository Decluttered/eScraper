import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.evaluation import EvaluationSnapshotModel
from app.db.models.listing import ListingObservationModel
from app.db.models.market import CostProfileModel, MarketComparableModel, RiskRuleModel
from app.db.models.product import ProductModel
from app.domain.enums import ComparableStatus, ConfidenceLevel
from app.domain.finance import (
    FeeProfile,
    FinancialInputs,
    FinancialResult,
    RiskInputs,
    calculate_financials,
)
from app.domain.market import ComparableEvidence, MarketEstimationConfig
from app.domain.scoring import (
    EvaluationPolicy,
    GateMetrics,
    RecommendationInputs,
    ScoreInputs,
    calculate_score,
    recommend,
)
from app.services.market_estimation import estimate_market
from app.services.max_purchase import solve_max_purchase_price


@dataclass(frozen=True, slots=True)
class EvaluationBlocked(Exception):
    code: str


def _fee_profile(config: dict[str, object]) -> FeeProfile:
    return FeeProfile(
        platform_fee_bps=int(config.get("platform_fee_bps", 0)),
        fixed_fee_cents=int(config.get("fixed_fee_cents", 0)),
        fee_vat_bps=int(config.get("fee_vat_bps", 0)),
        fee_vat_recoverable=bool(config.get("fee_vat_recoverable", True)),
    )


def _risk_inputs(config: dict[str, object]) -> RiskInputs:
    return RiskInputs(
        return_probability_bps=int(config.get("return_probability_bps", 0)),
        expected_return_cost_cents=int(config.get("expected_return_cost_cents", 0)),
        defect_probability_bps=int(config.get("defect_probability_bps", 0)),
        expected_defect_loss_cents=int(config.get("expected_defect_loss_cents", 0)),
        fraud_probability_bps=int(config.get("fraud_probability_bps", 0)),
        expected_fraud_loss_cents=int(config.get("expected_fraud_loss_cents", 0)),
    )


def _policy(config: dict[str, object]) -> EvaluationPolicy:
    return EvaluationPolicy(
        minimum_expected_profit_cents=int(config.get("minimum_expected_profit_cents", 1500)),
        minimum_roi_bps=int(config.get("minimum_roi_bps", 1500)),
        minimum_downside_profit_cents=int(config.get("minimum_downside_profit_cents", 0)),
        risk_saturation_bps=int(config.get("risk_saturation_bps", 2000)),
    )


def _rule_matches(rule: RiskRuleModel, flags: list[str]) -> bool:
    triggers = rule.matcher.get("flags_any", []) if isinstance(rule.matcher, dict) else []
    return bool(set(triggers) & set(flags))


class EvaluationService:
    async def evaluate(
        self,
        session: AsyncSession,
        observation_id: uuid.UUID,
        cost_profile_id: uuid.UUID,
    ) -> EvaluationSnapshotModel:
        return await self._evaluate_loaded(session, observation_id, cost_profile_id)

    async def _evaluate_loaded(
        self,
        session: AsyncSession,
        observation_id: uuid.UUID,
        cost_profile_id: uuid.UUID,
    ) -> EvaluationSnapshotModel:
        observation = await session.get(ListingObservationModel, observation_id)
        if observation is None:
            raise EvaluationBlocked(code="OBSERVATION_NOT_FOUND")
        if observation.product_id is None or "UNCLEAR_VARIANT" in observation.flags:
            raise EvaluationBlocked(code="AMBIGUOUS_PRODUCT")

        product = await session.get(ProductModel, observation.product_id)
        if product is None:
            raise EvaluationBlocked(code="AMBIGUOUS_PRODUCT")

        cost_profile = await session.get(CostProfileModel, cost_profile_id)
        if cost_profile is None:
            raise EvaluationBlocked(code="COST_PROFILE_NOT_FOUND")
        config = cost_profile.configuration

        now = datetime.now(UTC)
        candidate_rules = (
            await session.scalars(
                select(RiskRuleModel).where(RiskRuleModel.effective_from <= now)
            )
        ).all()
        effective_rules = [
            rule
            for rule in candidate_rules
            if rule.effective_to is None or rule.effective_to > now
        ]
        matched_rules = [rule for rule in effective_rules if _rule_matches(rule, observation.flags)]
        blocking_rules = [
            rule
            for rule in matched_rules
            if rule.severity == "BLOCKING" and rule.required_evidence
        ]

        comparable_rows = (
            await session.scalars(
                select(MarketComparableModel).where(
                    MarketComparableModel.product_id == product.id
                )
            )
        ).all()
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
            for row in comparable_rows
        ]

        try:
            estimate = estimate_market(evidence, now, MarketEstimationConfig())

            fee = _fee_profile(config)
            risk = _risk_inputs(config)
            policy = _policy(config)
            buyer_shipping_cents = int(config.get("buyer_shipping_cents", 0))
            asking_landed_cents = observation.asking_price_cents + observation.shipping_cents

            def _financials(resale_item_price_cents: int, purchase_price_cents: int) -> FinancialResult:
                return calculate_financials(
                    FinancialInputs(
                        resale_item_price_cents=resale_item_price_cents,
                        buyer_shipping_cents=buyer_shipping_cents,
                        purchase_price_cents=purchase_price_cents,
                        outbound_shipping_cents=int(config.get("outbound_shipping_cents", 0)),
                        packaging_cents=int(config.get("packaging_cents", 0)),
                        refurbishment_cents=int(config.get("refurbishment_cents", 0)),
                        travel_cents=int(config.get("travel_cents", 0)),
                        labor_cents=int(config.get("labor_cents", 0)),
                        advertising_cents=int(config.get("advertising_cents", 0)),
                        fee=fee,
                        risk=risk,
                        tax_profile=cost_profile.tax_profile,
                        recoverable_input_vat_cents=int(
                            config.get("recoverable_input_vat_cents", 0)
                        ),
                        margin_scheme_supplier_eligible=bool(
                            config.get("margin_scheme_supplier_eligible", False)
                        ),
                    )
                )

            expected_result = _financials(estimate.expected_item_price_cents, asking_landed_cents)
            downside_result = _financials(estimate.downside_item_price_cents, asking_landed_cents)

            def _evaluate_candidate(candidate_cents: int) -> GateMetrics:
                result = _financials(estimate.downside_item_price_cents, candidate_cents)
                return GateMetrics(
                    expected_profit_cents=result.contribution_profit_cents,
                    downside_profit_cents=result.contribution_profit_cents,
                    roi_bps=result.roi_bps,
                )

            upper_bound = estimate.downside_item_price_cents + buyer_shipping_cents
            maximum_purchase_price_cents = solve_max_purchase_price(
                upper_bound, policy, _evaluate_candidate
            )

            score = calculate_score(
                ScoreInputs(
                    expected_profit_cents=expected_result.contribution_profit_cents,
                    roi_bps=expected_result.roi_bps,
                    liquidity_bps=estimate.liquidity_bps,
                    confidence=estimate.confidence,
                    risk_reserve_cents=expected_result.risk_reserve_cents,
                    expected_sale_receipts_cents=expected_result.sale_receipts_cents,
                ),
                policy,
            )
        except EvaluationBlocked:
            raise
        except Exception as exc:
            raise EvaluationBlocked(code=f"CALCULATION_ERROR:{uuid.uuid4()}") from exc

        recommendation = recommend(
            RecommendationInputs(
                asking_landed_cents=asking_landed_cents,
                maximum_purchase_price_cents=maximum_purchase_price_cents,
                confidence=estimate.confidence,
                stale=estimate.stale,
                ambiguous=False,
                blocking_risk=bool(blocking_rules),
                viable_purchase_price=maximum_purchase_price_cents >= 0,
            )
        )

        exact_sold_count = sum(
            1
            for row in evidence
            if row.status is ComparableStatus.SOLD and row.variant_match_confidence_bps == 10000
        )
        reasons = [f"{exact_sold_count} exact sold comparables"]
        if asking_landed_cents <= maximum_purchase_price_cents:
            reasons.append("asking cost is within maximum purchase price")
        else:
            reasons.append("asking cost exceeds maximum purchase price")
        if estimate.stale:
            reasons.append("market data is stale")
        if estimate.confidence is ConfidenceLevel.LOW:
            reasons.append("comparable confidence is low")
        for rule in matched_rules:
            reasons.append(rule.explanation)

        risk_severity = "BLOCKING" if blocking_rules else "ELEVATED" if matched_rules else "NONE"

        snapshot = EvaluationSnapshotModel(
            observation_id=observation.id,
            cost_profile_id=cost_profile.id,
            cost_profile_version=cost_profile.version,
            risk_rule_versions={rule.key: rule.version for rule in matched_rules},
            comparable_ids=list(estimate.comparable_ids),
            input_snapshot={
                "product_id": str(product.id),
                "asking_price_cents": observation.asking_price_cents,
                "shipping_cents": observation.shipping_cents,
                "asking_landed_cents": asking_landed_cents,
                "fee": {
                    "platform_fee_bps": fee.platform_fee_bps,
                    "fixed_fee_cents": fee.fixed_fee_cents,
                    "fee_vat_bps": fee.fee_vat_bps,
                    "fee_vat_recoverable": fee.fee_vat_recoverable,
                },
                "policy": {
                    "minimum_expected_profit_cents": policy.minimum_expected_profit_cents,
                    "minimum_roi_bps": policy.minimum_roi_bps,
                    "minimum_downside_profit_cents": policy.minimum_downside_profit_cents,
                },
            },
            downside_resale_cents=estimate.downside_item_price_cents,
            expected_resale_cents=estimate.expected_item_price_cents,
            optimistic_resale_cents=estimate.optimistic_item_price_cents,
            expected_profit_cents=expected_result.contribution_profit_cents,
            downside_profit_cents=downside_result.contribution_profit_cents,
            expected_roi_bps=expected_result.roi_bps,
            maximum_purchase_price_cents=max(0, maximum_purchase_price_cents),
            liquidity_bps=estimate.liquidity_bps,
            market_confidence=estimate.confidence,
            risk_reserve_cents=expected_result.risk_reserve_cents,
            risk_severity=risk_severity,
            score=score,
            recommendation=recommendation,
            reasons=reasons,
        )
        session.add(snapshot)
        await session.commit()
        return snapshot
