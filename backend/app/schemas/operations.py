from datetime import datetime
from enum import StrEnum
from uuid import UUID

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
    polling_interval_seconds: int = Field(default=900, ge=300)
    enabled: bool = True


class CostProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    version: int = Field(ge=1)
    effective_from: datetime
    effective_to: datetime | None = None
    tax_profile: TaxProfileType
    configuration: dict[str, object]


class RiskRuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=120)
    version: int = Field(ge=1)
    effective_from: datetime
    effective_to: datetime | None = None
    matcher: dict[str, object]
    severity: str = Field(min_length=1, max_length=40)
    required_evidence: list[str] = Field(default_factory=list)
    reserve_adjustment_bps: int = Field(default=0)
    recommendation_cap: str | None = None
    explanation: str = Field(min_length=1, max_length=500)


class InventoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: UUID
    serial_number: str | None = Field(default=None, max_length=240)
    acquisition_price_cents: int = Field(ge=0)
    acquisition_costs: dict[str, int] = Field(default_factory=dict)
    condition_notes: str = Field(default="", max_length=4000)


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
