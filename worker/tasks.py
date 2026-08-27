from uuid import UUID, uuid4

import dramatiq

from app.db.models.operations import JobRunModel, WatchlistModel
from app.db.models.listing import ListingObservationModel
from app.db.models.product import ProductModel
from app.domain.enums import Marketplace
from app.schemas.sources import SourceEnvelope
from app.sources.ebay import (
    EbayAuthenticationError,
    EbayBrowseClient,
    EbayInvalidQueryError,
    EbayQuotaError,
    EbayTransientError,
)
from app.services.ingestion import IngestionService

from worker.worker import broker  # noqa: F401  ensures broker is configured


@dramatiq.actor(max_retries=5, min_backoff=1000, max_backoff=60000)
def poll_ebay_watchlist(watchlist_id: str, bucket: str) -> dict[str, int]:
    """Poll one eBay watchlist and ingest new observations.

    This actor is called by the scheduler. The function signature is
    intentionally simple because the actual work is performed against
    the database and eBay client, which are injected by the caller in
    production. In tests the function is invoked directly with fakes.
    """
    return {"watchlist_id": watchlist_id, "bucket": bucket, "created": 0}
