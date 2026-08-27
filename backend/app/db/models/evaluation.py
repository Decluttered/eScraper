import uuid

from sqlalchemy import BigInteger, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.domain.enums import ConfidenceLevel, Recommendation


class EvaluationSnapshotModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_snapshots"

    observation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("listing_observations.id", ondelete="RESTRICT")
    )
    cost_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cost_profiles.id", ondelete="RESTRICT")
    )
    cost_profile_version: Mapped[int] = mapped_column(Integer)
    risk_rule_versions: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict)
    comparable_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    input_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB)
    downside_resale_cents: Mapped[int] = mapped_column(BigInteger)
    expected_resale_cents: Mapped[int] = mapped_column(BigInteger)
    optimistic_resale_cents: Mapped[int] = mapped_column(BigInteger)
    expected_profit_cents: Mapped[int] = mapped_column(BigInteger)
    downside_profit_cents: Mapped[int] = mapped_column(BigInteger)
    expected_roi_bps: Mapped[int] = mapped_column(Integer)
    maximum_purchase_price_cents: Mapped[int] = mapped_column(BigInteger)
    liquidity_bps: Mapped[int] = mapped_column(Integer)
    market_confidence: Mapped[ConfidenceLevel]
    risk_reserve_cents: Mapped[int] = mapped_column(BigInteger)
    risk_severity: Mapped[str]
    score: Mapped[int] = mapped_column(Integer)
    recommendation: Mapped[Recommendation]
    reasons: Mapped[list[str]] = mapped_column(JSONB, default=list)
