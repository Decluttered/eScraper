import base64
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import httpx

from app.db.models.operations import WatchlistModel
from app.domain.enums import Marketplace
from app.schemas.sources import SourceEnvelope

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"

logger = logging.getLogger(__name__)


class EbayAuthenticationError(Exception):
    pass


class EbayQuotaError(Exception):
    pass


class EbayInvalidQueryError(Exception):
    pass


class EbayTransientError(Exception):
    pass


def _decimal_to_cents(value: str) -> int:
    return int(
        (Decimal(value) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    )


@dataclass
class EbayBrowseClient:
    client_id: str
    client_secret: str
    http_client: httpx.AsyncClient
    marketplace_id: str = "EBAY_DE"
    _token: str | None = field(default=None, init=False, repr=False)
    _token_expires_at: datetime | None = field(default=None, init=False, repr=False)

    async def _get_token(self) -> str:
        now = datetime.now(UTC)
        if (
            self._token is not None
            and self._token_expires_at is not None
            and now < self._token_expires_at
        ):
            return self._token

        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        response = await self.http_client.post(
            TOKEN_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": OAUTH_SCOPE},
        )
        if response.status_code == 401:
            raise EbayAuthenticationError(
                f"eBay OAuth token request failed with status {response.status_code}"
            )
        if response.status_code >= 500:
            raise EbayTransientError(
                f"eBay OAuth token request failed with status {response.status_code}"
            )
        response.raise_for_status()
        payload = response.json()
        self._token = payload["access_token"]
        self._token_expires_at = now + timedelta(seconds=int(payload["expires_in"]) - 60)
        logger.info("ebay token refreshed", extra={"expires_in": payload["expires_in"]})
        return self._token

    async def search(self, watchlist: WatchlistModel) -> list[SourceEnvelope]:
        token = await self._get_token()
        params: dict[str, str] = {
            "q": " ".join(watchlist.include_terms),
            "limit": "200",
        }
        category_id = watchlist.filters.get("category_id")
        if category_id:
            params["category_ids"] = str(category_id)
        price_ceiling_cents = watchlist.filters.get("price_ceiling_cents")
        if price_ceiling_cents:
            params["filter"] = f"price:[..{Decimal(price_ceiling_cents) / 100}],priceCurrency:EUR"

        response = await self.http_client.get(
            SEARCH_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
            },
            params=params,
        )
        self._raise_for_status(response)
        payload = response.json()
        envelopes = [self._map_item(item) for item in payload.get("itemSummaries", [])]
        logger.info(
            "ebay search completed",
            extra={"status_code": response.status_code, "item_count": len(envelopes)},
        )
        return envelopes

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code == 401:
            raise EbayAuthenticationError(f"eBay search failed with status {response.status_code}")
        if response.status_code == 429:
            raise EbayQuotaError(f"eBay search failed with status {response.status_code}")
        if response.status_code == 400:
            raise EbayInvalidQueryError(f"eBay search failed with status {response.status_code}")
        if response.status_code >= 500:
            raise EbayTransientError(f"eBay search failed with status {response.status_code}")
        response.raise_for_status()

    def _map_item(self, item: dict[str, Any]) -> SourceEnvelope:
        price = item["price"]
        shipping_options = item.get("shippingOptions", [])
        shipping_value = (
            shipping_options[0]["shippingCost"]["value"] if shipping_options else "0"
        )
        location = item.get("itemLocation", {})
        return SourceEnvelope(
            source=Marketplace.EBAY_DE,
            external_id=item["itemId"],
            source_url=item["itemWebUrl"],
            captured_at=datetime.now(UTC),
            title=item["title"],
            description="",
            asking_price_cents=_decimal_to_cents(price["value"]),
            shipping_cents=_decimal_to_cents(shipping_value),
            condition=item.get("condition", ""),
            location_summary=location.get("postalCode", ""),
            sale_format="FIXED_PRICE",
            metadata={"item_id": item["itemId"]},
            import_method="EBAY_API",
        )
