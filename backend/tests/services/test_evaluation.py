from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.db.models.evaluation import EvaluationSnapshotModel
from app.db.models.listing import ListingObservationModel, RawListingModel
from app.db.models.market import CostProfileModel, MarketComparableModel
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

PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000012")
CAPTURED_AT = datetime(2026, 8, 27, tzinfo=UTC)
NOW = datetime(2026, 8, 27, tzinfo=UTC)


async def _seed_listing(session) -> tuple[RawListingModel, ListingObservationModel]:
    product = ProductModel(
        id=PRODUCT_ID,
        category=ProductCategory.GPU,
        manufacturer="NVIDIA",
        canonical_model="RTX 3060",
        variant="12GB",
        attributes={"vram_gb": 12},
    )
    raw = RawListingModel(
        source=Marketplace.EBAY_DE,
        external_id="v1|999|0",
        source_url="https://www.ebay.de/itm/999",
        captured_at=CAPTURED_AT,
        raw_title="RTX 3060 12GB",
        raw_description="tested working",
        asking_price_cents=18000,
        shipping_cents=690,
        raw_condition="Gebraucht",
        location_summary="Berlin",
        payload_checksum="sha256:eval-test",
        import_method="EBAY_API",
        raw_metadata={},
    )
    observation = ListingObservationModel(
        raw_listing_id=raw.id,
        product_id=product.id,
        asking_price_cents=18000,
        shipping_cents=690,
        condition=Condition.USED,
        sale_format="FIXED_PRICE",
        model_match_confidence_bps=10000,
        flags=[],
        review_status="RESOLVED",
    )
    session.add_all([product, raw])
    await session.flush()
    session.add(observation)
    return raw, observation


async def _seed_comparables(session, count: int = 8) -> None:
    for index in range(count):
        session.add(
            MarketComparableModel(
                product_id=PRODUCT_ID,
                source=Marketplace.EBAY_DE,
                status=ComparableStatus.SOLD,
                condition=Condition.USED,
                item_price_cents=24000 + index * 100,
                shipping_cents=690,
                occurred_at=NOW - timedelta(days=10 + index),
                variant_match_confidence_bps=10000,
                source_quality="PRODUCT_RESEARCH",
                observation_count=1,
                sold_through_bps=7000,
                source_note="authorized import",
            )
        )


async def _seed_cost_profile(session) -> CostProfileModel:
    profile = CostProfileModel(
        name="small-business-default",
        version=1,
        effective_from=CAPTURED_AT,
        effective_to=None,
        tax_profile=TaxProfileType.SMALL_BUSINESS,
        configuration={
            "platform_fee_bps": 500,
            "fixed_fee_cents": 45,
            "fee_vat_bps": 0,
            "fee_vat_recoverable": True,
            "return_probability_bps": 200,
            "expected_return_cost_cents": 1000,
            "defect_probability_bps": 100,
            "expected_defect_loss_cents": 2000,
            "fraud_probability_bps": 50,
            "expected_fraud_loss_cents": 5000,
            "outbound_shipping_cents": 690,
            "packaging_cents": 200,
            "labor_cents": 500,
            "minimum_expected_profit_cents": 1000,
            "minimum_roi_bps": 1000,
            "minimum_downside_profit_cents": 0,
            "risk_saturation_bps": 2000,
        },
    )
    session.add(profile)
    await session.flush()
    return profile


async def test_profitable_offer_evaluates_to_buy(session) -> None:
    raw, observation = await _seed_listing(session)
    await _seed_comparables(session, count=8)
    profile = await _seed_cost_profile(session)
    await session.commit()

    snapshot = await EvaluationService().evaluate(session, observation.id, profile.id)

    assert snapshot.recommendation is Recommendation.BUY
    assert len(snapshot.comparable_ids) == 8
    assert snapshot.cost_profile_version == 1
    assert snapshot.downside_profit_cents >= 0
    assert "8 exact sold comparables" in snapshot.reasons
    assert "asking cost is within maximum purchase price" in snapshot.reasons


async def test_ambiguous_product_raises_blocked(session) -> None:
    raw, observation = await _seed_listing(session)
    observation.product_id = None
    observation.model_match_confidence_bps = 0
    profile = await _seed_cost_profile(session)
    await session.commit()

    with pytest.raises(EvaluationBlocked, match="AMBIGUOUS_PRODUCT"):
        await EvaluationService().evaluate(session, observation.id, profile.id)

    stored = await session.scalar(EvaluationSnapshotModel.__table__.select())
    assert stored is None


async def test_low_confidence_caps_at_watch(session) -> None:
    raw, observation = await _seed_listing(session)
    # Only 3 comparables → low confidence
    await _seed_comparables(session, count=3)
    profile = await _seed_cost_profile(session)
    await session.commit()

    snapshot = await EvaluationService().evaluate(session, observation.id, profile.id)

    assert snapshot.recommendation is Recommendation.WATCH
    assert snapshot.market_confidence is ConfidenceLevel.LOW
