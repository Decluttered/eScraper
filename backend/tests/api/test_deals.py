from datetime import UTC, datetime, timedelta

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

NOW = datetime(2026, 8, 27, tzinfo=UTC)


async def _seed_snapshot(session) -> tuple[EvaluationSnapshotModel, RawListingModel]:
    product = ProductModel(
        category=ProductCategory.GPU,
        manufacturer="NVIDIA",
        canonical_model="RTX 3060",
        variant="12GB",
        attributes={"vram_gb": 12},
    )
    session.add(product)
    await session.flush()

    raw = RawListingModel(
        source=Marketplace.EBAY_DE,
        external_id="v1|555|0",
        source_url="https://www.ebay.de/itm/555",
        captured_at=NOW,
        raw_title="RTX 3060 12GB Gaming X",
        raw_description="getestet",
        asking_price_cents=18000,
        shipping_cents=690,
        raw_condition="Gebraucht",
        location_summary="Berlin",
        payload_checksum="sha256:deal-detail-test",
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
        flags=[],
    )
    session.add(observation)
    await session.flush()

    cost_profile = CostProfileModel(
        name="default",
        version=1,
        effective_from=NOW,
        effective_to=None,
        tax_profile=TaxProfileType.SMALL_BUSINESS,
        configuration={},
    )
    session.add(cost_profile)
    await session.flush()

    snapshot = EvaluationSnapshotModel(
        observation_id=observation.id,
        cost_profile_id=cost_profile.id,
        cost_profile_version=1,
        risk_rule_versions={},
        comparable_ids=["comp-1", "comp-2"],
        input_snapshot={"asking_landed_cents": 18690},
        downside_resale_cents=24000,
        expected_resale_cents=25000,
        optimistic_resale_cents=26000,
        expected_profit_cents=3000,
        downside_profit_cents=2000,
        expected_roi_bps=1700,
        maximum_purchase_price_cents=19500,
        liquidity_bps=7000,
        market_confidence=ConfidenceLevel.MEDIUM,
        risk_reserve_cents=300,
        risk_severity="NONE",
        score=78,
        recommendation=Recommendation.BUY,
        reasons=["8 exact sold comparables", "asking cost is within maximum purchase price"],
        created_at=NOW,
    )
    session.add(snapshot)
    await session.commit()
    return snapshot, raw


async def test_deal_list_returns_only_latest_snapshot(client, session) -> None:
    snapshot, _ = await _seed_snapshot(session)

    older = EvaluationSnapshotModel(
        observation_id=snapshot.observation_id,
        cost_profile_id=snapshot.cost_profile_id,
        cost_profile_version=1,
        risk_rule_versions={},
        comparable_ids=[],
        input_snapshot={},
        downside_resale_cents=20000,
        expected_resale_cents=21000,
        optimistic_resale_cents=22000,
        expected_profit_cents=100,
        downside_profit_cents=-100,
        expected_roi_bps=100,
        maximum_purchase_price_cents=15000,
        liquidity_bps=3000,
        market_confidence=ConfidenceLevel.LOW,
        risk_reserve_cents=500,
        risk_severity="NONE",
        score=20,
        recommendation=Recommendation.WATCH,
        reasons=["stale"],
        created_at=NOW - timedelta(days=1),
    )
    session.add(older)
    await session.commit()

    response = await client.get("/api/v1/deals")

    assert response.status_code == 200
    items = response.json()
    matching = [item for item in items if item["observation_id"] == str(snapshot.observation_id)]
    assert len(matching) == 1
    assert matching[0]["evaluation_id"] == str(snapshot.id)
    assert matching[0]["recommendation"] == "BUY"


async def test_deal_detail_returns_full_evidence(client, session) -> None:
    snapshot, raw = await _seed_snapshot(session)

    response = await client.get(f"/api/v1/deals/{snapshot.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["input_snapshot"] == {"asking_landed_cents": 18690}
    assert body["comparable_ids"] == ["comp-1", "comp-2"]
    assert body["reasons"] == [
        "8 exact sold comparables",
        "asking cost is within maximum purchase price",
    ]
    assert body["maximum_purchase_price_cents"] == 19500
    assert body["expected_profit_cents"] == 3000
    assert body["downside_profit_cents"] == 2000
    assert body["confidence"] == "MEDIUM"
    assert body["recommendation"] == "BUY"
    assert body["source_url"] == raw.source_url
