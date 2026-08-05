from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryBalance
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.schemas.csv_transfer import CsvImportError
from app.schemas.product import ProductCreate

PRODUCT_HEADERS = (
    "sku",
    "name",
    "description",
    "unit",
    "purchase_price",
    "sale_price",
    "reorder_threshold",
    "is_active",
)

INVENTORY_HEADERS = (
    "sku",
    "product_name",
    "unit",
    "warehouse_code",
    "warehouse_name",
    "quantity",
    "reorder_threshold",
    "low_stock",
    "updated_at",
)


@dataclass(frozen=True)
class ParsedProductCsv:
    rows_received: int
    products: list[ProductCreate]
    errors: list[CsvImportError]


def parse_product_csv(payload: bytes) -> ParsedProductCsv:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        return ParsedProductCsv(
            rows_received=0,
            products=[],
            errors=[CsvImportError(row=1, field="file", message="File must use UTF-8 encoding")],
        )

    reader = csv.DictReader(io.StringIO(text, newline=""))
    headers = tuple(reader.fieldnames or ())
    if headers != PRODUCT_HEADERS:
        expected = ",".join(PRODUCT_HEADERS)
        actual = ",".join(headers) if headers else "none"
        return ParsedProductCsv(
            rows_received=0,
            products=[],
            errors=[
                CsvImportError(
                    row=1,
                    field="headers",
                    message=f"Expected headers '{expected}' but received '{actual}'",
                )
            ],
        )

    products: list[ProductCreate] = []
    errors: list[CsvImportError] = []
    seen_skus: dict[str, int] = {}
    rows_received = 0
    for row_number, row in enumerate(reader, start=2):
        if not any((value or "").strip() for key, value in row.items() if key is not None):
            continue
        rows_received += 1
        if None in row:
            errors.append(
                CsvImportError(
                    row=row_number,
                    field="row",
                    message="Row contains more values than the header",
                )
            )
            continue
        try:
            product = ProductCreate.model_validate(
                {
                    "sku": row["sku"],
                    "name": row["name"],
                    "description": row["description"] or None,
                    "unit": row["unit"],
                    "purchase_price": row["purchase_price"],
                    "sale_price": row["sale_price"],
                    "reorder_threshold": row["reorder_threshold"],
                    "is_active": _parse_boolean(row["is_active"]),
                }
            )
        except (ValidationError, ValueError) as exc:
            errors.extend(_validation_errors(row_number, exc))
            continue
        first_row = seen_skus.get(product.sku)
        if first_row is not None:
            errors.append(
                CsvImportError(
                    row=row_number,
                    field="sku",
                    message=f"Duplicate SKU in file; first seen on row {first_row}",
                )
            )
            continue
        seen_skus[product.sku] = row_number
        products.append(product)

    if rows_received == 0:
        errors.append(CsvImportError(row=2, field="file", message="CSV contains no data rows"))
    return ParsedProductCsv(rows_received=rows_received, products=products, errors=errors)


def existing_sku_errors(session: Session, parsed: ParsedProductCsv) -> list[CsvImportError]:
    if not parsed.products:
        return []
    skus = [product.sku for product in parsed.products]
    existing = set(session.scalars(select(Product.sku).where(Product.sku.in_(skus))))
    return [
        CsvImportError(
            row=index + 2,
            field="sku",
            message="A product with this SKU already exists",
        )
        for index, product in enumerate(parsed.products)
        if product.sku in existing
    ]


def product_export_csv(products: list[Product]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=PRODUCT_HEADERS, lineterminator="\n")
    writer.writeheader()
    for product in products:
        writer.writerow(
            {
                "sku": product.sku,
                "name": product.name,
                "description": product.description or "",
                "unit": product.unit,
                "purchase_price": _decimal(product.purchase_price),
                "sale_price": _decimal(product.sale_price),
                "reorder_threshold": _decimal(product.reorder_threshold),
                "is_active": str(product.is_active).lower(),
            }
        )
    return output.getvalue()


def inventory_export_csv(
    rows: list[tuple[InventoryBalance, Product, Warehouse]],
) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=INVENTORY_HEADERS, lineterminator="\n")
    writer.writeheader()
    for balance, product, warehouse in rows:
        writer.writerow(
            {
                "sku": product.sku,
                "product_name": product.name,
                "unit": product.unit,
                "warehouse_code": warehouse.code,
                "warehouse_name": warehouse.name,
                "quantity": _decimal(balance.quantity),
                "reorder_threshold": _decimal(product.reorder_threshold),
                "low_stock": str(balance.quantity <= product.reorder_threshold).lower(),
                "updated_at": _timestamp(balance.updated_at),
            }
        )
    return output.getvalue()


def _parse_boolean(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError("is_active must be true, false, 1, 0, yes, or no")


def _validation_errors(row_number: int, exc: ValidationError | ValueError) -> list[CsvImportError]:
    if isinstance(exc, ValidationError):
        return [
            CsvImportError(
                row=row_number,
                field=".".join(str(part) for part in issue["loc"]),
                message=str(issue["msg"]),
            )
            for issue in exc.errors(include_url=False)
        ]
    return [CsvImportError(row=row_number, field="is_active", message=str(exc))]


def _decimal(value: Decimal) -> str:
    return format(value, "f")


def _timestamp(value: datetime) -> str:
    return value.isoformat()
