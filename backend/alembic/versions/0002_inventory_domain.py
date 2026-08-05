"""Create products, warehouses, inventory balances, and stock movements.

Revision ID: 0002_inventory_domain
Revises: 0001_auth_and_audit
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_inventory_domain"
down_revision: str | None = "0001_auth_and_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=24), nullable=False),
        sa.Column("sale_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("purchase_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("purchase_price >= 0", name="ck_products_purchase_price_nonnegative"),
        sa.CheckConstraint("sale_price >= 0", name="ck_products_sale_price_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_active_name", "products", ["is_active", "name"])
    op.create_index("ix_products_name", "products", ["name"])
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)

    op.create_table(
        "warehouses",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("location", sa.String(length=240), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_warehouses_active_name", "warehouses", ["is_active", "name"])
    op.create_index("ix_warehouses_code", "warehouses", ["code"], unique=True)
    op.create_index("ix_warehouses_name", "warehouses", ["name"])

    op.create_table(
        "inventory_balances",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "warehouse_id", name="uq_inventory_product_warehouse"),
    )
    op.create_index("ix_inventory_balances_product_id", "inventory_balances", ["product_id"])
    op.create_index("ix_inventory_balances_warehouse_id", "inventory_balances", ["warehouse_id"])
    op.create_index(
        "ix_inventory_product_quantity", "inventory_balances", ["product_id", "quantity"]
    )
    op.create_index(
        "ix_inventory_warehouse_quantity", "inventory_balances", ["warehouse_id", "quantity"]
    )

    op.create_table(
        "stock_movements",
        sa.Column(
            "movement_type",
            sa.Enum(
                "receipt",
                "sale_issue",
                "transfer",
                "return",
                "adjustment",
                name="stock_movement_type",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("destination_warehouse_id", sa.Uuid(), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("allow_negative_override", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "(movement_type = 'adjustment' AND quantity <> 0) OR "
            "(movement_type <> 'adjustment' AND quantity > 0)",
            name="ck_stock_movements_quantity",
        ),
        sa.CheckConstraint(
            "(movement_type = 'transfer' AND destination_warehouse_id IS NOT NULL "
            "AND destination_warehouse_id <> warehouse_id) OR "
            "(movement_type <> 'transfer' AND destination_warehouse_id IS NULL)",
            name="ck_stock_movements_transfer_destination",
        ),
        sa.CheckConstraint(
            "movement_type IN ('receipt', 'sale_issue', 'transfer', 'return', 'adjustment')",
            name="ck_stock_movements_type",
        ),
        sa.CheckConstraint(
            "unit_cost IS NULL OR unit_cost >= 0",
            name="ck_stock_movements_unit_cost_nonnegative",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["destination_warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_movements_created_at", "stock_movements", ["created_at"])
    op.create_index(
        "ix_stock_movements_created_by_user_id", "stock_movements", ["created_by_user_id"]
    )
    op.create_index(
        "ix_stock_movements_destination_warehouse_id",
        "stock_movements",
        ["destination_warehouse_id"],
    )
    op.create_index("ix_stock_movements_movement_type", "stock_movements", ["movement_type"])
    op.create_index(
        "ix_stock_movements_product_created",
        "stock_movements",
        ["product_id", "created_at"],
    )
    op.create_index("ix_stock_movements_product_id", "stock_movements", ["product_id"])
    op.create_index("ix_stock_movements_reference", "stock_movements", ["reference"])
    op.create_index(
        "ix_stock_movements_warehouse_created",
        "stock_movements",
        ["warehouse_id", "created_at"],
    )
    op.create_index("ix_stock_movements_warehouse_id", "stock_movements", ["warehouse_id"])


def downgrade() -> None:
    op.drop_table("stock_movements")
    op.drop_table("inventory_balances")
    op.drop_table("warehouses")
    op.drop_table("products")
