from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.api.dependencies import AuthContext, require_permission
from app.core.enums import PurchaseOrderStatus, SalesOrderStatus
from app.core.permissions import Permission
from app.db.base import Base
from app.db.session import get_db
from app.models.inventory import InventoryBalance, StockMovement
from app.models.orders import PurchaseOrder, SalesOrder, SalesOrderLine
from app.models.partner import Partner
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.schemas.dashboard import (
    DashboardCounts,
    DashboardSummary,
    RecentMovement,
    RecentOrder,
)
from app.schemas.orders import PurchaseOrderPublic, SalesOrderPublic
from app.services.orders import (
    PURCHASE_LOAD_OPTIONS,
    SALES_LOAD_OPTIONS,
    purchase_order_public,
    sales_order_public,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CanReadDashboard = Annotated[AuthContext, Depends(require_permission(Permission.DASHBOARD_READ))]


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    session: DatabaseSession,
    _auth: CanReadDashboard,
) -> DashboardSummary:
    active_products = _count(session, Product, Product.is_active.is_(True))
    active_warehouses = _count(session, Warehouse, Warehouse.is_active.is_(True))
    active_partners = _count(session, Partner, Partner.is_active.is_(True))
    pending_sales = _count(
        session,
        SalesOrder,
        SalesOrder.status.in_(
            [SalesOrderStatus.DRAFT, SalesOrderStatus.CONFIRMED, SalesOrderStatus.PROCESSING]
        ),
    )
    pending_purchases = _count(
        session,
        PurchaseOrder,
        PurchaseOrder.status.in_([PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.ORDERED]),
    )
    low_stock = int(
        session.scalar(
            select(func.count())
            .select_from(InventoryBalance)
            .join(Product, Product.id == InventoryBalance.product_id)
            .where(InventoryBalance.quantity <= Product.reorder_threshold)
        )
        or 0
    )

    inventory_value = session.scalar(
        select(func.coalesce(func.sum(InventoryBalance.quantity * Product.purchase_price), 0))
        .select_from(InventoryBalance)
        .join(Product, Product.id == InventoryBalance.product_id)
    )
    pending_sales_value = session.scalar(
        select(func.coalesce(func.sum(SalesOrderLine.quantity * SalesOrderLine.unit_price), 0))
        .select_from(SalesOrderLine)
        .join(SalesOrder, SalesOrder.id == SalesOrderLine.order_id)
        .where(
            SalesOrder.status.in_(
                [SalesOrderStatus.DRAFT, SalesOrderStatus.CONFIRMED, SalesOrderStatus.PROCESSING]
            )
        )
    )

    recent_sales = list(
        session.scalars(
            select(SalesOrder)
            .options(*SALES_LOAD_OPTIONS)
            .order_by(SalesOrder.created_at.desc())
            .limit(5)
        )
    )
    recent_purchases = list(
        session.scalars(
            select(PurchaseOrder)
            .options(*PURCHASE_LOAD_OPTIONS)
            .order_by(PurchaseOrder.created_at.desc())
            .limit(5)
        )
    )
    movement_rows = session.execute(
        select(StockMovement, Product.sku, Warehouse.code)
        .join(Product, Product.id == StockMovement.product_id)
        .join(Warehouse, Warehouse.id == StockMovement.warehouse_id)
        .order_by(StockMovement.created_at.desc())
        .limit(8)
    )

    return DashboardSummary(
        counts=DashboardCounts(
            active_products=active_products,
            active_warehouses=active_warehouses,
            active_partners=active_partners,
            pending_sales_orders=pending_sales,
            pending_purchase_orders=pending_purchases,
            low_stock_balances=low_stock,
        ),
        inventory_value=Decimal(inventory_value or 0),
        pending_sales_value=Decimal(pending_sales_value or 0),
        recent_sales_orders=[
            _recent_sales_order(sales_order_public(order)) for order in recent_sales
        ],
        recent_purchase_orders=[
            _recent_purchase_order(purchase_order_public(order)) for order in recent_purchases
        ],
        recent_movements=[
            RecentMovement(
                id=movement.id,
                movement_type=movement.movement_type,
                product_sku=sku,
                warehouse_code=warehouse_code,
                quantity=movement.quantity,
                created_at=movement.created_at,
            )
            for movement, sku, warehouse_code in movement_rows
        ],
    )


def _count(session: Session, model: type[Base], criterion: ColumnElement[bool]) -> int:
    return int(session.scalar(select(func.count()).select_from(model).where(criterion)) or 0)


def _recent_sales_order(order: SalesOrderPublic) -> RecentOrder:
    return RecentOrder(
        id=order.id,
        order_number=order.order_number,
        partner_name=order.partner.name,
        status=order.status,
        total_amount=order.total_amount,
        created_at=order.created_at,
    )


def _recent_purchase_order(order: PurchaseOrderPublic) -> RecentOrder:
    return RecentOrder(
        id=order.id,
        order_number=order.order_number,
        partner_name=order.partner.name,
        status=order.status,
        total_amount=order.total_amount,
        created_at=order.created_at,
    )
