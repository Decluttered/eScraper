from datetime import UTC, datetime

from sqlalchemy import select

from app.db.models.listing import ListingObservationModel, RawListingModel
from app.db.models.product import ProductModel
from app.domain.enums import Condition, Marketplace, ProductCategory


async def test_observation_links_raw_evidence_to_canonical_product(session) -> None:
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
    session.add(observation)
    await session.commit()

    stored = await session.scalar(select(ListingObservationModel))
    assert stored is not None
    assert stored.product_id == product.id
    assert stored.raw_listing_id == raw.id
