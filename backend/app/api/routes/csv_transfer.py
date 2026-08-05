from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, require_permission
from app.core.enums import AuditOutcome
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.inventory import InventoryBalance
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.schemas.csv_transfer import CsvImportFailure, ProductImportSummary
from app.services.audit import record_audit_event
from app.services.csv_transfer import (
    existing_sku_errors,
    inventory_export_csv,
    parse_product_csv,
    product_export_csv,
)
from app.services.inventory import create_product_balances

router = APIRouter(prefix="/csv", tags=["CSV transfer"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CanImportCsv = Annotated[AuthContext, Depends(require_permission(Permission.CSV_IMPORT))]
CanExportCsv = Annotated[AuthContext, Depends(require_permission(Permission.CSV_EXPORT))]
CsvBody = Annotated[bytes, Body(media_type="text/csv", max_length=2_000_000)]


@router.post(
    "/products/import",
    response_model=ProductImportSummary,
    responses={422: {"model": CsvImportFailure}},
)
def import_products(
    payload: CsvBody,
    request: Request,
    session: DatabaseSession,
    auth: CanImportCsv,
) -> ProductImportSummary:
    parsed = parse_product_csv(payload)
    errors = [*parsed.errors, *existing_sku_errors(session, parsed)]
    if errors:
        record_audit_event(
            session,
            actor_user_id=auth.user.id,
            action="csv.products.import",
            entity_type="product",
            outcome=AuditOutcome.FAILURE,
            request_id=request.state.request_id,
            details={"rows_received": parsed.rows_received, "error_count": len(errors)},
        )
        session.commit()
        raise HTTPException(
            status_code=422,
            detail={
                "message": "CSV validation failed; no products were imported",
                "errors": [error.model_dump() for error in errors],
            },
        )

    created: list[Product] = []
    try:
        for product_data in parsed.products:
            product = Product(**product_data.model_dump(mode="python"))
            session.add(product)
            session.flush()
            create_product_balances(session, product.id)
            created.append(product)
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        record_audit_event(
            session,
            actor_user_id=auth.user.id,
            action="csv.products.import",
            entity_type="product",
            outcome=AuditOutcome.FAILURE,
            request_id=request.state.request_id,
            details={"rows_received": parsed.rows_received, "reason": "database_conflict"},
        )
        session.commit()
        raise HTTPException(
            status_code=409,
            detail=(
                "CSV import conflicted with data created by another request; "
                "no products were imported"
            ),
        ) from exc

    created_skus = [product.sku for product in created]
    record_audit_event(
        session,
        actor_user_id=auth.user.id,
        action="csv.products.import",
        entity_type="product",
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={"products_created": len(created), "skus": created_skus},
    )
    session.commit()
    return ProductImportSummary(
        rows_received=parsed.rows_received,
        products_created=len(created),
        created_skus=created_skus,
    )


@router.get("/products/export")
def export_products(
    request: Request,
    session: DatabaseSession,
    auth: CanExportCsv,
) -> Response:
    products = list(session.scalars(select(Product).order_by(Product.sku)))
    content = product_export_csv(products)
    _audit_export(session, request, auth, "csv.products.export", len(products))
    return _csv_response(content, "opsforge-products.csv")


@router.get("/inventory/export")
def export_inventory(
    request: Request,
    session: DatabaseSession,
    auth: CanExportCsv,
) -> Response:
    rows = list(
        session.execute(
            select(InventoryBalance, Product, Warehouse)
            .join(Product, Product.id == InventoryBalance.product_id)
            .join(Warehouse, Warehouse.id == InventoryBalance.warehouse_id)
            .order_by(Product.sku, Warehouse.code)
        ).tuples()
    )
    content = inventory_export_csv(rows)
    _audit_export(session, request, auth, "csv.inventory.export", len(rows))
    return _csv_response(content, "opsforge-inventory.csv")


def _audit_export(
    session: Session,
    request: Request,
    auth: AuthContext,
    action: str,
    row_count: int,
) -> None:
    record_audit_event(
        session,
        actor_user_id=auth.user.id,
        action=action,
        entity_type="csv_export",
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={"row_count": row_count},
    )
    session.commit()


def _csv_response(content: str, filename: str) -> Response:
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
