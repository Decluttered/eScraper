import asyncio
import uuid
from datetime import UTC, datetime

import dramatiq
import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.operations import JobRunModel, WatchlistModel
from app.db.session import SessionFactory
from app.domain.enums import Marketplace
from app.services.ingestion import IngestionService
from app.sources.ebay import (
    EbayAuthenticationError,
    EbayBrowseClient,
    EbayInvalidQueryError,
    EbayQuotaError,
    EbayTransientError,
)
from worker import worker as _worker  # noqa: F401  registers the Redis broker on import


class EbayClientProtocol:
    async def search(self, watchlist: WatchlistModel) -> list:
        raise NotImplementedError


_TERMINAL_ERRORS: dict[type[Exception], str] = {
    EbayAuthenticationError: "EBAY_AUTH",
    EbayInvalidQueryError: "EBAY_INVALID_QUERY",
    EbayQuotaError: "EBAY_QUOTA",
}


async def poll_ebay_watchlist_async(
    watchlist_id: str,
    bucket: str,
    session: AsyncSession,
    client: EbayClientProtocol,
    ingestion: IngestionService | None = None,
) -> None:
    """Idempotently poll one eBay watchlist bucket and ingest any new listings.

    Exposed separately from the dramatiq actor so tests can invoke it directly
    with a fake session/adapter instead of going through the broker.
    """
    idempotency_key = f"poll:{watchlist_id}:{bucket}"
    job_run = JobRunModel(
        idempotency_key=idempotency_key,
        job_type="POLL_EBAY",
        status="RUNNING",
        attempts=1,
    )
    session.add(job_run)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return

    watchlist = await session.get(WatchlistModel, uuid.UUID(watchlist_id))
    if watchlist is None or watchlist.marketplace is not Marketplace.EBAY_DE:
        job_run.status = "FAILED"
        job_run.last_error_code = "INVALID_WATCHLIST"
        job_run.finished_at = datetime.now(UTC)
        await session.commit()
        return

    try:
        envelopes = await client.search(watchlist)
    except EbayTransientError as exc:
        job_run.attempts += 1
        job_run.last_error_code = "EBAY_TRANSIENT"
        job_run.last_error_message = str(exc)
        await session.commit()
        raise
    except tuple(_TERMINAL_ERRORS) as exc:
        job_run.status = "FAILED"
        job_run.last_error_code = _TERMINAL_ERRORS[type(exc)]
        job_run.last_error_message = str(exc)
        job_run.finished_at = datetime.now(UTC)
        await session.commit()
        return

    ingestion_service = ingestion or IngestionService()
    for envelope in envelopes:
        await ingestion_service.ingest(session, envelope)

    watchlist.last_polled_at = datetime.now(UTC)
    job_run.status = "SUCCEEDED"
    job_run.finished_at = datetime.now(UTC)
    await session.commit()


async def _poll_ebay_watchlist_live(watchlist_id: str, bucket: str) -> None:
    settings = get_settings()
    async with SessionFactory() as session, httpx.AsyncClient() as http_client:
        client = EbayBrowseClient(
            client_id=(
                settings.ebay_client_id.get_secret_value() if settings.ebay_client_id else ""
            ),
            client_secret=(
                settings.ebay_client_secret.get_secret_value()
                if settings.ebay_client_secret
                else ""
            ),
            http_client=http_client,
            marketplace_id=settings.ebay_marketplace_id,
        )
        await poll_ebay_watchlist_async(watchlist_id, bucket, session, client)


@dramatiq.actor(max_retries=5, min_backoff=1000, max_backoff=60000)
def poll_ebay_watchlist(watchlist_id: str, bucket: str) -> None:
    asyncio.run(_poll_ebay_watchlist_live(watchlist_id, bucket))
