"""Simple scheduler that dispatches poll tasks for due watchlists.

Runs as a standalone process: ``python -m worker.scheduler``.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)


async def _tick() -> None:
    from sqlalchemy import select

    from app.db.models.operations import WatchlistModel
    from app.db.session import SessionFactory
    from worker.tasks import poll_ebay_watchlist

    now = datetime.now(UTC)
    async with SessionFactory() as session:
        watchlists = (
            await session.scalars(
                select(WatchlistModel).where(WatchlistModel.enabled.is_(True))
            )
        ).all()
        for watchlist in watchlists:
            if watchlist.marketplace is not Marketplace.EBAY_DE:
                continue
            last_polled = watchlist.last_polled_at
            if last_polled is not None and (now - last_polled) < timedelta(
                seconds=watchlist.polling_interval_seconds
            ):
                continue
            bucket = now.strftime("%Y%m%d%H%M")
            poll_ebay_watchlist.send(str(watchlist.id), bucket)
            watchlist.last_polled_at = now
        await session.commit()


async def main() -> None:
    while True:
        try:
            await _tick()
        except Exception:
            logger.exception("scheduler tick failed")
        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
