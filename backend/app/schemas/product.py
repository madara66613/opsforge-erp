from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    unit: str = Field(default="pcs", min_length=1, max_length=24)
    sale_price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    purchase_price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    is_active: bool = True

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name", "unit")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        return value.strip()


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    unit: str | None = Field(default=None, min_length=1, max_length=24)
    sale_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    purchase_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    is_active: bool | None = None

    @field_validator("sku")
    @classmethod
    def normalize_optional_sku(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("name", "unit")
    @classmethod
    def trim_optional_required_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class ProductPublic(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class ProductList(BaseModel):
    items: list[ProductPublic]
    total: int
    limit: int
    offset: int


ProductSortField = Literal["sku", "name", "sale_price", "purchase_price", "created_at"]
