from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field

from app.domain.enums import ComparableStatus, Condition, Marketplace


class ComparableImportRow(BaseModel):
    product_id: UUID
    source: Marketplace
    status: ComparableStatus
    condition: Condition
    currency: Literal["EUR"]
    occurred_at: AwareDatetime
    item_price_cents: int = Field(ge=0)
    shipping_cents: int = Field(default=0, ge=0)
    variant_match_confidence_bps: int = Field(ge=0, le=10000)
    observation_count: int = Field(default=1, ge=1)
    sold_through_bps: int | None = Field(default=None, ge=0, le=10000)
    source_note: str = Field(default="", max_length=500)


class ImportRowError(BaseModel):
    row_number: int
    field: str
    message: str
