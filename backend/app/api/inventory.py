from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.operations import InventoryItemModel, TestRunModel
from app.db.session import get_session
from app.schemas.operations import InventoryCreate, InventoryOut, TestRunCreate, TestRunOut

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("", response_model=list[InventoryOut])
async def list_inventory(
    session: AsyncSession = Depends(get_session),
) -> list[InventoryItemModel]:
    rows = (
        await session.scalars(
            select(InventoryItemModel).order_by(InventoryItemModel.created_at.desc())
        )
    ).all()
    return list(rows)


@router.post("", response_model=InventoryOut, status_code=201)
async def create_inventory_item(
    payload: InventoryCreate, session: AsyncSession = Depends(get_session)
) -> InventoryItemModel:
    item = InventoryItemModel(**payload.model_dump())
    session.add(item)
    await session.commit()
    return item


async def _get_inventory_item_or_404(
    session: AsyncSession, inventory_item_id: UUID
) -> InventoryItemModel:
    item = await session.get(InventoryItemModel, inventory_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="inventory item not found")
    return item


@router.get("/{inventory_item_id}", response_model=InventoryOut)
async def get_inventory_item(
    inventory_item_id: UUID, session: AsyncSession = Depends(get_session)
) -> InventoryItemModel:
    return await _get_inventory_item_or_404(session, inventory_item_id)


@router.post("/{inventory_item_id}/test-runs", response_model=TestRunOut, status_code=201)
async def add_test_run(
    inventory_item_id: UUID,
    payload: TestRunCreate,
    session: AsyncSession = Depends(get_session),
) -> TestRunModel:
    await _get_inventory_item_or_404(session, inventory_item_id)
    test_run = TestRunModel(inventory_item_id=inventory_item_id, **payload.model_dump())
    session.add(test_run)
    await session.commit()
    return test_run


@router.get("/{inventory_item_id}/test-runs", response_model=list[TestRunOut])
async def list_test_runs(
    inventory_item_id: UUID, session: AsyncSession = Depends(get_session)
) -> list[TestRunModel]:
    await _get_inventory_item_or_404(session, inventory_item_id)
    rows = (
        await session.scalars(
            select(TestRunModel)
            .where(TestRunModel.inventory_item_id == inventory_item_id)
            .order_by(TestRunModel.created_at.desc())
        )
    ).all()
    return list(rows)
