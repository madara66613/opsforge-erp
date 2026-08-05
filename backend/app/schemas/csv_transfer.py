from __future__ import annotations

from pydantic import BaseModel


class CsvImportError(BaseModel):
    row: int
    field: str
    message: str


class ProductImportSummary(BaseModel):
    rows_received: int
    products_created: int
    created_skus: list[str]


class CsvImportFailure(BaseModel):
    message: str
    errors: list[CsvImportError]
