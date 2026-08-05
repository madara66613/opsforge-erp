from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.core.enums import AuditOutcome, PurchaseOrderStatus, SalesOrderStatus, StockMovementType


class DashboardCounts(BaseModel):
    active_products: int
    active_warehouses: int
    active_partners: int
    pending_sales_orders: int
    pending_purchase_orders: int
    low_stock_balances: int


class RecentOrder(BaseModel):
    id: UUID
    order_number: str
    partner_name: str
    status: SalesOrderStatus | PurchaseOrderStatus
    total_amount: Decimal
    created_at: datetime


class RecentMovement(BaseModel):
    id: UUID
    movement_type: StockMovementType
    product_sku: str
    warehouse_code: str
    quantity: Decimal
    created_at: datetime


class RecentAuditEvent(BaseModel):
    id: UUID
    action: str
    entity_type: str
    outcome: AuditOutcome
    created_at: datetime


class DashboardSummary(BaseModel):
    counts: DashboardCounts
    inventory_value: Decimal
    pending_sales_value: Decimal
    recent_sales_orders: list[RecentOrder]
    recent_purchase_orders: list[RecentOrder]
    recent_movements: list[RecentMovement]
    recent_audit_events: list[RecentAuditEvent]
