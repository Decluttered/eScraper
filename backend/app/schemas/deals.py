import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.domain.enums import Condition, ConfidenceLevel, Recommendation


class CompanionImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["KLEINANZEIGEN_DE", "MANUAL"]
    external_id: str = Field(min_length=1, max_length=240)
    source_url: HttpUrl
    captured_at: datetime
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=8000)
    asking_price_cents: int = Field(ge=0)
    shipping_cents: int = Field(default=0, ge=0)
    condition: str = Field(default="", max_length=120)
    location_summary: str = Field(default="", max_length=240)
    sale_format: str = Field(default="CLASSIFIED_AD", max_length=40)
    import_method: Literal["CONFIRMED_EXTENSION", "MANUAL"]


class DealListItem(BaseModel):
    evaluation_id: uuid.UUID
    observation_id: uuid.UUID
    title: str
    asking_landed_cents: int
    expected_profit_cents: int
    downside_profit_cents: int
    maximum_purchase_price_cents: int
    expected_roi_bps: int
    score: int
    confidence: ConfidenceLevel
    recommendation: Recommendation
    evaluated_at: datetime


class DealDetail(DealListItem):
    source_url: HttpUrl
    input_snapshot: dict[str, object]
    comparable_ids: list[str]
    reasons: list[str]
    risk_reserve_cents: int


class ComparablePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    csv_content: str


class ComparablePreviewResponse(BaseModel):
    preview_token: str
    rows: list[dict[str, object]]
    errors: list[dict[str, object]]


class ComparableCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preview_token: str
    rows: list[dict[str, object]]


class ComparableCommitResponse(BaseModel):
    created_count: int


class ReviewResolutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: uuid.UUID
    condition: Condition
    confirmed_flags: list[str] = Field(default_factory=list)


class ReviewResolutionResponse(BaseModel):
    observation_id: uuid.UUID
    product_id: uuid.UUID
    condition: Condition
    flags: list[str]
    review_status: str
