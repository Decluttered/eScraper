import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.domain.enums import ProductCategory


class ProductModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("manufacturer", "canonical_model", "variant", name="uq_product_variant"),
    )

    category: Mapped[ProductCategory]
    manufacturer: Mapped[str] = mapped_column(String(120))
    canonical_model: Mapped[str] = mapped_column(String(160))
    variant: Mapped[str] = mapped_column(String(120), default="")
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    ean: Mapped[str | None] = mapped_column(String(32))
    mpn: Mapped[str | None] = mapped_column(String(120))
    ebay_product_id: Mapped[str | None] = mapped_column(String(120))
    windows_11_status: Mapped[str | None] = mapped_column(String(40))


class ProductAliasModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "product_aliases"
    __table_args__ = (UniqueConstraint("normalized_alias", name="uq_product_alias"),)

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    normalized_alias: Mapped[str] = mapped_column(String(240))
    required_tokens: Mapped[list[str]] = mapped_column(JSONB, default=list)
    excluded_tokens: Mapped[list[str]] = mapped_column(JSONB, default=list)
