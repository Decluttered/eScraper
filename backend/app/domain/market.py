from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.enums import ComparableStatus, Condition, ConfidenceLevel


@dataclass(frozen=True, slots=True)
class ComparableEvidence:
    id: str
    product_id: UUID
    status: ComparableStatus
    condition: Condition
    item_price_cents: int
    shipping_cents: int
    occurred_at: datetime
    variant_match_confidence_bps: int
    observation_count: int
    sold_through_bps: int | None


@dataclass(frozen=True, slots=True)
class MarketEstimationConfig:
    recency_half_life_days: int = 45
    stale_after_days: int = 30
    medium_min_sales: int = 8
    medium_max_age_days: int = 180
    high_min_sales: int = 20
    high_max_age_days: int = 90


@dataclass(frozen=True, slots=True)
class MarketEstimate:
    downside_item_price_cents: int
    expected_item_price_cents: int
    optimistic_item_price_cents: int
    confidence: ConfidenceLevel
    liquidity_bps: int
    comparable_ids: tuple[str, ...]
    latest_sale_at: datetime | None
    stale: bool
