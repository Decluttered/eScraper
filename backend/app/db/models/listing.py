import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.domain.enums import Condition, Marketplace


class RawListingModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "raw_listings"
    __table_args__ = (
        UniqueConstraint("source", "external_id", "payload_checksum", name="uq_raw_payload"),
        Index("ix_raw_listing_source_capture", "source", "captured_at"),
    )

    source: Mapped[Marketplace]
    external_id: Mapped[str] = mapped_column(String(240))
    source_url: Mapped[str] = mapped_column(String(2048))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_title: Mapped[str] = mapped_column(String(500))
    raw_description: Mapped[str] = mapped_column(String(8000), default="")
    asking_price_cents: Mapped[int] = mapped_column(BigInteger)
    shipping_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    raw_condition: Mapped[str] = mapped_column(String(120), default="")
    location_summary: Mapped[str] = mapped_column(String(240), default="")
    payload_checksum: Mapped[str] = mapped_column(String(80))
    import_method: Mapped[str] = mapped_column(String(40))
    raw_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class ListingObservationModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "listing_observations"

    raw_listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("raw_listings.id", ondelete="RESTRICT"), unique=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT")
    )
    asking_price_cents: Mapped[int] = mapped_column(BigInteger)
    shipping_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    condition: Mapped[Condition]
    sale_format: Mapped[str] = mapped_column(String(40))
    seller_type: Mapped[str | None] = mapped_column(String(40))
    model_match_confidence_bps: Mapped[int] = mapped_column(default=0)
    flags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    review_status: Mapped[str] = mapped_column(String(40), default="PENDING")
