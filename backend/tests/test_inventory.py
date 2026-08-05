from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import AuditOutcome, UserRole
from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.inventory import InventoryBalance, StockMovement
from app.models.user import User


def add_user(session: Session, email: str, role: UserRole) -> User:
    user = User(
        id=uuid4(),
        email=email,
        full_name=f"{role.value.title()} User",
        role=role,
        password_hash=hash_password("SecureDemo!2026"),
        is_active=True,
    )
    session.add(user)
    session.commit()
    return user


def token_for(client: TestClient, user: User) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "SecureDemo!2026"},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_product(client: TestClient, token: str, sku: str = "SKU-001") -> dict[str, object]:
    response = client.post(
        "/api/v1/products",
        headers=headers(token),
        json={
            "sku": sku,
            "name": f"Product {sku}",
            "unit": "pcs",
            "sale_price": "25.50",
            "purchase_price": "15.25",
        },
    )
    assert response.status_code == 201
    return dict(response.json())


def create_warehouse(client: TestClient, token: str, code: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/warehouses",
        headers=headers(token),
        json={"code": code, "name": f"Warehouse {code}"},
    )
    assert response.status_code == 201
    return dict(response.json())


def movement(
    client: TestClient,
    token: str,
    *,
    movement_type: str,
    product_id: object,
    warehouse_id: object,
    quantity: str,
    destination_warehouse_id: object | None = None,
    allow_negative_override: bool = False,
) -> object:
    payload = {
        "movement_type": movement_type,
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "quantity": quantity,
        "reference": f"TEST-{movement_type}",
        "allow_negative_override": allow_negative_override,
    }
    if destination_warehouse_id is not None:
        payload["destination_warehouse_id"] = destination_warehouse_id
    return client.post("/api/v1/inventory/movements", headers=headers(token), json=payload)


def test_product_crud_normalizes_and_rejects_duplicate_sku(
    client: TestClient, db_session: Session
) -> None:
    operator = add_user(db_session, "operator@example.com", UserRole.OPERATOR)
    support = add_user(db_session, "support@example.com", UserRole.SUPPORT)
    operator_token = token_for(client, operator)
    support_token = token_for(client, support)
    create_warehouse(client, operator_token, "MAIN")

    created = create_product(client, operator_token, "sku-001")
    duplicate = client.post(
        "/api/v1/products",
        headers=headers(operator_token),
        json={"sku": "SKU-001", "name": "Duplicate", "sale_price": 1, "purchase_price": 1},
    )

    assert created["sku"] == "SKU-001"
    assert duplicate.status_code == 409
    assert (
        client.get("/api/v1/products?search=sku-001", headers=headers(support_token)).json()[
            "total"
        ]
        == 1
    )
    assert (
        client.post(
            "/api/v1/products",
            headers=headers(support_token),
            json={"sku": "NOPE", "name": "Denied"},
        ).status_code
        == 403
    )
    assert db_session.scalar(select(func.count()).select_from(InventoryBalance)) == 1


def test_receipt_transfer_and_issue_update_balances_atomically(
    client: TestClient, db_session: Session
) -> None:
    operator = add_user(db_session, "operator@example.com", UserRole.OPERATOR)
    token = token_for(client, operator)
    product = create_product(client, token)
    source = create_warehouse(client, token, "SOURCE")
    destination = create_warehouse(client, token, "DEST")

    received = movement(
        client,
        token,
        movement_type="receipt",
        product_id=product["id"],
        warehouse_id=source["id"],
        quantity="10",
    )
    transferred = movement(
        client,
        token,
        movement_type="transfer",
        product_id=product["id"],
        warehouse_id=source["id"],
        destination_warehouse_id=destination["id"],
        quantity="4",
    )
    issued = movement(
        client,
        token,
        movement_type="sale_issue",
        product_id=product["id"],
        warehouse_id=destination["id"],
        quantity="1.5",
    )

    assert received.status_code == 201
    assert transferred.status_code == 201
    assert transferred.json()["source_quantity"] == "6.000"
    assert transferred.json()["destination_quantity"] == "4.000"
    assert issued.status_code == 201
    balances = client.get(
        f"/api/v1/inventory?product_id={product['id']}&sort_by=warehouse",
        headers=headers(token),
    ).json()["items"]
    assert sorted(Decimal(item["quantity"]) for item in balances) == [Decimal("2.5"), Decimal("6")]
    assert all(item["product"]["reorder_threshold"] == "5.000" for item in balances)
    assert db_session.scalar(select(func.count()).select_from(StockMovement)) == 3


def test_negative_inventory_is_rejected_without_partial_write_and_audited(
    client: TestClient, db_session: Session
) -> None:
    operator = add_user(db_session, "operator@example.com", UserRole.OPERATOR)
    token = token_for(client, operator)
    product = create_product(client, token)
    warehouse = create_warehouse(client, token, "MAIN")
    movement(
        client,
        token,
        movement_type="receipt",
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity="2",
    )

    rejected = movement(
        client,
        token,
        movement_type="sale_issue",
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity="5",
    )

    assert rejected.status_code == 409
    balance = db_session.scalar(select(InventoryBalance))
    assert balance is not None and balance.quantity == Decimal("2.000")
    assert db_session.scalar(select(func.count()).select_from(StockMovement)) == 1
    failure = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "inventory.movement.create",
            AuditLog.outcome == AuditOutcome.FAILURE,
        )
    )
    assert failure is not None
    assert failure.details["reason"] == "insufficient_stock"


def test_only_admin_can_explicitly_override_negative_inventory(
    client: TestClient, db_session: Session
) -> None:
    admin = add_user(db_session, "admin@example.com", UserRole.ADMIN)
    operator = add_user(db_session, "operator@example.com", UserRole.OPERATOR)
    admin_token = token_for(client, admin)
    operator_token = token_for(client, operator)
    product = create_product(client, operator_token)
    warehouse = create_warehouse(client, operator_token, "MAIN")

    denied = movement(
        client,
        operator_token,
        movement_type="adjustment",
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity="-3",
        allow_negative_override=True,
    )
    overridden = movement(
        client,
        admin_token,
        movement_type="adjustment",
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity="-3",
        allow_negative_override=True,
    )

    assert denied.status_code == 403
    assert overridden.status_code == 201
    assert overridden.json()["source_quantity"] == "-3.000"
    success = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "inventory.movement.create",
            AuditLog.outcome == AuditOutcome.SUCCESS,
            AuditLog.details["negative_override"].as_boolean().is_(True),
        )
    )
    assert success is not None


def test_failed_transfer_rolls_back_both_warehouse_balances(
    client: TestClient, db_session: Session
) -> None:
    operator = add_user(db_session, "operator@example.com", UserRole.OPERATOR)
    token = token_for(client, operator)
    product = create_product(client, token)
    source = create_warehouse(client, token, "SOURCE")
    destination = create_warehouse(client, token, "DEST")
    movement(
        client,
        token,
        movement_type="receipt",
        product_id=product["id"],
        warehouse_id=source["id"],
        quantity="3",
    )

    rejected = movement(
        client,
        token,
        movement_type="transfer",
        product_id=product["id"],
        warehouse_id=source["id"],
        destination_warehouse_id=destination["id"],
        quantity="5",
    )

    assert rejected.status_code == 409
    quantities = sorted(db_session.scalars(select(InventoryBalance.quantity)).all())
    assert quantities == [Decimal("0.000"), Decimal("3.000")]
    assert db_session.scalar(select(func.count()).select_from(StockMovement)) == 1
