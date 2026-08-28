from datetime import UTC, datetime, timedelta

import pytest

from app.db.models.listing import ListingObservationModel, RawListingModel
from app.db.models.market import CostProfileModel, MarketComparableModel, RiskRuleModel
from app.db.models.product import ProductModel
from app.domain.enums import (
    ComparableStatus,
    Condition,
    ConfidenceLevel,
    Marketplace,
    ProductCategory,
    Recommendation,
    TaxProfileType,
)
from app.services.evaluation import EvaluationBlocked, EvaluationService

NOW = datetime(2026, 8, 27, tzinfo=UTC)

SMALL_BUSINESS_CONFIG = {
    "platform_fee_bps": 500,
    "fixed_fee_cents": 45,
    "fee_vat_bps": 1900,
    "fee_vat_recoverable": False,
    "outbound_shipping_cents": 690,
    "packaging_cents": 200,
    "labor_cents": 1000,
    "buyer_shipping_cents": 690,
    "return_probability_bps": 500,
    "expected_return_cost_cents": 1000,
    "defect_probability_bps": 300,
    "expected_defect_loss_cents": 5000,
    "fraud_probability_bps": 100,
    "expected_fraud_loss_cents": 10000,
    "minimum_expected_profit_cents": 1500,
    "minimum_roi_bps": 1500,
    "minimum_downside_profit_cents": 0,
    "risk_saturation_bps": 2000,
}


async def _seed_product(session) -> ProductModel:
    product = ProductModel(
        category=ProductCategory.GPU,
        manufacturer="NVIDIA",
        canonical_model="RTX 3060",
        variant="12GB",
        attributes={"vram_gb": 12},
    )
    session.add(product)
    await session.flush()
    return product


async def _seed_observation(
    session, product: ProductModel, flags: list[str] | None = None
) -> ListingObservationModel:
    raw = RawListingModel(
        source=Marketplace.EBAY_DE,
        external_id="v1|999|0",
        source_url="https://www.ebay.de/itm/999",
        captured_at=NOW,
        raw_title="RTX 3060 12GB",
        raw_description="getestet",
        asking_price_cents=18000,
        shipping_cents=690,
        raw_condition="Gebraucht",
        location_summary="Berlin",
        payload_checksum="sha256:eval-test",
        import_method="EBAY_API",
        raw_metadata={},
    )
    session.add(raw)
    await session.flush()
    observation = ListingObservationModel(
        raw_listing_id=raw.id,
        product_id=product.id,
        asking_price_cents=18000,
        shipping_cents=690,
        condition=Condition.USED,
        sale_format="FIXED_PRICE",
        model_match_confidence_bps=10000,
        flags=flags or [],
    )
    session.add(observation)
    await session.flush()
    return observation


async def _seed_cost_profile(session, config: dict[str, object] | None = None) -> CostProfileModel:
    cost_profile = CostProfileModel(
        name="default",
        version=1,
        effective_from=NOW - timedelta(days=1),
        effective_to=None,
        tax_profile=TaxProfileType.SMALL_BUSINESS,
        configuration=config if config is not None else dict(SMALL_BUSINESS_CONFIG),
    )
    session.add(cost_profile)
    await session.flush()
    return cost_profile


def _sold_comparable(
    product_id, item_price_cents: int, age_days: int = 5, exact: bool = True
) -> MarketComparableModel:
    return MarketComparableModel(
        product_id=product_id,
        source=Marketplace.EBAY_DE,
        status=ComparableStatus.SOLD,
        condition=Condition.USED,
        item_price_cents=item_price_cents,
        shipping_cents=690,
        occurred_at=NOW - timedelta(days=age_days),
        variant_match_confidence_bps=10000 if exact else 6000,
        source_quality="AUTHORIZED_EXPORT",
        observation_count=1,
        sold_through_bps=7000,
    )


async def test_profitable_medium_confidence_offer_is_recommended_buy(session) -> None:
    product = await _seed_product(session)
    observation = await _seed_observation(session, product)
    cost_profile = await _seed_cost_profile(session)
    session.add_all(_sold_comparable(product.id, 25000) for _ in range(8))
    await session.flush()

    snapshot = await EvaluationService().evaluate(session, observation.id, cost_profile.id)

    assert snapshot.recommendation is Recommendation.BUY
    assert len(snapshot.comparable_ids) == 8
    assert snapshot.cost_profile_version == 1
    assert snapshot.downside_profit_cents >= 0
    assert "8 exact sold comparables" in snapshot.reasons
    assert "asking cost is within maximum purchase price" in snapshot.reasons


async def test_missing_product_blocks_evaluation_without_snapshot(session) -> None:
    product = await _seed_product(session)
    observation = await _seed_observation(session, product)
    observation.product_id = None
    await session.flush()
    cost_profile = await _seed_cost_profile(session)

    with pytest.raises(EvaluationBlocked) as excinfo:
        await EvaluationService().evaluate(session, observation.id, cost_profile.id)

    assert excinfo.value.code == "AMBIGUOUS_PRODUCT"


async def test_low_comparable_confidence_caps_at_watch(session) -> None:
    product = await _seed_product(session)
    observation = await _seed_observation(session, product)
    cost_profile = await _seed_cost_profile(session)
    session.add_all(_sold_comparable(product.id, 25000) for _ in range(3))
    await session.flush()

    snapshot = await EvaluationService().evaluate(session, observation.id, cost_profile.id)

    assert snapshot.market_confidence is ConfidenceLevel.LOW
    assert snapshot.recommendation is Recommendation.WATCH


async def test_stale_comparables_cap_at_watch(session) -> None:
    product = await _seed_product(session)
    observation = await _seed_observation(session, product)
    cost_profile = await _seed_cost_profile(session)
    session.add_all(_sold_comparable(product.id, 25000, age_days=40) for _ in range(8))
    await session.flush()

    snapshot = await EvaluationService().evaluate(session, observation.id, cost_profile.id)

    assert snapshot.recommendation is Recommendation.WATCH


async def test_blocking_risk_evidence_rejects_offer(session) -> None:
    product = await _seed_product(session)
    observation = await _seed_observation(session, product, flags=["DEFECTIVE"])
    cost_profile = await _seed_cost_profile(session)
    session.add_all(_sold_comparable(product.id, 25000) for _ in range(8))
    session.add(
        RiskRuleModel(
            key="gpu_defect_evidence",
            version=1,
            effective_from=NOW - timedelta(days=1),
            effective_to=None,
            matcher={"flags_any": ["DEFECTIVE"]},
            severity="BLOCKING",
            required_evidence=["repair_invoice"],
            reserve_adjustment_bps=0,
            recommendation_cap="REJECT",
            explanation="Defective GPU requires documented repair evidence",
        )
    )
    await session.flush()

    snapshot = await EvaluationService().evaluate(session, observation.id, cost_profile.id)

    assert snapshot.recommendation is Recommendation.REJECT
    assert snapshot.risk_severity == "BLOCKING"


async def test_calculation_failure_is_blocked_with_diagnostic_code(session) -> None:
    product = await _seed_product(session)
    observation = await _seed_observation(session, product)
    config = dict(SMALL_BUSINESS_CONFIG)
    cost_profile = await _seed_cost_profile(session, config)
    cost_profile.tax_profile = TaxProfileType.MARGIN_SCHEME
    session.add_all(_sold_comparable(product.id, 25000) for _ in range(8))
    await session.flush()

    with pytest.raises(EvaluationBlocked) as excinfo:
        await EvaluationService().evaluate(session, observation.id, cost_profile.id)

    assert excinfo.value.code.startswith("CALCULATION_ERROR:")
