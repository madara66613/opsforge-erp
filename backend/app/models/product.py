from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UuidPrimaryKeyMixin


class Product(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("sale_price >= 0", name="ck_products_sale_price_nonnegative"),
        CheckConstraint("purchase_price >= 0", name="ck_products_purchase_price_nonnegative"),
        CheckConstraint("reorder_threshold >= 0", name="ck_products_reorder_threshold_nonnegative"),
        Index("ix_products_name", "name"),
        Index("ix_products_active_name", "is_active", "name"),
    )

    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(String(24), default="pcs", nullable=False)
    sale_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    purchase_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    reorder_threshold: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), default=Decimal("5"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
