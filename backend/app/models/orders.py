from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import PurchaseOrderStatus, SalesOrderStatus
from app.db.base import Base
from app.models.base import TimestampMixin, UuidPrimaryKeyMixin


class SalesOrder(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sales_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'confirmed', 'processing', 'completed', 'cancelled')",
            name="ck_sales_orders_status",
        ),
        Index("ix_sales_orders_status_created", "status", "created_at"),
        Index("ix_sales_orders_partner_created", "partner_id", "created_at"),
    )

    order_number: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("partners.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    status: Mapped[SalesOrderStatus] = mapped_column(
        Enum(
            SalesOrderStatus,
            name="sales_order_status",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
            create_constraint=False,
        ),
        index=True,
        default=SalesOrderStatus.DRAFT,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), default="PLN", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    partner: Mapped[Partner] = relationship()
    warehouse: Mapped[Warehouse] = relationship(foreign_keys=[warehouse_id])
    lines: Mapped[list[SalesOrderLine]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="SalesOrderLine.id"
    )

    @property
    def total_amount(self) -> Decimal:
        return sum(
            (line.quantity * line.unit_price for line in self.lines),
            start=Decimal("0"),
        )


class SalesOrderLine(UuidPrimaryKeyMixin, Base):
    __tablename__ = "sales_order_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_sales_order_lines_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_sales_order_lines_price_nonnegative"),
        UniqueConstraint("order_id", "product_id", name="uq_sales_order_line_product"),
    )

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("sales_orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped[SalesOrder] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship()


class PurchaseOrder(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'ordered', 'received', 'cancelled')",
            name="ck_purchase_orders_status",
        ),
        Index("ix_purchase_orders_status_created", "status", "created_at"),
        Index("ix_purchase_orders_partner_created", "partner_id", "created_at"),
    )

    order_number: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("partners.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        Enum(
            PurchaseOrderStatus,
            name="purchase_order_status",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
            create_constraint=False,
        ),
        index=True,
        default=PurchaseOrderStatus.DRAFT,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), default="PLN", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    partner: Mapped[Partner] = relationship()
    warehouse: Mapped[Warehouse] = relationship(foreign_keys=[warehouse_id])
    lines: Mapped[list[PurchaseOrderLine]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="PurchaseOrderLine.id"
    )

    @property
    def total_amount(self) -> Decimal:
        return sum(
            (line.quantity * line.unit_cost for line in self.lines),
            start=Decimal("0"),
        )


class PurchaseOrderLine(UuidPrimaryKeyMixin, Base):
    __tablename__ = "purchase_order_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_purchase_order_lines_quantity_positive"),
        CheckConstraint("unit_cost >= 0", name="ck_purchase_order_lines_cost_nonnegative"),
        UniqueConstraint("order_id", "product_id", name="uq_purchase_order_line_product"),
    )

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped[PurchaseOrder] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship()


from app.models.partner import Partner  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.models.warehouse import Warehouse  # noqa: E402
