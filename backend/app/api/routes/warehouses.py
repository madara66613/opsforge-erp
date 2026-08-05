from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, require_permission
from app.core.enums import AuditOutcome
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.warehouse import Warehouse
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseList,
    WarehousePublic,
    WarehouseUpdate,
)
from app.services.audit import record_audit_event
from app.services.inventory import create_warehouse_balances

router = APIRouter(prefix="/warehouses", tags=["warehouses"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CanReadInventory = Annotated[AuthContext, Depends(require_permission(Permission.INVENTORY_READ))]
CanWriteInventory = Annotated[AuthContext, Depends(require_permission(Permission.INVENTORY_WRITE))]


@router.get("", response_model=WarehouseList)
def list_warehouses(
    session: DatabaseSession,
    _auth: CanReadInventory,
    search: str | None = None,
    active: bool | None = None,
    sort_by: Literal["code", "name", "created_at"] = "name",
    sort_order: Literal["asc", "desc"] = "asc",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WarehouseList:
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(Warehouse.code.ilike(pattern), Warehouse.name.ilike(pattern)))
    if active is not None:
        filters.append(Warehouse.is_active == active)

    total = session.scalar(select(func.count()).select_from(Warehouse).where(*filters)) or 0
    sort_columns = {
        "code": Warehouse.code,
        "name": Warehouse.name,
        "created_at": Warehouse.created_at,
    }
    direction = asc if sort_order == "asc" else desc
    warehouses = list(
        session.scalars(
            select(Warehouse)
            .where(*filters)
            .order_by(direction(sort_columns[sort_by]), Warehouse.id)
            .limit(limit)
            .offset(offset)
        )
    )
    return WarehouseList(
        items=[WarehousePublic.model_validate(warehouse) for warehouse in warehouses],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=WarehousePublic, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    payload: WarehouseCreate,
    request: Request,
    session: DatabaseSession,
    auth: CanWriteInventory,
) -> WarehousePublic:
    actor_id = auth.user.id
    warehouse = Warehouse(**payload.model_dump())
    session.add(warehouse)
    try:
        session.flush()
        create_warehouse_balances(session, warehouse.id)
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        record_audit_event(
            session,
            actor_user_id=actor_id,
            action="warehouse.create",
            entity_type="warehouse",
            outcome=AuditOutcome.FAILURE,
            request_id=request.state.request_id,
            details={"reason": "code_already_exists", "code": payload.code},
        )
        session.commit()
        raise HTTPException(
            status_code=409, detail="A warehouse with this code already exists"
        ) from exc

    record_audit_event(
        session,
        actor_user_id=actor_id,
        action="warehouse.create",
        entity_type="warehouse",
        entity_id=str(warehouse.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={"code": warehouse.code},
    )
    session.commit()
    return WarehousePublic.model_validate(warehouse)


@router.get("/{warehouse_id}", response_model=WarehousePublic)
def get_warehouse(
    warehouse_id: UUID,
    session: DatabaseSession,
    _auth: CanReadInventory,
) -> WarehousePublic:
    warehouse = session.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return WarehousePublic.model_validate(warehouse)


@router.patch("/{warehouse_id}", response_model=WarehousePublic)
def update_warehouse(
    warehouse_id: UUID,
    payload: WarehouseUpdate,
    request: Request,
    session: DatabaseSession,
    auth: CanWriteInventory,
) -> WarehousePublic:
    actor_id = auth.user.id
    warehouse = session.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        if field_name == "location" or value is not None:
            setattr(warehouse, field_name, value)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        record_audit_event(
            session,
            actor_user_id=actor_id,
            action="warehouse.update",
            entity_type="warehouse",
            entity_id=str(warehouse_id),
            outcome=AuditOutcome.FAILURE,
            request_id=request.state.request_id,
            details={"reason": "code_already_exists"},
        )
        session.commit()
        raise HTTPException(
            status_code=409, detail="A warehouse with this code already exists"
        ) from exc

    record_audit_event(
        session,
        actor_user_id=actor_id,
        action="warehouse.update",
        entity_type="warehouse",
        entity_id=str(warehouse.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={"changed_fields": sorted(updates)},
    )
    session.commit()
    return WarehousePublic.model_validate(warehouse)
