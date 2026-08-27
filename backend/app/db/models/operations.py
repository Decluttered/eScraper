import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.domain.enums import Marketplace, ProductCategory


class WatchlistModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "watchlists"
    name: Mapped[str] = mapped_column(String(120))
    marketplace: Mapped[Marketplace]
    category: Mapped[ProductCategory]
    include_terms: Mapped[list[str]] = mapped_column(JSONB)
    exclude_terms: Mapped[list[str]] = mapped_column(JSONB, default=list)
    filters: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    polling_interval_seconds: Mapped[int] = mapped_column(Integer, default=900)
    enabled: Mapped[bool] = mapped_column(default=True)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AlertModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "alerts"
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_snapshots.id", ondelete="CASCADE")
    )
    alert_type: Mapped[str] = mapped_column(String(40))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InventoryItemModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "inventory_items"
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    source_observation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("listing_observations.id", ondelete="SET NULL")
    )
    serial_number: Mapped[str | None] = mapped_column(String(240))
    acquisition_price_cents: Mapped[int] = mapped_column(BigInteger)
    acquisition_costs: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict)
    condition_notes: Mapped[str] = mapped_column(String(4000), default="")
    disposition: Mapped[str] = mapped_column(String(40), default="IN_STOCK")


class TestRunModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "test_runs"
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_items.id", ondelete="CASCADE")
    )
    procedure_name: Mapped[str] = mapped_column(String(160))
    tool_name: Mapped[str] = mapped_column(String(160))
    duration_seconds: Mapped[int] = mapped_column(Integer)
    configuration: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    result: Mapped[str] = mapped_column(String(40))
    measured_values: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    notes: Mapped[str] = mapped_column(String(4000), default="")
    evidence_paths: Mapped[list[str]] = mapped_column(JSONB, default=list)


class JobRunModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "job_runs"
    idempotency_key: Mapped[str] = mapped_column(String(240), unique=True)
    job_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(120))
    last_error_message: Mapped[str | None] = mapped_column(String(500))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExtensionPairingModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "extension_pairings"
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    extension_origin: Mapped[str] = mapped_column(String(240))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
