from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import AuditOutcome, SalesOrderStatus, UserRole
from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.idempotency import IdempotencyRecord
from app.models.inventory import InventoryBalance, StockMovement
from app.models.orders import PurchaseOrder, SalesOrder
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


def headers(token: str, idempotency_key: str | None = None) -> dict[str, str]:
    result = {"Authorization": f"Bearer {token}"}
    if idempotency_key:
        result["Idempotency-Key"] = idempotency_key
    return result


def setup_catalog(client: TestClient, token: str) -> tuple[dict[str, object], dict[str, object]]:
    product_response = client.post(
        "/api/v1/products",
        headers=headers(token),
        json={
            "sku": "ORDER-SKU",
            "name": "Order test product",
            "sale_price": "25.00",
            "purchase_price": "10.00",
        },
    )
    warehouse_response = client.post(
        "/api/v1/warehouses",
        headers=headers(token),
        json={"code": "MAIN", "name": "Main warehouse"},
    )
    assert product_response.status_code == 201
    assert warehouse_response.status_code == 201
    return dict(product_response.json()), dict(warehouse_response.json())


def create_partner(client: TestClient, token: str, partner_type: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/partners",
        headers=headers(token),
        json={
            "code": f"PARTNER-{partner_type}",
            "name": f"{partner_type.title()} Partner",
            "partner_type": partner_type,
            "email": f"{partner_type}@example.com",
        },
    )
    assert response.status_code == 201
    return dict(response.json())


def stock_receipt(
    client: TestClient,
    token: str,
    product: dict[str, object],
    warehouse: dict[str, object],
    quantity: str,
) -> None:
    response = client.post(
        "/api/v1/inventory/movements",
        headers=headers(token),
        json={
            "movement_type": "receipt",
            "product_id": product["id"],
            "warehouse_id": warehouse["id"],
            "quantity": quantity,
            "reference": "TEST-OPENING",
        },
    )
    assert response.status_code == 201


def test_sales_completion_is_atomic_and_idempotent(client: TestClient, db_session: Session) -> None:
    operator = add_user(db_session, "operator@example.com", UserRole.OPERATOR)
    token = token_for(client, operator)
    product, warehouse = setup_catalog(client, token)
    customer = create_partner(client, token, "customer")
    stock_receipt(client, token, product, warehouse, "10")

    created = client.post(
        "/api/v1/sales-orders",
        headers=headers(token),
        json={
            "partner_id": customer["id"],
            "warehouse_id": warehouse["id"],
            "lines": [{"product_id": product["id"], "quantity": "3"}],
        },
    )
    assert created.status_code == 201
    order_id = created.json()["id"]
    assert created.json()["total_amount"] == "75.00"
    assert (
        client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=headers(token)).status_code
        == 200
    )

    first = client.post(
        f"/api/v1/sales-orders/{order_id}/complete",
        headers=headers(token, "sales-complete-0001"),
    )
    replay = client.post(
        f"/api/v1/sales-orders/{order_id}/complete",
        headers=headers(token, "sales-complete-0001"),
    )
    different_key = client.post(
        f"/api/v1/sales-orders/{order_id}/complete",
        headers=headers(token, "sales-complete-0002"),
    )

    assert first.status_code == 200
    assert first.json()["status"] == "completed"
    assert first.headers["X-Idempotent-Replay"] == "false"
    assert replay.status_code == 200
    assert replay.headers["X-Idempotent-Replay"] == "true"
    assert different_key.status_code == 409
    balance = db_session.scalar(select(InventoryBalance.quantity))
    assert balance == Decimal("7.000")
    assert db_session.scalar(select(func.count()).select_from(StockMovement)) == 2
    assert db_session.scalar(select(func.count()).select_from(IdempotencyRecord)) == 1


def test_failed_sales_completion_rolls_back_order_stock_and_movements(
    client: TestClient, db_session: Session
) -> None:
    operator = add_user(db_session, "operator@example.com", UserRole.OPERATOR)
    token = token_for(client, operator)
    product, warehouse = setup_catalog(client, token)
    customer = create_partner(client, token, "customer")
    created = client.post(
        "/api/v1/sales-orders",
        headers=headers(token),
        json={
            "partner_id": customer["id"],
            "warehouse_id": warehouse["id"],
            "lines": [{"product_id": product["id"], "quantity": "2"}],
        },
    ).json()
    client.post(f"/api/v1/sales-orders/{created['id']}/confirm", headers=headers(token))

    failed = client.post(
        f"/api/v1/sales-orders/{created['id']}/complete",
        headers=headers(token, "insufficient-0001"),
    )

    assert failed.status_code == 409
    order = db_session.get(SalesOrder, UUID(created["id"]))
    assert order is not None and order.status == SalesOrderStatus.CONFIRMED
    assert db_session.scalar(select(func.count()).select_from(StockMovement)) == 0
    assert db_session.scalar(select(func.count()).select_from(IdempotencyRecord)) == 0
    failure = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "sales_order.complete",
            AuditLog.outcome == AuditOutcome.FAILURE,
        )
    )
    assert failure is not None and failure.details["reason"] == "insufficient_stock"


def test_purchase_receipt_is_atomic_and_idempotent(client: TestClient, db_session: Session) -> None:
    operator = add_user(db_session, "operator@example.com", UserRole.OPERATOR)
    token = token_for(client, operator)
    product, warehouse = setup_catalog(client, token)
    supplier = create_partner(client, token, "supplier")
    created = client.post(
        "/api/v1/purchase-orders",
        headers=headers(token),
        json={
            "partner_id": supplier["id"],
            "warehouse_id": warehouse["id"],
            "expected_delivery_date": "2026-08-20",
            "lines": [{"product_id": product["id"], "quantity": "5"}],
        },
    )
    assert created.status_code == 201
    assert created.json()["expected_delivery_date"] == "2026-08-20"
    order_id = created.json()["id"]
    assert (
        client.post(f"/api/v1/purchase-orders/{order_id}/order", headers=headers(token)).json()[
            "status"
        ]
        == "ordered"
    )

    first = client.post(
        f"/api/v1/purchase-orders/{order_id}/receive",
        headers=headers(token, "purchase-receive-0001"),
    )
    replay = client.post(
        f"/api/v1/purchase-orders/{order_id}/receive",
        headers=headers(token, "purchase-receive-0001"),
    )

    assert first.status_code == 200
    assert first.json()["status"] == "received"
    assert replay.status_code == 200
    assert replay.headers["X-Idempotent-Replay"] == "true"
    assert db_session.scalar(select(InventoryBalance.quantity)) == Decimal("5.000")
    assert db_session.scalar(select(func.count()).select_from(StockMovement)) == 1
    assert db_session.scalar(select(func.count()).select_from(PurchaseOrder)) == 1


def test_partner_type_rules_and_support_read_only_access(
    client: TestClient, db_session: Session
) -> None:
    operator = add_user(db_session, "operator@example.com", UserRole.OPERATOR)
    support = add_user(db_session, "support@example.com", UserRole.SUPPORT)
    operator_token = token_for(client, operator)
    support_token = token_for(client, support)
    product, warehouse = setup_catalog(client, operator_token)
    supplier = create_partner(client, operator_token, "supplier")

    invalid_sales = client.post(
        "/api/v1/sales-orders",
        headers=headers(operator_token),
        json={
            "partner_id": supplier["id"],
            "warehouse_id": warehouse["id"],
            "lines": [{"product_id": product["id"], "quantity": "1"}],
        },
    )

    assert invalid_sales.status_code == 409
    assert client.get("/api/v1/partners", headers=headers(support_token)).status_code == 200
    assert (
        client.post(
            "/api/v1/partners",
            headers=headers(support_token),
            json={"code": "DENIED", "name": "Denied", "partner_type": "both"},
        ).status_code
        == 403
    )


def test_dashboard_summarizes_operational_state(client: TestClient, db_session: Session) -> None:
    operator = add_user(db_session, "operator@example.com", UserRole.OPERATOR)
    token = token_for(client, operator)
    product, warehouse = setup_catalog(client, token)
    customer = create_partner(client, token, "customer")
    stock_receipt(client, token, product, warehouse, "4")
    client.post(
        "/api/v1/sales-orders",
        headers=headers(token),
        json={
            "partner_id": customer["id"],
            "warehouse_id": warehouse["id"],
            "lines": [{"product_id": product["id"], "quantity": "2"}],
        },
    )

    response = client.get("/api/v1/dashboard/summary", headers=headers(token))

    assert response.status_code == 200
    data = response.json()
    assert data["counts"] == {
        "active_products": 1,
        "active_warehouses": 1,
        "active_partners": 1,
        "pending_sales_orders": 1,
        "pending_purchase_orders": 0,
        "low_stock_balances": 1,
    }
    assert Decimal(data["inventory_value"]) == Decimal("40")
    assert Decimal(data["pending_sales_value"]) == Decimal("50")
    assert len(data["recent_sales_orders"]) == 1
    assert len(data["recent_movements"]) == 1
    assert data["recent_audit_events"] == []

    admin = add_user(db_session, "admin.dashboard@example.com", UserRole.ADMIN)
    admin_token = token_for(client, admin)
    admin_dashboard = client.get("/api/v1/dashboard/summary", headers=headers(admin_token)).json()
    assert admin_dashboard["recent_audit_events"]
    assert admin_dashboard["recent_audit_events"][0]["action"] == "auth.login"
    assert admin_dashboard["recent_audit_events"][0]["outcome"] == "success"
