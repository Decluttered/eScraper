from datetime import UTC, datetime

from app.domain.enums import Marketplace
from app.schemas.sources import SourceEnvelope
from app.services.ingestion import IngestionService


def ebay_envelope(title: str = "RTX 3060 12GB") -> SourceEnvelope:
    return SourceEnvelope(
        source=Marketplace.EBAY_DE,
        external_id="v1|123|0",
        source_url="https://www.ebay.de/itm/123",
        captured_at=datetime(2026, 8, 27, tzinfo=UTC),
        title=title,
        description="tested",
        asking_price_cents=18000,
        shipping_cents=690,
        condition="Gebraucht",
        location_summary="Berlin",
        sale_format="FIXED_PRICE",
        metadata={"item_id": "v1|123|0"},
        import_method="EBAY_API",
    )


async def test_identical_payload_is_idempotent(session) -> None:
    first = await IngestionService().ingest(session, ebay_envelope())
    second = await IngestionService().ingest(session, ebay_envelope())

    assert first.created is True
    assert second.created is False
    assert second.raw_listing_id == first.raw_listing_id


async def test_changed_payload_creates_new_evidence(session) -> None:
    first = await IngestionService().ingest(session, ebay_envelope())
    changed = ebay_envelope(title="RTX 3060 12GB price drop")
    second = await IngestionService().ingest(session, changed)

    assert second.created is True
    assert second.raw_listing_id != first.raw_listing_id
