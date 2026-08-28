import json
import logging
from pathlib import Path

import httpx
import pytest

from app.db.models.operations import WatchlistModel
from app.domain.enums import Marketplace, ProductCategory
from app.sources.ebay import (
    TOKEN_URL,
    EbayAuthenticationError,
    EbayBrowseClient,
    EbayInvalidQueryError,
    EbayQuotaError,
    EbayTransientError,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ebay_search_rtx3060.json"
SEARCH_FIXTURE = json.loads(FIXTURE_PATH.read_text())


def _watchlist() -> WatchlistModel:
    return WatchlistModel(
        name="RTX 3060 12GB",
        marketplace=Marketplace.EBAY_DE,
        category=ProductCategory.GPU,
        include_terms=["rtx 3060", "12gb"],
        exclude_terms=[],
        filters={},
        polling_interval_seconds=900,
        enabled=True,
    )


def _token_response() -> httpx.Response:
    return httpx.Response(
        200, json={"access_token": "test-access-token", "expires_in": 7200}
    )


def _client_for(search_response: httpx.Response) -> EbayBrowseClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == TOKEN_URL:
            return _token_response()
        return search_response

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return EbayBrowseClient(
        client_id="test-client-id",
        client_secret="test-client-secret",
        http_client=http_client,
    )


async def test_search_maps_items_and_never_logs_secrets(caplog) -> None:
    client = _client_for(httpx.Response(200, json=SEARCH_FIXTURE))

    with caplog.at_level(logging.DEBUG):
        results = await client.search(_watchlist())

    assert len(results) == 2
    assert results[0].source is Marketplace.EBAY_DE
    assert results[0].external_id == "v1|123456789|0"
    assert results[0].asking_price_cents == 17999
    assert results[0].shipping_cents == 690
    assert results[0].import_method == "EBAY_API"
    assert "client-secret" not in caplog.text
    assert "test-client-secret" not in caplog.text


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (401, EbayAuthenticationError),
        (429, EbayQuotaError),
        (400, EbayInvalidQueryError),
        (503, EbayTransientError),
    ],
)
async def test_search_maps_error_status_codes(status_code, expected_error) -> None:
    client = _client_for(httpx.Response(status_code, json={"errors": []}))

    with pytest.raises(expected_error):
        await client.search(_watchlist())
