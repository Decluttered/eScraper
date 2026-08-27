from dataclasses import dataclass
from uuid import UUID

from app.domain.enums import Condition, ProductCategory


@dataclass(frozen=True, slots=True)
class NormalizationCandidate:
    product_id: UUID
    category: ProductCategory
    alias: str
    required_tokens: frozenset[str]
    excluded_tokens: frozenset[str]


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    product_id: UUID | None
    condition: Condition
    confidence_bps: int
    flags: tuple[str, ...]
    review_required: bool
