from datetime import UTC, datetime, timedelta

from app.db.models.evaluation import EvaluationSnapshotModel
from app.db.models.listing import ListingObservationModel, RawListingModel
from app.db.models.market import CostProfileModel
from app.db.models.operations import AlertModel, JobRunModel
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

WATCHLIST = {
    "name": "RTX 3060 12GB Berlin",
    "marketplace": "EBAY_DE",
    "category": "GPU",
    "include_terms": ["rtx 3060", "12gb"],
    "exclude_terms": ["ti", "8gb", "defekt", "ovp"],
    "filters": {"pickup_postal_code": "10115", "pickup_radius_km": 100},
    "polling_interval_seconds": 900,
    "enabled": True,
}


async def test_watchlist_create_validates_minimum_polling_interval(client) -> None:
    created = await client.post("/api/v1/watchlists", json=WATCHLIST)
    assert created.status_code == 201

    rejected = await client.post(
        "/api/v1/watchlists", json={**WATCHLIST, "name": "other", "polling_interval_seconds": 60}
    )
    assert rejected.status_code == 422


async def test_watchlist_create_rejects_duplicate_name(client) -> None:
    first = await client.post("/api/v1/watchlists", json=WATCHLIST)
    second = await client.post("/api/v1/watchlists", json=WATCHLIST)

    assert first.status_code == 201
    assert second.status_code == 409


async def test_watchlist_enable_disable_round_trip(client) -> None:
    created = (await client.post("/api/v1/watchlists", json=WATCHLIST)).json()

    disabled = await client.post(f"/api/v1/watchlists/{created['id']}/disable")
    assert disabled.json()["enabled"] is False

    enabled = await client.post(f"/api/v1/watchlists/{created['id']}/enable")
    assert enabled.json()["enabled"] is True


async def test_settings_report_credential_status_without_secret_values(client) -> None:
    response = await client.get("/api/v1/settings")

    assert response.status_code == 200
    settings = response.json()
    assert settings["ebay_client_id"] in {"SET", "EMPTY", "MISSING"}
    assert settings["ebay_client_secret"] in {"SET", "EMPTY", "MISSING"}
    assert "secret_value" not in str(settings)


async def test_settings_cost_profile_versions_increment(client) -> None:
    payload = {
        "name": "default",
        "effective_from": "2026-08-01T00:00:00Z",
        "effective_to": None,
        "tax_profile": "SMALL_BUSINESS",
        "configuration": {"platform_fee_bps": 500},
    }

    first = await client.post("/api/v1/settings/cost-profiles", json=payload)
    second = await client.post("/api/v1/settings/cost-profiles", json=payload)

    assert first.json()["version"] == 1
    assert second.json()["version"] == 2


async def _seed_inventory_source(session) -> tuple[ProductModel, ListingObservationModel]:
    product = ProductModel(
        category=ProductCategory.GPU,
        manufacturer="NVIDIA",
        canonical_model="RTX 3060",
        variant="12GB",
        attributes={},
    )
    session.add(product)
    await session.flush()

    raw = RawListingModel(
        source=Marketplace.EBAY_DE,
        external_id="v1|777|0",
        source_url="https://www.ebay.de/itm/777",
        captured_at=NOW,
        raw_title="RTX 3060 12GB",
        raw_description="getestet",
        asking_price_cents=18000,
        shipping_cents=690,
        raw_condition="Gebraucht",
        location_summary="Berlin",
        payload_checksum="sha256:inventory-test",
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
        review_status="RESOLVED",
    )
    session.add(observation)
    await session.commit()
    return product, observation


async def test_inventory_item_and_test_run_lifecycle(client, session) -> None:
    product, observation = await _seed_inventory_source(session)

    created = await client.post(
        "/api/v1/inventory",
        json={
            "product_id": str(product.id),
            "source_observation_id": str(observation.id),
            "serial_number": "SN-12345",
            "acquisition_price_cents": 18690,
            "acquisition_costs": {"cleaning": 500},
            "condition_notes": "leichte Gebrauchsspuren",
        },
    )
    assert created.status_code == 201
    inventory_item_id = created.json()["id"]

    test_run = await client.post(
        f"/api/v1/inventory/{inventory_item_id}/test-runs",
        json={
            "procedure_name": "FurMark stress test",
            "tool_name": "FurMark",
            "duration_seconds": 900,
            "configuration": {"resolution": "1080p"},
            "result": "PASS",
            "measured_values": {"max_temp_c": 78},
            "notes": "keine Artefakte",
            "evidence_paths": ["evidence/furmark-1.png"],
        },
    )
    assert test_run.status_code == 201
    assert test_run.json()["inventory_item_id"] == inventory_item_id

    listed = await client.get(f"/api/v1/inventory/{inventory_item_id}/test-runs")
    assert len(listed.json()) == 1
    assert listed.json()[0]["result"] == "PASS"


async def test_alert_list_and_acknowledge(client, session) -> None:
    _product, observation = await _seed_inventory_source(session)
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
        comparable_ids=[],
        input_snapshot={},
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
        reasons=[],
    )
    session.add(snapshot)
    await session.flush()

    alert = AlertModel(evaluation_id=snapshot.id, alert_type="NEW_BUY_CANDIDATE")
    session.add(alert)
    await session.commit()

    listed = await client.get("/api/v1/alerts")
    assert len(listed.json()) == 1

    acknowledged = await client.post(f"/api/v1/alerts/{alert.id}/acknowledge")
    assert acknowledged.json()["acknowledged_at"] is not None

    listed_again = await client.get("/api/v1/alerts")
    assert listed_again.json() == []


async def test_source_health_reports_aggregate_counts(client, session) -> None:
    session.add(
        JobRunModel(
            idempotency_key="poll:watchlist-1:2026-08-27T10:00",
            job_type="POLL_EBAY",
            status="SUCCEEDED",
            attempts=1,
            finished_at=NOW,
        )
    )
    session.add(
        JobRunModel(
            idempotency_key="poll:watchlist-1:2026-08-27T10:15",
            job_type="POLL_EBAY",
            status="FAILED",
            attempts=5,
            last_error_code="EBAY_AUTH",
            last_error_message="authentication failed",
            finished_at=NOW + timedelta(minutes=15),
        )
    )
    await session.commit()

    response = await client.get("/api/v1/source-health")

    assert response.status_code == 200
    body = response.json()
    assert body["last_success_at"] is not None
    assert body["failed_job_count"] == 1
    assert "quota_remaining" in body
    assert "stale_estimate_count" in body
    assert "review_queue_count" in body
