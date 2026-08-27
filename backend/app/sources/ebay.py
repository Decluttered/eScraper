import base64
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

import httpx
from pydantic import SecretStr

from app.schemas.sources import SourceEnvelope, SourceHealth

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"


class EbayAuthenticationError(Exception):
    """Raised when eBay rejects the client credentials."""


class EbayQuotaError(Exception):
    """Raised when eBay reports quota exhaustion."""


class EbayInvalidQueryError(Exception):
    """Raised when the search query is rejected as invalid."""


class EbayTransientError(Exception):
    """Raised for retryable transport or server failures."""


def _to_cents(value: object) -> int:
    if value is None:
        return 0
    amount = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(amount * 100)


class EbayBrowseClient:
    def __init__(
        self,
        client_id: SecretStr | None,
        client_secret: SecretStr | None,
        marketplace_id: str = "EBAY_DE",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._marketplace_id = marketplace_id
        self._http = http_client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = http_client is None
        self._token: str | None = None
        self._token_expires_at: datetime | None = None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def _ensure_token(self) -> str:
        if (
            self._token is not None
            and self._token_expires_at is not None
            and self._token_expires_at > datetime.utcnow()
        ):
            return self._token
        if self._client_id is None or self._client_secret is None:
            raise EbayAuthenticationError("missing eBay credentials")
        credentials = base64.b64encode(
            f"{self._client_id.get_secret_value()}:{self._client_secret.get_secret_value()}".encode()
        ).decode()
        response = await self._http.post(
            TOKEN_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": OAUTH_SCOPE},
        )
        if response.status_code == 401:
            raise EbayAuthenticationError("eBay token request rejected")
        if response.status_code >= 500:
            raise EbayTransientError("eBay token server error")
        payload = response.json()
        self._token = payload["access_token"]
        expires_in = int(payload.get("expires_in", 3600))
        self._token_expires_at = datetime.utcnow().replace(microsecond=0)
        self._token_expires_at = datetime.utcfromtimestamp(
            int(self._token_expires_at.timestamp()) + expires_in - 60
        )
        return self._token

    async def search(self, query: str, limit: int = 50) -> list[SourceEnvelope]:
        if not query.strip():
            raise EbayInvalidQueryError("empty search query")
        token = await self._ensure_token()
        response = await self._http.get(
            SEARCH_URL,
            params={"q": query, "limit": str(limit)},
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": self._marketplace_id,
            },
        )
        if response.status_code == 401:
            raise EbayAuthenticationError("eBay search rejected token")
        if response.status_code == 429:
            raise EbayQuotaError("eBay daily quota exhausted")
        if response.status_code == 400:
            raise EbayInvalidQueryError("eBay search query invalid")
        if response.status_code >= 500:
            raise EbayTransientError("eBay search server error")
        payload = response.json()
        envelopes: list[SourceEnvelope] = []
        for item in payload.get("itemSummaries", []):
            envelopes.append(
                SourceEnvelope(
                    source=self._marketplace_to_enum(),
                    external_id=str(item.get("itemId", "")),
                    source_url=str(item.get("itemWebUrl", "")),
                    captured_at=datetime.utcnow(),
                    title=str(item.get("title", "")),
                    description="",
                    asking_price_cents=_to_cents(item.get("price", {}).get("value")),
                    shipping_cents=_to_cents(
                        item.get("shippingOptions", [{}])[0].get("shippingCost", {}).get("value")
                        if item.get("shippingOptions")
                        else 0
                    ),
                    condition=str(item.get("condition", "")),
                    location_summary=str(item.get("itemLocation", {}).get("country", "")),
                    sale_format="FIXED_PRICE",
                    import_method="EBAY_API",
                    metadata={"item_id": str(item.get("itemId", ""))},
                )
            )
        return envelopes

    def _marketplace_to_enum(self):
        from app.domain.enums import Marketplace
        return Marketplace.EBAY_DE

    async def health(self) -> SourceHealth:
        try:
            await self._ensure_token()
            return SourceHealth(
                source=self._marketplace_to_enum(),
                healthy=True,
                checked_at=datetime.utcnow(),
            )
        except EbayAuthenticationError:
            return SourceHealth(
                source=self._marketplace_to_enum(),
                healthy=False,
                checked_at=datetime.utcnow(),
                error_code="EBAY_AUTH",
            )
        except EbayTransientError:
            return SourceHealth(
                source=self._marketplace_to_enum(),
                healthy=False,
                checked_at=datetime.utcnow(),
                error_code="EBAY_TRANSIENT",
            )
