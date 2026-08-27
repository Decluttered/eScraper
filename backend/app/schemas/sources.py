import uuid
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field, HttpUrl

from app.domain.enums import Marketplace


class SourceEnvelope(BaseModel):
    source: Marketplace
    external_id: str = Field(min_length=1, max_length=240)
    source_url: HttpUrl
    captured_at: datetime
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=8000)
    asking_price_cents: int = Field(ge=0)
    shipping_cents: int = Field(default=0, ge=0)
    condition: str = Field(default="", max_length=120)
    location_summary: str = Field(default="", max_length=240)
    sale_format: str = Field(default="UNKNOWN", max_length=40)
    metadata: dict[str, object] = Field(default_factory=dict)
    import_method: str = Field(max_length=40)


class SourceHealth(BaseModel):
    source: Marketplace
    healthy: bool
    checked_at: datetime
    quota_remaining: int | None = None
    error_code: str | None = None


class SourceAdapter(Protocol):
    async def discover(self) -> list[SourceEnvelope]:
        raise NotImplementedError

    async def health(self) -> SourceHealth:
        raise NotImplementedError


class IngestionResult(BaseModel):
    raw_listing_id: uuid.UUID
    observation_id: uuid.UUID
    created: bool
