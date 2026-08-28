from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.operations import WatchlistModel
from app.db.session import get_session
from app.schemas.operations import WatchlistCreate, WatchlistOut, WatchlistUpdate

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


@router.get("", response_model=list[WatchlistOut])
async def list_watchlists(session: AsyncSession = Depends(get_session)) -> list[WatchlistModel]:
    rows = (await session.scalars(select(WatchlistModel).order_by(WatchlistModel.name))).all()
    return list(rows)


@router.post("", response_model=WatchlistOut, status_code=201)
async def create_watchlist(
    payload: WatchlistCreate, session: AsyncSession = Depends(get_session)
) -> WatchlistModel:
    existing = await session.scalar(
        select(WatchlistModel).where(WatchlistModel.name == payload.name)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="a watchlist with this name already exists")

    watchlist = WatchlistModel(**payload.model_dump())
    session.add(watchlist)
    await session.commit()
    return watchlist


async def _get_watchlist_or_404(session: AsyncSession, watchlist_id: UUID) -> WatchlistModel:
    watchlist = await session.get(WatchlistModel, watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=404, detail="watchlist not found")
    return watchlist


@router.patch("/{watchlist_id}", response_model=WatchlistOut)
async def update_watchlist(
    watchlist_id: UUID,
    payload: WatchlistUpdate,
    session: AsyncSession = Depends(get_session),
) -> WatchlistModel:
    watchlist = await _get_watchlist_or_404(session, watchlist_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(watchlist, field, value)
    await session.commit()
    return watchlist


@router.post("/{watchlist_id}/enable", response_model=WatchlistOut)
async def enable_watchlist(
    watchlist_id: UUID, session: AsyncSession = Depends(get_session)
) -> WatchlistModel:
    watchlist = await _get_watchlist_or_404(session, watchlist_id)
    watchlist.enabled = True
    await session.commit()
    return watchlist


@router.post("/{watchlist_id}/disable", response_model=WatchlistOut)
async def disable_watchlist(
    watchlist_id: UUID, session: AsyncSession = Depends(get_session)
) -> WatchlistModel:
    watchlist = await _get_watchlist_or_404(session, watchlist_id)
    watchlist.enabled = False
    await session.commit()
    return watchlist


@router.delete("/{watchlist_id}", status_code=204)
async def delete_watchlist(
    watchlist_id: UUID, session: AsyncSession = Depends(get_session)
) -> None:
    watchlist = await _get_watchlist_or_404(session, watchlist_id)
    await session.delete(watchlist)
    await session.commit()
