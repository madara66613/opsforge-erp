"""Add product replenishment thresholds and expected purchase delivery dates.

Revision ID: 0004_replenishment_fields
Revises: 0003_partners_orders
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_replenishment_fields"
down_revision: str | None = "0003_partners_orders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "reorder_threshold",
            sa.Numeric(precision=14, scale=3),
            server_default="5",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_products_reorder_threshold_nonnegative",
        "products",
        "reorder_threshold >= 0",
    )
    op.add_column(
        "purchase_orders",
        sa.Column("expected_delivery_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("purchase_orders", "expected_delivery_date")
    op.drop_constraint(
        "ck_products_reorder_threshold_nonnegative",
        "products",
        type_="check",
    )
    op.drop_column("products", "reorder_threshold")
