"""Create partners, sales and purchase orders, and idempotency records.

Revision ID: 0003_partners_orders
Revises: 0002_inventory_domain
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_partners_orders"
down_revision: str | None = "0002_inventory_domain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "partners",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column(
            "partner_type",
            sa.Enum(
                "customer",
                "supplier",
                "both",
                name="partner_type",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=60), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("tax_id", sa.String(length=60), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "partner_type IN ('customer', 'supplier', 'both')",
            name="ck_partners_type",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_partners_active_name", "partners", ["is_active", "name"])
    op.create_index("ix_partners_code", "partners", ["code"], unique=True)
    op.create_index("ix_partners_name", "partners", ["name"])
    op.create_index("ix_partners_partner_type", "partners", ["partner_type"])
    op.create_index("ix_partners_tax_id", "partners", ["tax_id"])

    op.create_table(
        "sales_orders",
        sa.Column("order_number", sa.String(length=40), nullable=False),
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "confirmed",
                "processing",
                "completed",
                "cancelled",
                name="sales_order_status",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'confirmed', 'processing', 'completed', 'cancelled')",
            name="ck_sales_orders_status",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_orders_created_by_user_id", "sales_orders", ["created_by_user_id"])
    op.create_index("ix_sales_orders_order_number", "sales_orders", ["order_number"], unique=True)
    op.create_index("ix_sales_orders_partner_created", "sales_orders", ["partner_id", "created_at"])
    op.create_index("ix_sales_orders_partner_id", "sales_orders", ["partner_id"])
    op.create_index("ix_sales_orders_status", "sales_orders", ["status"])
    op.create_index("ix_sales_orders_status_created", "sales_orders", ["status", "created_at"])
    op.create_index("ix_sales_orders_warehouse_id", "sales_orders", ["warehouse_id"])

    op.create_table(
        "sales_order_lines",
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_sales_order_lines_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_sales_order_lines_price_nonnegative"),
        sa.ForeignKeyConstraint(["order_id"], ["sales_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "product_id", name="uq_sales_order_line_product"),
    )
    op.create_index("ix_sales_order_lines_order_id", "sales_order_lines", ["order_id"])
    op.create_index("ix_sales_order_lines_product_id", "sales_order_lines", ["product_id"])

    op.create_table(
        "purchase_orders",
        sa.Column("order_number", sa.String(length=40), nullable=False),
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "ordered",
                "received",
                "cancelled",
                name="purchase_order_status",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'ordered', 'received', 'cancelled')",
            name="ck_purchase_orders_status",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_purchase_orders_created_by_user_id", "purchase_orders", ["created_by_user_id"]
    )
    op.create_index(
        "ix_purchase_orders_order_number", "purchase_orders", ["order_number"], unique=True
    )
    op.create_index(
        "ix_purchase_orders_partner_created", "purchase_orders", ["partner_id", "created_at"]
    )
    op.create_index("ix_purchase_orders_partner_id", "purchase_orders", ["partner_id"])
    op.create_index("ix_purchase_orders_status", "purchase_orders", ["status"])
    op.create_index(
        "ix_purchase_orders_status_created", "purchase_orders", ["status", "created_at"]
    )
    op.create_index("ix_purchase_orders_warehouse_id", "purchase_orders", ["warehouse_id"])

    op.create_table(
        "purchase_order_lines",
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_purchase_order_lines_quantity_positive"),
        sa.CheckConstraint("unit_cost >= 0", name="ck_purchase_order_lines_cost_nonnegative"),
        sa.ForeignKeyConstraint(["order_id"], ["purchase_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "product_id", name="uq_purchase_order_line_product"),
    )
    op.create_index("ix_purchase_order_lines_order_id", "purchase_order_lines", ["order_id"])
    op.create_index("ix_purchase_order_lines_product_id", "purchase_order_lines", ["product_id"])

    op.create_table(
        "idempotency_records",
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("operation", "idempotency_key", name="uq_idempotency_operation_key"),
    )
    op.create_index(
        "ix_idempotency_records_actor_user_id", "idempotency_records", ["actor_user_id"]
    )
    op.create_index("ix_idempotency_records_created_at", "idempotency_records", ["created_at"])
    op.create_index("ix_idempotency_records_resource_id", "idempotency_records", ["resource_id"])
    op.create_index("ix_idempotency_resource", "idempotency_records", ["operation", "resource_id"])


def downgrade() -> None:
    op.drop_table("idempotency_records")
    op.drop_table("purchase_order_lines")
    op.drop_table("purchase_orders")
    op.drop_table("sales_order_lines")
    op.drop_table("sales_orders")
    op.drop_table("partners")
