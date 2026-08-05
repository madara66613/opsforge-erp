from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import StockMovementType
from app.models.inventory import InventoryBalance, StockMovement
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.schemas.inventory import StockMovementCreate
from app.services.errors import DomainError, EntityNotFoundError


@dataclass(frozen=True)
class AppliedMovement:
    movement: StockMovement
    source_quantity: Decimal
    destination_quantity: Decimal | None


def create_product_balances(session: Session, product_id: UUID) -> None:
    warehouse_ids = list(session.scalars(select(Warehouse.id)))
    session.add_all(
        [
            InventoryBalance(product_id=product_id, warehouse_id=warehouse_id)
            for warehouse_id in warehouse_ids
        ]
    )


def create_warehouse_balances(session: Session, warehouse_id: UUID) -> None:
    product_ids = list(session.scalars(select(Product.id)))
    session.add_all(
        [
            InventoryBalance(product_id=product_id, warehouse_id=warehouse_id)
            for product_id in product_ids
        ]
    )


def _lock_balances(
    session: Session, product_id: UUID, warehouse_ids: list[UUID]
) -> dict[UUID, InventoryBalance]:
    balances = list(
        session.scalars(
            select(InventoryBalance)
            .where(
                InventoryBalance.product_id == product_id,
                InventoryBalance.warehouse_id.in_(warehouse_ids),
            )
            .order_by(InventoryBalance.warehouse_id)
            .with_for_update()
        )
    )
    balance_by_warehouse = {balance.warehouse_id: balance for balance in balances}
    for warehouse_id in warehouse_ids:
        if warehouse_id not in balance_by_warehouse:
            balance = InventoryBalance(product_id=product_id, warehouse_id=warehouse_id)
            session.add(balance)
            session.flush()
            balance_by_warehouse[warehouse_id] = balance
    return balance_by_warehouse


def _require_active_product(session: Session, product_id: UUID) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise EntityNotFoundError("Product")
    if not product.is_active:
        raise DomainError("Product is inactive", code="inactive_product")
    return product


def _require_active_warehouse(session: Session, warehouse_id: UUID) -> Warehouse:
    warehouse = session.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise EntityNotFoundError("Warehouse")
    if not warehouse.is_active:
        raise DomainError("Warehouse is inactive", code="inactive_warehouse")
    return warehouse


def apply_stock_movement(
    session: Session,
    payload: StockMovementCreate,
    *,
    actor_user_id: UUID,
) -> AppliedMovement:
    _require_active_product(session, payload.product_id)
    _require_active_warehouse(session, payload.warehouse_id)

    warehouse_ids = [payload.warehouse_id]
    if payload.destination_warehouse_id is not None:
        _require_active_warehouse(session, payload.destination_warehouse_id)
        warehouse_ids.append(payload.destination_warehouse_id)

    balances = _lock_balances(session, payload.product_id, warehouse_ids)
    source = balances[payload.warehouse_id]
    destination: InventoryBalance | None = None

    if payload.movement_type in {StockMovementType.RECEIPT, StockMovementType.RETURN}:
        source_delta = payload.quantity
    elif payload.movement_type in {StockMovementType.SALE_ISSUE, StockMovementType.TRANSFER}:
        source_delta = -payload.quantity
    else:
        source_delta = payload.quantity

    resulting_source = source.quantity + source_delta
    if resulting_source < 0 and not payload.allow_negative_override:
        raise DomainError(
            "Operation would create negative inventory",
            code="insufficient_stock",
            details={
                "available": str(source.quantity),
                "requested_delta": str(source_delta),
            },
        )

    source.quantity = resulting_source
    destination_quantity: Decimal | None = None
    if payload.movement_type == StockMovementType.TRANSFER:
        assert payload.destination_warehouse_id is not None
        destination = balances[payload.destination_warehouse_id]
        destination.quantity += payload.quantity
        destination_quantity = destination.quantity

    movement = StockMovement(
        movement_type=payload.movement_type,
        product_id=payload.product_id,
        warehouse_id=payload.warehouse_id,
        destination_warehouse_id=payload.destination_warehouse_id,
        quantity=payload.quantity,
        unit_cost=payload.unit_cost,
        reference=payload.reference.strip() if payload.reference else None,
        notes=payload.notes.strip() if payload.notes else None,
        created_by_user_id=actor_user_id,
        allow_negative_override=payload.allow_negative_override,
    )
    session.add(movement)
    session.flush()
    return AppliedMovement(
        movement=movement,
        source_quantity=source.quantity,
        destination_quantity=destination_quantity,
    )
