from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, require_permission
from app.core.enums import AuditOutcome, PurchaseOrderStatus, SalesOrderStatus
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.orders import PurchaseOrder, SalesOrder
from app.models.partner import Partner
from app.schemas.orders import (
    PurchaseOrderCreate,
    PurchaseOrderList,
    PurchaseOrderPublic,
    SalesOrderCreate,
    SalesOrderList,
    SalesOrderPublic,
)
from app.services.audit import record_audit_event
from app.services.errors import DomainError
from app.services.orders import (
    PURCHASE_LOAD_OPTIONS,
    SALES_LOAD_OPTIONS,
    cancel_purchase_order,
    cancel_sales_order,
    complete_sales_order,
    confirm_sales_order,
    create_purchase_order,
    create_sales_order,
    get_purchase_order,
    get_sales_order,
    order_purchase,
    purchase_order_public,
    receive_purchase_order,
    sales_order_public,
    start_sales_processing,
)

router = APIRouter(tags=["orders"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CanReadSales = Annotated[AuthContext, Depends(require_permission(Permission.SALES_READ))]
CanWriteSales = Annotated[AuthContext, Depends(require_permission(Permission.SALES_WRITE))]
CanReadPurchases = Annotated[AuthContext, Depends(require_permission(Permission.PURCHASES_READ))]
CanWritePurchases = Annotated[AuthContext, Depends(require_permission(Permission.PURCHASES_WRITE))]
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
        description="Unique key used to safely replay stock-changing order operations",
    ),
]


def _audit_failure(
    session: Session,
    *,
    actor_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID,
    request_id: str,
    error: DomainError,
) -> None:
    record_audit_event(
        session,
        actor_user_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        outcome=AuditOutcome.FAILURE,
        request_id=request_id,
        details={"reason": error.code, **error.details},
    )
    session.commit()


@router.get("/sales-orders", response_model=SalesOrderList)
def list_sales_orders(
    session: DatabaseSession,
    _auth: CanReadSales,
    search: str | None = None,
    order_status: Annotated[SalesOrderStatus | None, Query(alias="status")] = None,
    partner_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    sort_by: Literal["order_number", "created_at", "status"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SalesOrderList:
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(SalesOrder.order_number.ilike(pattern), Partner.name.ilike(pattern)))
    if order_status:
        filters.append(SalesOrder.status == order_status)
    if partner_id:
        filters.append(SalesOrder.partner_id == partner_id)
    if warehouse_id:
        filters.append(SalesOrder.warehouse_id == warehouse_id)

    total = (
        session.scalar(
            select(func.count())
            .select_from(SalesOrder)
            .join(Partner, Partner.id == SalesOrder.partner_id)
            .where(*filters)
        )
        or 0
    )
    sort_columns = {
        "order_number": SalesOrder.order_number,
        "created_at": SalesOrder.created_at,
        "status": SalesOrder.status,
    }
    direction = asc if sort_order == "asc" else desc
    orders = list(
        session.scalars(
            select(SalesOrder)
            .join(Partner, Partner.id == SalesOrder.partner_id)
            .options(*SALES_LOAD_OPTIONS)
            .where(*filters)
            .order_by(direction(sort_columns[sort_by]), SalesOrder.id)
            .limit(limit)
            .offset(offset)
        )
    )
    return SalesOrderList(
        items=[sales_order_public(order) for order in orders],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/sales-orders", response_model=SalesOrderPublic, status_code=status.HTTP_201_CREATED)
def create_sales(
    payload: SalesOrderCreate,
    request: Request,
    session: DatabaseSession,
    auth: CanWriteSales,
) -> SalesOrderPublic:
    actor_id = auth.user.id
    try:
        order = create_sales_order(session, payload, actor_user_id=actor_id)
    except DomainError as exc:
        session.rollback()
        _audit_failure(
            session,
            actor_id=actor_id,
            action="sales_order.create",
            entity_type="sales_order",
            entity_id=payload.partner_id,
            request_id=request.state.request_id,
            error=exc,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    record_audit_event(
        session,
        actor_user_id=actor_id,
        action="sales_order.create",
        entity_type="sales_order",
        entity_id=str(order.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={"order_number": order.order_number, "line_count": len(order.lines)},
    )
    session.commit()
    return sales_order_public(order)


@router.get("/sales-orders/{order_id}", response_model=SalesOrderPublic)
def get_sales(
    order_id: UUID,
    session: DatabaseSession,
    _auth: CanReadSales,
) -> SalesOrderPublic:
    try:
        return sales_order_public(get_sales_order(session, order_id))
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/sales-orders/{order_id}/confirm", response_model=SalesOrderPublic)
def confirm_sales(
    order_id: UUID,
    request: Request,
    session: DatabaseSession,
    auth: CanWriteSales,
) -> SalesOrderPublic:
    return _transition_sales(
        order_id,
        request,
        session,
        auth,
        action="sales_order.confirm",
        transition=confirm_sales_order,
    )


@router.post("/sales-orders/{order_id}/process", response_model=SalesOrderPublic)
def process_sales(
    order_id: UUID,
    request: Request,
    session: DatabaseSession,
    auth: CanWriteSales,
) -> SalesOrderPublic:
    return _transition_sales(
        order_id,
        request,
        session,
        auth,
        action="sales_order.process",
        transition=start_sales_processing,
    )


@router.post("/sales-orders/{order_id}/cancel", response_model=SalesOrderPublic)
def cancel_sales(
    order_id: UUID,
    request: Request,
    session: DatabaseSession,
    auth: CanWriteSales,
) -> SalesOrderPublic:
    return _transition_sales(
        order_id,
        request,
        session,
        auth,
        action="sales_order.cancel",
        transition=cancel_sales_order,
    )


def _transition_sales(
    order_id: UUID,
    request: Request,
    session: Session,
    auth: AuthContext,
    *,
    action: str,
    transition: Callable[[Session, UUID], SalesOrder],
) -> SalesOrderPublic:
    actor_id = auth.user.id
    try:
        order = transition(session, order_id)
    except DomainError as exc:
        session.rollback()
        _audit_failure(
            session,
            actor_id=actor_id,
            action=action,
            entity_type="sales_order",
            entity_id=order_id,
            request_id=request.state.request_id,
            error=exc,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    record_audit_event(
        session,
        actor_user_id=actor_id,
        action=action,
        entity_type="sales_order",
        entity_id=str(order.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={"status": order.status.value},
    )
    session.commit()
    return sales_order_public(order)


@router.post("/sales-orders/{order_id}/complete", response_model=SalesOrderPublic)
def complete_sales(
    order_id: UUID,
    request: Request,
    response: Response,
    idempotency_key: IdempotencyKey,
    session: DatabaseSession,
    auth: CanWriteSales,
) -> SalesOrderPublic:
    actor_id = auth.user.id
    try:
        order, replayed = complete_sales_order(
            session,
            order_id,
            actor_user_id=actor_id,
            idempotency_key=idempotency_key,
        )
    except DomainError as exc:
        session.rollback()
        _audit_failure(
            session,
            actor_id=actor_id,
            action="sales_order.complete",
            entity_type="sales_order",
            entity_id=order_id,
            request_id=request.state.request_id,
            error=exc,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    record_audit_event(
        session,
        actor_user_id=actor_id,
        action="sales_order.complete",
        entity_type="sales_order",
        entity_id=str(order.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={"status": order.status.value, "idempotent_replay": replayed},
    )
    session.commit()
    response.headers["X-Idempotent-Replay"] = str(replayed).lower()
    return sales_order_public(order)


@router.get("/purchase-orders", response_model=PurchaseOrderList)
def list_purchase_orders(
    session: DatabaseSession,
    _auth: CanReadPurchases,
    search: str | None = None,
    order_status: Annotated[PurchaseOrderStatus | None, Query(alias="status")] = None,
    partner_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    sort_by: Literal["order_number", "created_at", "status"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PurchaseOrderList:
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(PurchaseOrder.order_number.ilike(pattern), Partner.name.ilike(pattern)))
    if order_status:
        filters.append(PurchaseOrder.status == order_status)
    if partner_id:
        filters.append(PurchaseOrder.partner_id == partner_id)
    if warehouse_id:
        filters.append(PurchaseOrder.warehouse_id == warehouse_id)

    total = (
        session.scalar(
            select(func.count())
            .select_from(PurchaseOrder)
            .join(Partner, Partner.id == PurchaseOrder.partner_id)
            .where(*filters)
        )
        or 0
    )
    sort_columns = {
        "order_number": PurchaseOrder.order_number,
        "created_at": PurchaseOrder.created_at,
        "status": PurchaseOrder.status,
    }
    direction = asc if sort_order == "asc" else desc
    orders = list(
        session.scalars(
            select(PurchaseOrder)
            .join(Partner, Partner.id == PurchaseOrder.partner_id)
            .options(*PURCHASE_LOAD_OPTIONS)
            .where(*filters)
            .order_by(direction(sort_columns[sort_by]), PurchaseOrder.id)
            .limit(limit)
            .offset(offset)
        )
    )
    return PurchaseOrderList(
        items=[purchase_order_public(order) for order in orders],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/purchase-orders",
    response_model=PurchaseOrderPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_purchase(
    payload: PurchaseOrderCreate,
    request: Request,
    session: DatabaseSession,
    auth: CanWritePurchases,
) -> PurchaseOrderPublic:
    actor_id = auth.user.id
    try:
        order = create_purchase_order(session, payload, actor_user_id=actor_id)
    except DomainError as exc:
        session.rollback()
        _audit_failure(
            session,
            actor_id=actor_id,
            action="purchase_order.create",
            entity_type="purchase_order",
            entity_id=payload.partner_id,
            request_id=request.state.request_id,
            error=exc,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    record_audit_event(
        session,
        actor_user_id=actor_id,
        action="purchase_order.create",
        entity_type="purchase_order",
        entity_id=str(order.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={"order_number": order.order_number, "line_count": len(order.lines)},
    )
    session.commit()
    return purchase_order_public(order)


@router.get("/purchase-orders/{order_id}", response_model=PurchaseOrderPublic)
def get_purchase(
    order_id: UUID,
    session: DatabaseSession,
    _auth: CanReadPurchases,
) -> PurchaseOrderPublic:
    try:
        return purchase_order_public(get_purchase_order(session, order_id))
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/purchase-orders/{order_id}/order", response_model=PurchaseOrderPublic)
def submit_purchase(
    order_id: UUID,
    request: Request,
    session: DatabaseSession,
    auth: CanWritePurchases,
) -> PurchaseOrderPublic:
    return _transition_purchase(
        order_id,
        request,
        session,
        auth,
        action="purchase_order.order",
        transition=order_purchase,
    )


@router.post("/purchase-orders/{order_id}/cancel", response_model=PurchaseOrderPublic)
def cancel_purchase(
    order_id: UUID,
    request: Request,
    session: DatabaseSession,
    auth: CanWritePurchases,
) -> PurchaseOrderPublic:
    return _transition_purchase(
        order_id,
        request,
        session,
        auth,
        action="purchase_order.cancel",
        transition=cancel_purchase_order,
    )


def _transition_purchase(
    order_id: UUID,
    request: Request,
    session: Session,
    auth: AuthContext,
    *,
    action: str,
    transition: Callable[[Session, UUID], PurchaseOrder],
) -> PurchaseOrderPublic:
    actor_id = auth.user.id
    try:
        order = transition(session, order_id)
    except DomainError as exc:
        session.rollback()
        _audit_failure(
            session,
            actor_id=actor_id,
            action=action,
            entity_type="purchase_order",
            entity_id=order_id,
            request_id=request.state.request_id,
            error=exc,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    record_audit_event(
        session,
        actor_user_id=actor_id,
        action=action,
        entity_type="purchase_order",
        entity_id=str(order.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={"status": order.status.value},
    )
    session.commit()
    return purchase_order_public(order)


@router.post("/purchase-orders/{order_id}/receive", response_model=PurchaseOrderPublic)
def receive_purchase(
    order_id: UUID,
    request: Request,
    response: Response,
    idempotency_key: IdempotencyKey,
    session: DatabaseSession,
    auth: CanWritePurchases,
) -> PurchaseOrderPublic:
    actor_id = auth.user.id
    try:
        order, replayed = receive_purchase_order(
            session,
            order_id,
            actor_user_id=actor_id,
            idempotency_key=idempotency_key,
        )
    except DomainError as exc:
        session.rollback()
        _audit_failure(
            session,
            actor_id=actor_id,
            action="purchase_order.receive",
            entity_type="purchase_order",
            entity_id=order_id,
            request_id=request.state.request_id,
            error=exc,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    record_audit_event(
        session,
        actor_user_id=actor_id,
        action="purchase_order.receive",
        entity_type="purchase_order",
        entity_id=str(order.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={"status": order.status.value, "idempotent_replay": replayed},
    )
    session.commit()
    response.headers["X-Idempotent-Replay"] = str(replayed).lower()
    return purchase_order_public(order)
