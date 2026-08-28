from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from worker.tasks import poll_ebay_watchlist_async

from app.db.models.listing import ListingObservationModel, RawListingModel
from app.db.models.operations import JobRunModel, WatchlistModel
from app.domain.enums import Marketplace, ProductCategory
from app.schemas.sources import SourceEnvelope
from app.sources.ebay import EbayAuthenticationError, EbayTransientError

NOW = datetime(2026, 8, 27, tzinfo=UTC)
BUCKET = "2026-08-27T10:00:00+00:00"


class FakeEbayClient:
    def __init__(self, envelopes=None, error=None) -> None:
        self._envelopes = envelopes or []
        self._error = error
        self.call_count = 0

    async def search(self, watchlist: WatchlistModel) -> list[SourceEnvelope]:
        self.call_count += 1
        if self._error is not None:
            raise self._error
        return self._envelopes


async def _seed_watchlist(session) -> WatchlistModel:
    watchlist = WatchlistModel(
        name="RTX 3060 12GB",
        marketplace=Marketplace.EBAY_DE,
        category=ProductCategory.GPU,
        include_terms=["rtx 3060", "12gb"],
        exclude_terms=[],
        filters={},
        polling_interval_seconds=900,
        enabled=True,
    )
    session.add(watchlist)
    await session.commit()
    return watchlist


def _envelope(external_id: str) -> SourceEnvelope:
    return SourceEnvelope(
        source=Marketplace.EBAY_DE,
        external_id=external_id,
        source_url="https://www.ebay.de/itm/123",
        captured_at=NOW,
        title="RTX 3060 12GB",
        description="",
        asking_price_cents=17999,
        shipping_cents=690,
        condition="Gebraucht",
        location_summary="10115",
        sale_format="FIXED_PRICE",
        metadata={},
        import_method="EBAY_API",
    )


async def test_repeated_call_for_same_bucket_discovers_only_once(session) -> None:
    watchlist = await _seed_watchlist(session)
    client = FakeEbayClient(envelopes=[_envelope("v1|1|0")])

    await poll_ebay_watchlist_async(str(watchlist.id), BUCKET, session, client)
    await poll_ebay_watchlist_async(str(watchlist.id), BUCKET, session, client)

    assert client.call_count == 1
    observations = (await session.scalars(select(ListingObservationModel))).all()
    assert len(observations) == 1


async def test_transient_failure_increments_attempts_and_reraises(session) -> None:
    watchlist = await _seed_watchlist(session)
    client = FakeEbayClient(error=EbayTransientError("service unavailable"))

    with pytest.raises(EbayTransientError):
        await poll_ebay_watchlist_async(str(watchlist.id), BUCKET, session, client)

    job_run = await session.scalar(
        select(JobRunModel).where(JobRunModel.idempotency_key == f"poll:{watchlist.id}:{BUCKET}")
    )
    assert job_run is not None
    assert job_run.attempts == 2
    assert job_run.status == "RUNNING"


async def test_authentication_failure_is_terminal_and_does_not_reraise(session) -> None:
    watchlist = await _seed_watchlist(session)
    client = FakeEbayClient(error=EbayAuthenticationError("invalid credentials"))

    await poll_ebay_watchlist_async(str(watchlist.id), BUCKET, session, client)

    job_run = await session.scalar(
        select(JobRunModel).where(JobRunModel.idempotency_key == f"poll:{watchlist.id}:{BUCKET}")
    )
    assert job_run is not None
    assert job_run.status == "FAILED"
    assert job_run.last_error_code == "EBAY_AUTH"
    assert job_run.finished_at is not None

    observations = (await session.scalars(select(RawListingModel))).all()
    assert observations == []
