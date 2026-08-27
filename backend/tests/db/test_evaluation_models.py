from datetime import UTC, datetime

from sqlalchemy import select

from app.db.models.evaluation import EvaluationSnapshotModel
from app.db.models.listing import ListingObservationModel, RawListingModel
from app.db.models.market import CostProfileModel
from app.db.models.product import ProductModel
from app.domain.enums import (
    Condition,
    ConfidenceLevel,
    Marketplace,
    ProductCategory,
    Recommendation,
    TaxProfileType,
)


async def test_evaluation_snapshot_retains_versions_and_results(session) -> None:
    product = ProductModel(
        category=ProductCategory.GPU,
        manufacturer="NVIDIA",
        canonical_model="RTX 3060",
        variant="12GB",
        attributes={"vram_gb": 12},
    )
    raw = RawListingModel(
        source=Marketplace.EBAY_DE,
        external_id="v1|123|0",
        source_url="https://www.ebay.de/itm/123",
        captured_at=datetime(2026, 8, 27, tzinfo=UTC),
        raw_title="RTX 3060 12GB",
        raw_description="tested",
        asking_price_cents=18000,
        shipping_cents=690,
        raw_condition="Gebraucht",
        location_summary="Berlin",
        payload_checksum="sha256:one",
        import_method="EBAY_API",
        raw_metadata={},
    )
    session.add_all([product, raw])
    await session.flush()
    observation = ListingObservationModel(
        raw_listing_id=raw.id,
        product_id=product.id,
        asking_price_cents=18000,
        shipping_cents=690,
        condition=Condition.USED,
        sale_format="FIXED_PRICE",
        model_match_confidence_bps=10000,
        flags=[],
    )
    cost_profile = CostProfileModel(
        name="small-business-default",
        version=1,
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        effective_to=None,
        tax_profile=TaxProfileType.SMALL_BUSINESS,
        configuration={"platform_fee_bps": 500},
    )
    session.add_all([observation, cost_profile])
    await session.flush()

    snapshot = EvaluationSnapshotModel(
        observation_id=observation.id,
        cost_profile_id=cost_profile.id,
        cost_profile_version=1,
        risk_rule_versions={"gpu_shipping": 1},
        comparable_ids=[],
        input_snapshot={"asking_price_cents": 18000},
        downside_resale_cents=22000,
        expected_resale_cents=25000,
        optimistic_resale_cents=28000,
        expected_profit_cents=4100,
        downside_profit_cents=1400,
        expected_roi_bps=2278,
        maximum_purchase_price_cents=17200,
        liquidity_bps=7000,
        market_confidence=ConfidenceLevel.MEDIUM,
        risk_reserve_cents=300,
        risk_severity="LOW",
        score=81,
        recommendation=Recommendation.NEGOTIATE,
        reasons=["8 exact sold comparables"],
    )
    session.add(snapshot)
    await session.commit()

    stored = await session.scalar(select(EvaluationSnapshotModel))
    assert stored is not None
    assert stored.cost_profile_version == 1
    assert stored.risk_rule_versions == {"gpu_shipping": 1}
    assert stored.comparable_ids == []
    assert stored.expected_profit_cents == 4100
    assert stored.downside_profit_cents == 1400
    assert stored.maximum_purchase_price_cents == 17200
    assert stored.score == 81
    assert stored.recommendation is Recommendation.NEGOTIATE
