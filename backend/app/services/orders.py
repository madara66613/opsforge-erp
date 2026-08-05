from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import (
    PartnerType,
    PurchaseOrderStatus,
    SalesOrderStatus,
    StockMovementType,
)
from app.models.orders import (
    PurchaseOrder,
    PurchaseOrderLine,
    SalesOrder,
    SalesOrderLine,
)
from app.models.partner import Partner
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.schemas.inventory import ProductReference, StockMovementCreate, WarehouseReference
from app.schemas.orders import (
    PurchaseOrderCreate,
    PurchaseOrderLinePublic,
    PurchaseOrderPublic,
    SalesOrderCreate,
    SalesOrderLinePublic,
    SalesOrderPublic,
)
from app.schemas.partner import PartnerReference
from app.services.errors import DomainError, EntityNotFoundError
from app.services.idempotency import claim_or_replay
from app.services.inventory import apply_stock_movement

SALES_LOAD_OPTIONS = (
    joinedload(SalesOrder.partner),
    joinedload(SalesOrder.warehouse),
    selectinload(SalesOrder.lines).joinedload(SalesOrderLine.product),
)
PURCHASE_LOAD_OPTIONS = (
    joinedload(PurchaseOrder.partner),
    joinedload(PurchaseOrder.warehouse),
    selectinload(PurchaseOrder.lines).joinedload(PurchaseOrderLine.product),
)


def _order_number(prefix: str) -> str:
    return f"{prefix}-{datetime.now(UTC):%Y%m%d}-{uuid4().hex[:8].upper()}"


def _require_partner(session: Session, partner_id: UUID, allowed: set[PartnerType]) -> Partner:
    partner = session.get(Partner, partner_id)
    if partner is None:
        raise EntityNotFoundError("Partner")
    if not partner.is_active:
        raise DomainError("Partner is inactive", code="inactive_partner")
    if partner.partner_type not in allowed:
        raise DomainError("Partner type is not valid for this order", code="invalid_partner_type")
    return partner


def _require_warehouse(session: Session, warehouse_id: UUID) -> Warehouse:
    warehouse = session.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise EntityNotFoundError("Warehouse")
    if not warehouse.is_active:
        raise DomainError("Warehouse is inactive", code="inactive_warehouse")
    return warehouse


def _load_products(session: Session, product_ids: list[UUID]) -> dict[UUID, Product]:
    products = {
        product.id: product
        for product in session.scalars(select(Product).where(Product.id.in_(product_ids)))
    }
    if len(products) != len(product_ids):
        raise EntityNotFoundError("Product")
    if any(not product.is_active for product in products.values()):
        raise DomainError("Order contains an inactive product", code="inactive_product")
    return products


def create_sales_order(
    session: Session, payload: SalesOrderCreate, *, actor_user_id: UUID
) -> SalesOrder:
    partner = _require_partner(
        session, payload.partner_id, {PartnerType.CUSTOMER, PartnerType.BOTH}
    )
    warehouse = _require_warehouse(session, payload.warehouse_id)
    products = _load_products(session, [line.product_id for line in payload.lines])
    order = SalesOrder(
        order_number=_order_number("SO"),
        partner=partner,
        warehouse=warehouse,
        status=SalesOrderStatus.DRAFT,
        notes=payload.notes.strip() if payload.notes else None,
        created_by_user_id=actor_user_id,
    )
    order.lines = [
        SalesOrderLine(
            product=products[line.product_id],
            quantity=line.quantity,
            unit_price=line.unit_price
            if line.unit_price is not None
            else products[line.product_id].sale_price,
        )
        for line in payload.lines
    ]
    session.add(order)
    session.flush()
    return order


def create_purchase_order(
    session: Session, payload: PurchaseOrderCreate, *, actor_user_id: UUID
) -> PurchaseOrder:
    partner = _require_partner(
        session, payload.partner_id, {PartnerType.SUPPLIER, PartnerType.BOTH}
    )
    warehouse = _require_warehouse(session, payload.warehouse_id)
    products = _load_products(session, [line.product_id for line in payload.lines])
    order = PurchaseOrder(
        order_number=_order_number("PO"),
        partner=partner,
        warehouse=warehouse,
        status=PurchaseOrderStatus.DRAFT,
        notes=payload.notes.strip() if payload.notes else None,
        expected_delivery_date=payload.expected_delivery_date,
        created_by_user_id=actor_user_id,
    )
    order.lines = [
        PurchaseOrderLine(
            product=products[line.product_id],
            quantity=line.quantity,
            unit_cost=line.unit_cost
            if line.unit_cost is not None
            else products[line.product_id].purchase_price,
        )
        for line in payload.lines
    ]
    session.add(order)
    session.flush()
    return order


def get_sales_order(session: Session, order_id: UUID, *, for_update: bool = False) -> SalesOrder:
    statement = select(SalesOrder).options(*SALES_LOAD_OPTIONS).where(SalesOrder.id == order_id)
    if for_update:
        statement = statement.with_for_update(of=SalesOrder)
    order = session.scalar(statement)
    if order is None:
        raise EntityNotFoundError("Sales order")
    return order


def get_purchase_order(
    session: Session, order_id: UUID, *, for_update: bool = False
) -> PurchaseOrder:
    statement = (
        select(PurchaseOrder).options(*PURCHASE_LOAD_OPTIONS).where(PurchaseOrder.id == order_id)
    )
    if for_update:
        statement = statement.with_for_update(of=PurchaseOrder)
    order = session.scalar(statement)
    if order is None:
        raise EntityNotFoundError("Purchase order")
    return order


def confirm_sales_order(session: Session, order_id: UUID) -> SalesOrder:
    order = get_sales_order(session, order_id, for_update=True)
    if order.status == SalesOrderStatus.CONFIRMED:
        return order
    if order.status != SalesOrderStatus.DRAFT:
        raise DomainError("Only draft sales orders can be confirmed", code="invalid_order_status")
    order.status = SalesOrderStatus.CONFIRMED
    order.confirmed_at = datetime.now(UTC)
    return order


def start_sales_processing(session: Session, order_id: UUID) -> SalesOrder:
    order = get_sales_order(session, order_id, for_update=True)
    if order.status == SalesOrderStatus.PROCESSING:
        return order
    if order.status != SalesOrderStatus.CONFIRMED:
        raise DomainError(
            "Only confirmed sales orders can start processing", code="invalid_order_status"
        )
    order.status = SalesOrderStatus.PROCESSING
    order.processing_at = datetime.now(UTC)
    return order


def complete_sales_order(
    session: Session,
    order_id: UUID,
    *,
    actor_user_id: UUID,
    idempotency_key: str,
) -> tuple[SalesOrder, bool]:
    order = get_sales_order(session, order_id, for_update=True)
    replayed = claim_or_replay(
        session,
        operation="sales_order.complete",
        idempotency_key=idempotency_key,
        resource_id=order.id,
        actor_user_id=actor_user_id,
    )
    if replayed:
        return order, True
    if order.status not in {SalesOrderStatus.CONFIRMED, SalesOrderStatus.PROCESSING}:
        raise DomainError(
            "Only confirmed or processing sales orders can be completed",
            code="invalid_order_status",
        )

    for line in order.lines:
        apply_stock_movement(
            session,
            StockMovementCreate(
                movement_type=StockMovementType.SALE_ISSUE,
                product_id=line.product_id,
                warehouse_id=order.warehouse_id,
                quantity=line.quantity,
                reference=order.order_number,
                notes="Generated by sales order completion",
            ),
            actor_user_id=actor_user_id,
        )
    order.status = SalesOrderStatus.COMPLETED
    order.completed_at = datetime.now(UTC)
    return order, False


def cancel_sales_order(session: Session, order_id: UUID) -> SalesOrder:
    order = get_sales_order(session, order_id, for_update=True)
    if order.status == SalesOrderStatus.CANCELLED:
        return order
    if order.status == SalesOrderStatus.COMPLETED:
        raise DomainError("Completed sales orders cannot be cancelled", code="invalid_order_status")
    order.status = SalesOrderStatus.CANCELLED
    order.cancelled_at = datetime.now(UTC)
    return order


def order_purchase(session: Session, order_id: UUID) -> PurchaseOrder:
    order = get_purchase_order(session, order_id, for_update=True)
    if order.status == PurchaseOrderStatus.ORDERED:
        return order
    if order.status != PurchaseOrderStatus.DRAFT:
        raise DomainError("Only draft purchase orders can be ordered", code="invalid_order_status")
    order.status = PurchaseOrderStatus.ORDERED
    order.ordered_at = datetime.now(UTC)
    return order


def receive_purchase_order(
    session: Session,
    order_id: UUID,
    *,
    actor_user_id: UUID,
    idempotency_key: str,
) -> tuple[PurchaseOrder, bool]:
    order = get_purchase_order(session, order_id, for_update=True)
    replayed = claim_or_replay(
        session,
        operation="purchase_order.receive",
        idempotency_key=idempotency_key,
        resource_id=order.id,
        actor_user_id=actor_user_id,
    )
    if replayed:
        return order, True
    if order.status != PurchaseOrderStatus.ORDERED:
        raise DomainError(
            "Only ordered purchase orders can be received", code="invalid_order_status"
        )

    for line in order.lines:
        apply_stock_movement(
            session,
            StockMovementCreate(
                movement_type=StockMovementType.RECEIPT,
                product_id=line.product_id,
                warehouse_id=order.warehouse_id,
                quantity=line.quantity,
                unit_cost=line.unit_cost,
                reference=order.order_number,
                notes="Generated by purchase order receipt",
            ),
            actor_user_id=actor_user_id,
        )
    order.status = PurchaseOrderStatus.RECEIVED
    order.received_at = datetime.now(UTC)
    return order, False


def cancel_purchase_order(session: Session, order_id: UUID) -> PurchaseOrder:
    order = get_purchase_order(session, order_id, for_update=True)
    if order.status == PurchaseOrderStatus.CANCELLED:
        return order
    if order.status == PurchaseOrderStatus.RECEIVED:
        raise DomainError(
            "Received purchase orders cannot be cancelled", code="invalid_order_status"
        )
    order.status = PurchaseOrderStatus.CANCELLED
    order.cancelled_at = datetime.now(UTC)
    return order


def sales_order_public(order: SalesOrder) -> SalesOrderPublic:
    return SalesOrderPublic(
        id=order.id,
        order_number=order.order_number,
        partner=PartnerReference.model_validate(order.partner, from_attributes=True),
        warehouse=WarehouseReference.model_validate(order.warehouse, from_attributes=True),
        status=order.status,
        currency=order.currency,
        notes=order.notes,
        created_by_user_id=order.created_by_user_id,
        confirmed_at=order.confirmed_at,
        processing_at=order.processing_at,
        completed_at=order.completed_at,
        cancelled_at=order.cancelled_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
        total_amount=order.total_amount,
        lines=[
            SalesOrderLinePublic(
                id=line.id,
                product=ProductReference.model_validate(line.product, from_attributes=True),
                quantity=line.quantity,
                unit_price=line.unit_price,
                line_total=line.quantity * line.unit_price,
            )
            for line in order.lines
        ],
    )


def purchase_order_public(order: PurchaseOrder) -> PurchaseOrderPublic:
    return PurchaseOrderPublic(
        id=order.id,
        order_number=order.order_number,
        partner=PartnerReference.model_validate(order.partner, from_attributes=True),
        warehouse=WarehouseReference.model_validate(order.warehouse, from_attributes=True),
        status=order.status,
        currency=order.currency,
        notes=order.notes,
        expected_delivery_date=order.expected_delivery_date,
        created_by_user_id=order.created_by_user_id,
        ordered_at=order.ordered_at,
        received_at=order.received_at,
        cancelled_at=order.cancelled_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
        total_amount=order.total_amount,
        lines=[
            PurchaseOrderLinePublic(
                id=line.id,
                product=ProductReference.model_validate(line.product, from_attributes=True),
                quantity=line.quantity,
                unit_cost=line.unit_cost,
                line_total=line.quantity * line.unit_cost,
            )
            for line in order.lines
        ],
    )
