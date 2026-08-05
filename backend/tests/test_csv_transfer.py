from __future__ import annotations

import csv
import io
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import AuditOutcome, UserRole
from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.inventory import InventoryBalance
from app.models.product import Product
from app.models.user import User
from app.models.warehouse import Warehouse

HEADER = "sku,name,description,unit,purchase_price,sale_price,reorder_threshold,is_active\n"


def add_user(session: Session, email: str, role: UserRole) -> User:
    user = User(
        id=uuid4(),
        email=email,
        full_name=f"{role.value.title()} CSV User",
        role=role,
        password_hash=hash_password("SecureDemo!2026"),
        is_active=True,
    )
    session.add(user)
    session.commit()
    return user


def login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecureDemo!2026"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def post_csv(client: TestClient, headers: dict[str, str], content: str) -> Response:
    return client.post(
        "/api/v1/csv/products/import",
        headers={**headers, "Content-Type": "text/csv"},
        content=content.encode(),
    )


def test_product_csv_import_is_atomic_and_creates_warehouse_balances(
    client: TestClient, db_session: Session
) -> None:
    operator = add_user(db_session, "operator.csv@example.com", UserRole.OPERATOR)
    db_session.add(Warehouse(id=uuid4(), code="CSV-WH", name="CSV warehouse", is_active=True))
    db_session.commit()
    headers = login(client, operator.email)
    content = HEADER + (
        "csv-100,CSV scanner,Imported scanner,pcs,120.50,189.99,4,true\n"
        "CSV-200,CSV labels,,box,15.00,28.00,12,false\n"
    )

    response = post_csv(client, headers, content)

    assert response.status_code == 200
    assert response.json() == {
        "rows_received": 2,
        "products_created": 2,
        "created_skus": ["CSV-100", "CSV-200"],
    }
    products = list(db_session.scalars(select(Product).order_by(Product.sku)))
    assert [product.sku for product in products] == ["CSV-100", "CSV-200"]
    assert str(products[0].reorder_threshold) == "4.000"
    assert db_session.scalar(select(func.count()).select_from(InventoryBalance)) == 2
    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "csv.products.import",
            AuditLog.outcome == AuditOutcome.SUCCESS,
        )
    )
    assert audit is not None
    assert audit.details["products_created"] == 2


def test_invalid_product_csv_rejects_every_row_without_partial_import(
    client: TestClient, db_session: Session
) -> None:
    operator = add_user(db_session, "operator.csv@example.com", UserRole.OPERATOR)
    headers = login(client, operator.email)
    content = HEADER + (
        "CSV-GOOD,Valid row,,pcs,10,20,5,true\nCSV-BAD,Invalid row,,pcs,-1,20,5,perhaps\n"
    )

    response = post_csv(client, headers, content)

    assert response.status_code == 422
    assert response.json()["detail"]["message"].endswith("no products were imported")
    assert db_session.scalar(select(func.count()).select_from(Product)) == 0
    failure = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "csv.products.import",
            AuditLog.outcome == AuditOutcome.FAILURE,
        )
    )
    assert failure is not None
    assert failure.details["error_count"] >= 1


def test_csv_headers_duplicates_and_role_permissions_are_enforced(
    client: TestClient, db_session: Session
) -> None:
    operator = add_user(db_session, "operator.csv@example.com", UserRole.OPERATOR)
    support = add_user(db_session, "support.csv@example.com", UserRole.SUPPORT)
    operator_headers = login(client, operator.email)
    support_headers = login(client, support.email)
    wrong_headers = post_csv(client, operator_headers, "sku,name\nONE,Incomplete\n")
    duplicates = post_csv(
        client,
        operator_headers,
        HEADER + "DUP-1,First,,pcs,1,2,3,true\nDUP-1,Second,,pcs,1,2,3,true\n",
    )
    denied = post_csv(
        client,
        support_headers,
        HEADER + "NOPE-1,Denied,,pcs,1,2,3,true\n",
    )

    assert wrong_headers.status_code == 422
    assert wrong_headers.json()["detail"]["errors"][0]["field"] == "headers"
    assert duplicates.status_code == 422
    assert "Duplicate SKU" in duplicates.json()["detail"]["errors"][0]["message"]
    assert denied.status_code == 403
    assert db_session.scalar(select(func.count()).select_from(Product)) == 0


def test_support_can_export_products_and_inventory_as_parseable_csv(
    client: TestClient, db_session: Session
) -> None:
    support = add_user(db_session, "support.csv@example.com", UserRole.SUPPORT)
    product = Product(
        id=uuid4(),
        sku="EXP-1",
        name="Export product",
        unit="pcs",
        purchase_price=Decimal("10"),
        sale_price=Decimal("20"),
        reorder_threshold=Decimal("3"),
        is_active=True,
    )
    warehouse = Warehouse(id=uuid4(), code="EXP-WH", name="Export warehouse", is_active=True)
    db_session.add_all([product, warehouse])
    db_session.flush()
    db_session.add(
        InventoryBalance(
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=Decimal("2"),
        )
    )
    db_session.commit()
    headers = login(client, support.email)

    products_response = client.get("/api/v1/csv/products/export", headers=headers)
    inventory_response = client.get("/api/v1/csv/inventory/export", headers=headers)

    assert products_response.status_code == 200
    assert products_response.headers["content-disposition"].endswith('"opsforge-products.csv"')
    product_rows = list(csv.DictReader(io.StringIO(products_response.text)))
    assert product_rows[0]["sku"] == "EXP-1"
    assert Decimal(product_rows[0]["reorder_threshold"]) == Decimal("3")
    inventory_rows = list(csv.DictReader(io.StringIO(inventory_response.text)))
    assert inventory_rows[0]["warehouse_code"] == "EXP-WH"
    assert inventory_rows[0]["low_stock"] == "true"
