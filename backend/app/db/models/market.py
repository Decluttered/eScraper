import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.domain.enums import ComparableStatus, Condition, Marketplace, TaxProfileType


class MarketComparableModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "market_comparables"

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    source: Mapped[Marketplace]
    status: Mapped[ComparableStatus]
    condition: Mapped[Condition]
    item_price_cents: Mapped[int] = mapped_column(BigInteger)
    shipping_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    variant_match_confidence_bps: Mapped[int] = mapped_column(Integer)
    source_quality: Mapped[str] = mapped_column(String(40))
    observation_count: Mapped[int] = mapped_column(Integer, default=1)
    sold_through_bps: Mapped[int | None] = mapped_column(Integer)
    source_note: Mapped[str] = mapped_column(String(500), default="")


class CostProfileModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "cost_profiles"

    name: Mapped[str] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tax_profile: Mapped[TaxProfileType]
    configuration: Mapped[dict[str, object]] = mapped_column(JSONB)


class RiskRuleModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "risk_rules"

    key: Mapped[str] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    matcher: Mapped[dict[str, object]] = mapped_column(JSONB)
    severity: Mapped[str] = mapped_column(String(40))
    required_evidence: Mapped[list[str]] = mapped_column(JSONB, default=list)
    reserve_adjustment_bps: Mapped[int] = mapped_column(Integer, default=0)
    recommendation_cap: Mapped[str | None] = mapped_column(String(40))
    explanation: Mapped[str] = mapped_column(String(500))
