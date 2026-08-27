import json
from pathlib import Path

import httpx
import pytest

from app.core.config import Settings
from app.sources.ebay import (
    EbayAuthenticationError,
    EbayBrowseClient,
    EbayInvalidQueryError,
    EbayQuotaError,
    EbayTransientError,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ebay_search_rtx3060.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


def _mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.endswith("/identity/v1/oauth2/token"):
            return httpx.Response(
                200,
                json={"access_token": "test-token", "expires_in": 3600},
            )
        return httpx.Response(200, json=_load_fixture())

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_ebay_search_maps_results_to_envelopes(caplog) -> None:
    transport = _mock_transport()
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = EbayBrowseClient(
            client_id="id",
            client_secret="secret",
            http_client=http_client,
        )
        results = await client.search("RTX 3060 12GB", limit=10)

    assert len(results) == 2
    assert results[0].asking_price_cents == 17999
    assert results[0].shipping_cents == 690
    assert results[0].import_method == "EBAY_API"
    assert "client-secret" not in caplog.text


@pytest.mark.asyncio
async def test_ebay_401_raises_authentication_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "token" in str(request.url):
            return httpx.Response(401, json={"error": "invalid_client"})
        return httpx.Response(200, json={"itemSummaries": []})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = EbayBrowseClient(
            client_id="id", client_secret="secret", http_client=http_client
        )
        with pytest.raises(EbayAuthenticationError):
            await client.search("RTX 3060 12GB")


@pytest.mark.asyncio
async def test_ebay_429_raises_quota_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "token" in str(request.url):
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        return httpx.Response(429, json={"error": "quota"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = EbayBrowseClient(
            client_id="id", client_secret="secret", http_client=http_client
        )
        with pytest.raises(EbayQuotaError):
            await client.search("RTX 3060 12GB")


@pytest.mark.asyncio
async def test_ebay_400_raises_invalid_query() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "token" in str(request.url):
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        return httpx.Response(400, json={"error": "bad_query"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = EbayBrowseClient(
            client_id="id", client_secret="secret", http_client=http_client
        )
        with pytest.raises(EbayInvalidQueryError):
            await client.search("RTX 3060 12GB")


@pytest.mark.asyncio
async def test_ebay_503_raises_transient() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "token" in str(request.url):
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        return httpx.Response(503, json={"error": "unavailable"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = EbayBrowseClient(
            client_id="id", client_secret="secret", http_client=http_client
        )
        with pytest.raises(EbayTransientError):
            await client.search("RTX 3060 12GB")
