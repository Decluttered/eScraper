from sqlalchemy import select

from app.db.models.operations import InventoryItemModel, TestRunModel, WatchlistModel
from app.db.models.product import ProductModel
from app.domain.enums import Marketplace, ProductCategory


async def test_watchlist_persists_include_and_exclude_terms(session) -> None:
    watchlist = WatchlistModel(
        name="RTX 3060 12GB Berlin",
        marketplace=Marketplace.EBAY_DE,
        category=ProductCategory.GPU,
        include_terms=["rtx 3060", "12gb"],
        exclude_terms=["ti", "defekt", "ovp"],
        filters={"pickup_postal_code": "10115"},
        polling_interval_seconds=900,
        enabled=True,
    )
    session.add(watchlist)
    await session.commit()

    stored = await session.scalar(select(WatchlistModel))
    assert stored is not None
    assert stored.include_terms == ["rtx 3060", "12gb"]
    assert stored.exclude_terms == ["ti", "defekt", "ovp"]
    assert stored.polling_interval_seconds == 900
    assert stored.enabled is True


async def test_inventory_item_and_test_run_survive_reload(session) -> None:
    product = ProductModel(
        category=ProductCategory.GPU,
        manufacturer="NVIDIA",
        canonical_model="RTX 3060",
        variant="12GB",
        attributes={"vram_gb": 12},
    )
    session.add(product)
    await session.flush()

    inventory_item = InventoryItemModel(
        product_id=product.id,
        source_observation_id=None,
        serial_number="GPU-SERIAL-001",
        acquisition_price_cents=18000,
        acquisition_costs={"shipping_cents": 690},
        condition_notes="tested working",
        disposition="IN_STOCK",
    )
    session.add(inventory_item)
    await session.flush()

    test_run = TestRunModel(
        inventory_item_id=inventory_item.id,
        procedure_name="furmark_stress",
        tool_name="FurMark",
        duration_seconds=900,
        configuration={"resolution": "1080p"},
        result="PASS",
        measured_values={"max_temp_c": 78},
        notes="no artifacts observed",
        evidence_paths=["evidence/gpu-001-furmark.log"],
    )
    session.add(test_run)
    await session.commit()

    stored_item = await session.scalar(select(InventoryItemModel))
    stored_run = await session.scalar(select(TestRunModel))
    assert stored_item is not None
    assert stored_item.serial_number == "GPU-SERIAL-001"
    assert stored_item.acquisition_price_cents == 18000
    assert stored_run is not None
    assert stored_run.procedure_name == "furmark_stress"
    assert stored_run.duration_seconds == 900
    assert stored_run.measured_values == {"max_temp_c": 78}
