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
from app.models.product import Product
from app.schemas.product import (
    ProductCreate,
    ProductList,
    ProductPublic,
    ProductSortField,
    ProductUpdate,
)
from app.services.audit import record_audit_event
from app.services.inventory import create_product_balances

router = APIRouter(prefix="/products", tags=["products"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CanReadProducts = Annotated[AuthContext, Depends(require_permission(Permission.PRODUCTS_READ))]
CanWriteProducts = Annotated[AuthContext, Depends(require_permission(Permission.PRODUCTS_WRITE))]


@router.get("", response_model=ProductList)
def list_products(
    session: DatabaseSession,
    _auth: CanReadProducts,
    search: str | None = None,
    active: bool | None = None,
    sort_by: ProductSortField = "name",
    sort_order: Literal["asc", "desc"] = "asc",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProductList:
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(Product.sku.ilike(pattern), Product.name.ilike(pattern)))
    if active is not None:
        filters.append(Product.is_active == active)

    total = session.scalar(select(func.count()).select_from(Product).where(*filters)) or 0
    sort_columns = {
        "sku": Product.sku,
        "name": Product.name,
        "sale_price": Product.sale_price,
        "purchase_price": Product.purchase_price,
        "created_at": Product.created_at,
    }
    direction = asc if sort_order == "asc" else desc
    products = list(
        session.scalars(
            select(Product)
            .where(*filters)
            .order_by(direction(sort_columns[sort_by]), Product.id)
            .limit(limit)
            .offset(offset)
        )
    )
    return ProductList(
        items=[ProductPublic.model_validate(product) for product in products],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ProductPublic, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    request: Request,
    session: DatabaseSession,
    auth: CanWriteProducts,
) -> ProductPublic:
    actor_id = auth.user.id
    product = Product(**payload.model_dump())
    session.add(product)
    try:
        session.flush()
        create_product_balances(session, product.id)
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        record_audit_event(
            session,
            actor_user_id=actor_id,
            action="product.create",
            entity_type="product",
            outcome=AuditOutcome.FAILURE,
            request_id=request.state.request_id,
            details={"reason": "sku_already_exists", "sku": payload.sku},
        )
        session.commit()
        raise HTTPException(
            status_code=409, detail="A product with this SKU already exists"
        ) from exc

    record_audit_event(
        session,
        actor_user_id=actor_id,
        action="product.create",
        entity_type="product",
        entity_id=str(product.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={"sku": product.sku},
    )
    session.commit()
    return ProductPublic.model_validate(product)


@router.get("/{product_id}", response_model=ProductPublic)
def get_product(
    product_id: UUID,
    session: DatabaseSession,
    _auth: CanReadProducts,
) -> ProductPublic:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductPublic.model_validate(product)


@router.patch("/{product_id}", response_model=ProductPublic)
def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    request: Request,
    session: DatabaseSession,
    auth: CanWriteProducts,
) -> ProductPublic:
    actor_id = auth.user.id
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        if field_name == "description" or value is not None:
            setattr(product, field_name, value)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        record_audit_event(
            session,
            actor_user_id=actor_id,
            action="product.update",
            entity_type="product",
            entity_id=str(product_id),
            outcome=AuditOutcome.FAILURE,
            request_id=request.state.request_id,
            details={"reason": "sku_already_exists"},
        )
        session.commit()
        raise HTTPException(
            status_code=409, detail="A product with this SKU already exists"
        ) from exc

    record_audit_event(
        session,
        actor_user_id=actor_id,
        action="product.update",
        entity_type="product",
        entity_id=str(product.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={"changed_fields": sorted(updates)},
    )
    session.commit()
    return ProductPublic.model_validate(product)
