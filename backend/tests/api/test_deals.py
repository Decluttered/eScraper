from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import *  # noqa: F401,F403
from app.db.models.evaluation import EvaluationSnapshotModel
from app.db.models.listing import ListingObservationModel, RawListingModel
from app.db.models.product import ProductModel
from app.db.session import get_session
from app.domain.enums import (
    Condition,
    ConfidenceLevel,
    Marketplace,
    ProductCategory,
    Recommendation,
)
from app.main import create_app


@pytest.fixture
def client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    session_holder = {}

    async def override_session():
        if "session" not in session_holder:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            async def _seed():
                from app.db.models.listing import ListingObservationModel, RawListingModel
                from app.db.models.evaluation import EvaluationSnapshotModel
                from app.db.models.product import ProductModel
                from app.db.models.market import CostProfileModel
                from app.db.models.market import MarketComparableModel
                from app.domain.enums import (
                    Condition,
                    ConfidenceLevel,
                    Marketplace,
                    ProductCategory,
                    Recommendation,
                    TaxProfileType,
                )
                from datetime import UTC, datetime
                from uuid import uuid4, UUID

                PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000012")
                async with async_sessionmaker(engine, expire_on_commit=False)() as s:
                    product = ProductModel(
                        id=PRODUCT_ID,
                        category=ProductCategory.GPU,
                        manufacturer="NVIDIA",
                        canonical_model="RTX 3060",
                        variant="12GB",
                        attributes={},
                    )
                    raw = RawListingModel(
                        source=Marketplace.EBAY_DE,
                        external_id="v1|abc|0",
                        source_url="https://www.ebay.de/itm/abc",
                        captured_at=datetime(2026, 8, 27, tzinfo=UTC),
                        raw_title="RTX 3060 12GB",
                        raw_description="tested",
                        asking_price_cents=18000,
                        shipping_cents=690,
                        raw_condition="Gebraucht",
                        location_summary="Berlin",
                        payload_checksum="sha256:deal-test",
                        import_method="EBAY_API",
                        raw_metadata={},
                    )
                    s.add_all([product, raw])
                    await s.flush()
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
                    s.add(observation)
                    await s.flush()
                    snapshot = EvaluationSnapshotModel(
                        observation_id=observation.id,
                        cost_profile_id=uuid4(),
                        cost_profile_version=1,
                        risk_rule_versions={},
                        comparable_ids=["sold-1", "sold-2"],
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
                    s.add(snapshot)
                    await s.commit()
                    session_holder["observation_id"] = str(observation.id)
                    session_holder["evaluation_id"] = str(snapshot.id)

            import asyncio
            asyncio.get_event_loop().run_until_complete(_seed())
        async with async_sessionmaker(engine, expire_on_commit=False)() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def test_list_deals_returns_latest_snapshot(client: TestClient) -> None:
    response = client.get("/api/v1/deals")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["recommendation"] == "NEGOTIATE"
    assert data[0]["score"] == 81


def test_deal_detail_returns_complete_snapshot(client: TestClient) -> None:
    evaluation_id = client.get("/api/v1/deals").json()[0]["evaluation_id"]
    response = client.get(f"/api/v1/deals/{evaluation_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["maximum_purchase_price_cents"] == 17200
    assert data["expected_profit_cents"] == 4100
    assert data["comparable_ids"] == ["sold-1", "sold-2"]
    assert "8 exact sold comparables" in data["reasons"]
