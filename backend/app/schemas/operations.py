import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import Marketplace, ProductCategory, TaxProfileType


class CredentialStatus(StrEnum):
    SET = "SET"
    EMPTY = "EMPTY"
    MISSING = "MISSING"


class WatchlistCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    marketplace: Marketplace
    category: ProductCategory
    include_terms: list[str] = Field(min_length=1)
    exclude_terms: list[str] = Field(default_factory=list)
    filters: dict[str, object] = Field(default_factory=dict)
    polling_interval_seconds: int = Field(ge=300)
    enabled: bool = True


class WatchlistUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    include_terms: list[str] | None = None
    exclude_terms: list[str] | None = None
    filters: dict[str, object] | None = None
    polling_interval_seconds: int | None = Field(default=None, ge=300)


class WatchlistOut(BaseModel):
    id: uuid.UUID
    name: str
    marketplace: Marketplace
    category: ProductCategory
    include_terms: list[str]
    exclude_terms: list[str]
    filters: dict[str, object]
    polling_interval_seconds: int
    enabled: bool
    last_polled_at: datetime | None


class CostProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    effective_from: datetime
    effective_to: datetime | None = None
    tax_profile: TaxProfileType
    configuration: dict[str, object]


class CostProfileOut(BaseModel):
    id: uuid.UUID
    name: str
    version: int
    effective_from: datetime
    effective_to: datetime | None
    tax_profile: TaxProfileType
    configuration: dict[str, object]


class RiskRuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=120)
    effective_from: datetime
    effective_to: datetime | None = None
    matcher: dict[str, object]
    severity: str = Field(min_length=1, max_length=40)
    required_evidence: list[str] = Field(default_factory=list)
    reserve_adjustment_bps: int = 0
    recommendation_cap: str | None = None
    explanation: str = Field(min_length=1, max_length=500)


class RiskRuleOut(BaseModel):
    id: uuid.UUID
    key: str
    version: int
    effective_from: datetime
    effective_to: datetime | None
    matcher: dict[str, object]
    severity: str
    required_evidence: list[str]
    reserve_adjustment_bps: int
    recommendation_cap: str | None
    explanation: str


class SettingsOut(BaseModel):
    ebay_client_id: CredentialStatus
    ebay_client_secret: CredentialStatus
    ebay_marketplace_id: str
    cost_profiles: list[CostProfileOut]
    risk_rules: list[RiskRuleOut]


class InventoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: uuid.UUID
    source_observation_id: uuid.UUID | None = None
    serial_number: str | None = Field(default=None, max_length=240)
    acquisition_price_cents: int = Field(ge=0)
    acquisition_costs: dict[str, int] = Field(default_factory=dict)
    condition_notes: str = Field(default="", max_length=4000)


class InventoryOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    source_observation_id: uuid.UUID | None
    serial_number: str | None
    acquisition_price_cents: int
    acquisition_costs: dict[str, int]
    condition_notes: str
    disposition: str


class TestRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    procedure_name: str = Field(min_length=1, max_length=160)
    tool_name: str = Field(min_length=1, max_length=160)
    duration_seconds: int = Field(gt=0)
    configuration: dict[str, object] = Field(default_factory=dict)
    result: str = Field(min_length=1, max_length=40)
    measured_values: dict[str, object] = Field(default_factory=dict)
    notes: str = Field(default="", max_length=4000)
    evidence_paths: list[str] = Field(default_factory=list)


class TestRunOut(BaseModel):
    id: uuid.UUID
    inventory_item_id: uuid.UUID
    procedure_name: str
    tool_name: str
    duration_seconds: int
    configuration: dict[str, object]
    result: str
    measured_values: dict[str, object]
    notes: str
    evidence_paths: list[str]


class AlertOut(BaseModel):
    id: uuid.UUID
    evaluation_id: uuid.UUID
    alert_type: str
    acknowledged_at: datetime | None


class SourceHealthOut(BaseModel):
    last_success_at: datetime | None
    quota_remaining: int | None
    stale_estimate_count: int
    review_queue_count: int
    failed_job_count: int
