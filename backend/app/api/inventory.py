import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.operations import InventoryItemModel, TestRunModel
from app.db.session import get_session
from app.schemas.operations import InventoryCreate, TestRunCreate

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("", response_model=list[dict])
async def list_inventory(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict]:
    items = (await session.scalars(select(InventoryItemModel))).all()
    return [
        {
            "id": str(item.id),
            "product_id": str(item.product_id),
            "serial_number": item.serial_number,
            "acquisition_price_cents": item.acquisition_price_cents,
            "disposition": item.disposition,
        }
        for item in items
    ]


@router.post("", status_code=201)
async def create_inventory_item(
    payload: InventoryCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    item = InventoryItemModel(
        product_id=payload.product_id,
        serial_number=payload.serial_number,
        acquisition_price_cents=payload.acquisition_price_cents,
        acquisition_costs=payload.acquisition_costs,
        condition_notes=payload.condition_notes,
        disposition="IN_STOCK",
    )
    session.add(item)
    await session.commit()
    return {"id": str(item.id)}


@router.post("/{item_id}/tests", status_code=201)
async def append_test_run(
    item_id: uuid.UUID,
    payload: TestRunCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    item = await session.scalar(
        select(InventoryItemModel).where(InventoryItemModel.id == item_id)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="inventory item not found")
    test_run = TestRunModel(
        inventory_item_id=item.id,
        procedure_name=payload.procedure_name,
        tool_name=payload.tool_name,
        duration_seconds=payload.duration_seconds,
        configuration=payload.configuration,
        result=payload.result,
        measured_values=payload.measured_values,
        notes=payload.notes,
        evidence_paths=payload.evidence_paths,
    )
    session.add(test_run)
    await session.commit()
    return {"id": str(test_run.id)}
