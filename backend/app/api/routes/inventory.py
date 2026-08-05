from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, require_permission
from app.core.enums import AuditOutcome, StockMovementType
from app.core.permissions import Permission, has_permission
from app.db.session import get_db
from app.models.inventory import InventoryBalance, StockMovement
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.schemas.inventory import (
    InventoryBalanceList,
    InventoryBalancePublic,
    InventoryOperationResult,
    ProductReference,
    StockMovementCreate,
    StockMovementList,
    StockMovementPublic,
    WarehouseReference,
)
from app.services.audit import record_audit_event
from app.services.errors import DomainError
from app.services.inventory import apply_stock_movement

router = APIRouter(prefix="/inventory", tags=["inventory"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CanReadInventory = Annotated[AuthContext, Depends(require_permission(Permission.INVENTORY_READ))]
CanWriteInventory = Annotated[AuthContext, Depends(require_permission(Permission.INVENTORY_WRITE))]


@router.get("", response_model=InventoryBalanceList)
def list_inventory(
    session: DatabaseSession,
    _auth: CanReadInventory,
    search: str | None = None,
    product_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    low_stock_threshold: Annotated[Decimal | None, Query(ge=0)] = None,
    sort_by: Literal["sku", "product", "warehouse", "quantity"] = "sku",
    sort_order: Literal["asc", "desc"] = "asc",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> InventoryBalanceList:
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Product.sku.ilike(pattern),
                Product.name.ilike(pattern),
                Warehouse.code.ilike(pattern),
                Warehouse.name.ilike(pattern),
            )
        )
    if product_id:
        filters.append(InventoryBalance.product_id == product_id)
    if warehouse_id:
        filters.append(InventoryBalance.warehouse_id == warehouse_id)
    if low_stock_threshold is not None:
        filters.append(InventoryBalance.quantity <= low_stock_threshold)

    base = (
        select(InventoryBalance, Product, Warehouse)
        .join(Product, Product.id == InventoryBalance.product_id)
        .join(Warehouse, Warehouse.id == InventoryBalance.warehouse_id)
        .where(*filters)
    )
    total = (
        session.scalar(
            select(func.count())
            .select_from(InventoryBalance)
            .join(Product, Product.id == InventoryBalance.product_id)
            .join(Warehouse, Warehouse.id == InventoryBalance.warehouse_id)
            .where(*filters)
        )
        or 0
    )
    sort_columns = {
        "sku": Product.sku,
        "product": Product.name,
        "warehouse": Warehouse.name,
        "quantity": InventoryBalance.quantity,
    }
    direction = asc if sort_order == "asc" else desc
    rows = session.execute(
        base.order_by(direction(sort_columns[sort_by]), InventoryBalance.id)
        .limit(limit)
        .offset(offset)
    )
    items = [
        InventoryBalancePublic(
            id=balance.id,
            product=ProductReference(
                id=product.id,
                sku=product.sku,
                name=product.name,
                unit=product.unit,
                reorder_threshold=product.reorder_threshold,
            ),
            warehouse=WarehouseReference(id=warehouse.id, code=warehouse.code, name=warehouse.name),
            quantity=balance.quantity,
            updated_at=balance.updated_at,
        )
        for balance, product, warehouse in rows
    ]
    return InventoryBalanceList(items=items, total=total, limit=limit, offset=offset)


@router.get("/movements", response_model=StockMovementList)
def list_stock_movements(
    session: DatabaseSession,
    _auth: CanReadInventory,
    movement_type: StockMovementType | None = None,
    product_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    reference: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> StockMovementList:
    filters = []
    if movement_type:
        filters.append(StockMovement.movement_type == movement_type)
    if product_id:
        filters.append(StockMovement.product_id == product_id)
    if warehouse_id:
        filters.append(
            or_(
                StockMovement.warehouse_id == warehouse_id,
                StockMovement.destination_warehouse_id == warehouse_id,
            )
        )
    if reference:
        filters.append(StockMovement.reference.ilike(f"%{reference.strip()}%"))

    total = session.scalar(select(func.count()).select_from(StockMovement).where(*filters)) or 0
    movements = list(
        session.scalars(
            select(StockMovement)
            .where(*filters)
            .order_by(StockMovement.created_at.desc(), StockMovement.id)
            .limit(limit)
            .offset(offset)
        )
    )
    return StockMovementList(
        items=[StockMovementPublic.model_validate(movement) for movement in movements],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/movements",
    response_model=InventoryOperationResult,
    status_code=status.HTTP_201_CREATED,
)
def create_stock_movement(
    payload: StockMovementCreate,
    request: Request,
    session: DatabaseSession,
    auth: CanWriteInventory,
) -> InventoryOperationResult:
    if payload.allow_negative_override and not has_permission(
        auth.user.role, Permission.INVENTORY_OVERRIDE
    ):
        record_audit_event(
            session,
            actor_user_id=auth.user.id,
            action="inventory.movement.create",
            entity_type="product",
            entity_id=str(payload.product_id),
            outcome=AuditOutcome.FAILURE,
            request_id=request.state.request_id,
            details={"reason": "negative_override_permission_required"},
        )
        session.commit()
        raise HTTPException(
            status_code=403, detail="Admin permission is required for negative override"
        )

    try:
        applied = apply_stock_movement(session, payload, actor_user_id=auth.user.id)
    except DomainError as exc:
        actor_id = auth.user.id
        session.rollback()
        record_audit_event(
            session,
            actor_user_id=actor_id,
            action="inventory.movement.create",
            entity_type="product",
            entity_id=str(payload.product_id),
            outcome=AuditOutcome.FAILURE,
            request_id=request.state.request_id,
            details={
                "reason": exc.code,
                "movement_type": payload.movement_type.value,
                "warehouse_id": str(payload.warehouse_id),
                "quantity": str(payload.quantity),
                **exc.details,
            },
        )
        session.commit()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    record_audit_event(
        session,
        actor_user_id=auth.user.id,
        action="inventory.movement.create",
        entity_type="stock_movement",
        entity_id=str(applied.movement.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={
            "movement_type": payload.movement_type.value,
            "product_id": str(payload.product_id),
            "warehouse_id": str(payload.warehouse_id),
            "quantity": str(payload.quantity),
            "negative_override": payload.allow_negative_override,
        },
    )
    session.commit()
    return InventoryOperationResult(
        movement=StockMovementPublic.model_validate(applied.movement),
        source_quantity=applied.source_quantity,
        destination_quantity=applied.destination_quantity,
    )
