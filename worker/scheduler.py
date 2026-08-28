import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.operations import WatchlistModel
from app.db.session import SessionFactory
from app.domain.enums import Marketplace
from worker.tasks import poll_ebay_watchlist

POLL_INTERVAL_SECONDS = 30


def bucket_for(now: datetime, polling_interval_seconds: int) -> str:
    epoch_seconds = int(now.timestamp())
    interval = max(1, polling_interval_seconds)
    bucket_start = epoch_seconds - (epoch_seconds % interval)
    return datetime.fromtimestamp(bucket_start, tz=UTC).isoformat()


def is_due(watchlist: WatchlistModel, now: datetime) -> bool:
    if watchlist.last_polled_at is None:
        return True
    elapsed = (now - watchlist.last_polled_at).total_seconds()
    return elapsed >= watchlist.polling_interval_seconds


async def dispatch_due_watchlists(session: AsyncSession) -> int:
    now = datetime.now(UTC)
    rows = (
        await session.scalars(
            select(WatchlistModel).where(
                WatchlistModel.enabled.is_(True),
                WatchlistModel.marketplace == Marketplace.EBAY_DE,
            )
        )
    ).all()
    dispatched = 0
    for watchlist in rows:
        if not is_due(watchlist, now):
            continue
        bucket = bucket_for(now, watchlist.polling_interval_seconds)
        poll_ebay_watchlist.send(str(watchlist.id), bucket)
        dispatched += 1
    return dispatched


async def run_forever() -> None:
    while True:
        async with SessionFactory() as session:
            await dispatch_due_watchlists(session)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_forever())
