from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import StockMovementType
from app.db.base import Base
from app.models.base import UuidPrimaryKeyMixin, utc_now


class InventoryBalance(UuidPrimaryKeyMixin, Base):
    __tablename__ = "inventory_balances"
    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", name="uq_inventory_product_warehouse"),
        Index("ix_inventory_warehouse_quantity", "warehouse_id", "quantity"),
        Index("ix_inventory_product_quantity", "product_id", "quantity"),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class StockMovement(UuidPrimaryKeyMixin, Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('receipt', 'sale_issue', 'transfer', 'return', 'adjustment')",
            name="ck_stock_movements_type",
        ),
        CheckConstraint(
            "(movement_type = 'adjustment' AND quantity <> 0) OR "
            "(movement_type <> 'adjustment' AND quantity > 0)",
            name="ck_stock_movements_quantity",
        ),
        CheckConstraint(
            "(movement_type = 'transfer' AND destination_warehouse_id IS NOT NULL "
            "AND destination_warehouse_id <> warehouse_id) OR "
            "(movement_type <> 'transfer' AND destination_warehouse_id IS NULL)",
            name="ck_stock_movements_transfer_destination",
        ),
        CheckConstraint(
            "unit_cost IS NULL OR unit_cost >= 0",
            name="ck_stock_movements_unit_cost_nonnegative",
        ),
        Index("ix_stock_movements_product_created", "product_id", "created_at"),
        Index("ix_stock_movements_warehouse_created", "warehouse_id", "created_at"),
    )

    movement_type: Mapped[StockMovementType] = mapped_column(
        Enum(
            StockMovementType,
            name="stock_movement_type",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
            create_constraint=False,
        ),
        index=True,
        nullable=False,
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    destination_warehouse_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    reference: Mapped[str | None] = mapped_column(String(100), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    allow_negative_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True, nullable=False
    )
