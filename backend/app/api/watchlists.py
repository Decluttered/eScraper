import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.operations import WatchlistModel
from app.db.session import get_session
from app.schemas.operations import WatchlistCreate

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


@router.get("", response_model=list[dict])
async def list_watchlists(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict]:
    watchlists = (await session.scalars(select(WatchlistModel))).all()
    return [
        {
            "id": str(w.id),
            "name": w.name,
            "marketplace": w.marketplace.value,
            "category": w.category.value,
            "include_terms": list(w.include_terms),
            "exclude_terms": list(w.exclude_terms),
            "polling_interval_seconds": w.polling_interval_seconds,
            "enabled": w.enabled,
        }
        for w in watchlists
    ]


@router.post("", status_code=201)
async def create_watchlist(
    payload: WatchlistCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    existing = await session.scalar(
        select(WatchlistModel).where(WatchlistModel.name == payload.name)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="watchlist name already exists")
    watchlist = WatchlistModel(
        name=payload.name,
        marketplace=payload.marketplace,
        category=payload.category,
        include_terms=payload.include_terms,
        exclude_terms=payload.exclude_terms,
        filters=payload.filters,
        polling_interval_seconds=payload.polling_interval_seconds,
        enabled=payload.enabled,
    )
    session.add(watchlist)
    await session.commit()
    return {"id": str(watchlist.id)}


@router.delete("/{watchlist_id}", status_code=204)
async def delete_watchlist(
    watchlist_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    watchlist = await session.scalar(
        select(WatchlistModel).where(WatchlistModel.id == watchlist_id)
    )
    if watchlist is None:
        raise HTTPException(status_code=404, detail="watchlist not found")
    await session.delete(watchlist)
    await session.commit()
