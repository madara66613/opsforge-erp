from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import PurchaseOrderStatus, SalesOrderStatus
from app.schemas.inventory import ProductReference, WarehouseReference
from app.schemas.partner import PartnerReference


class SalesOrderLineCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class PurchaseOrderLineCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    unit_cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class SalesOrderCreate(BaseModel):
    partner_id: UUID
    warehouse_id: UUID
    notes: str | None = Field(default=None, max_length=4000)
    lines: list[SalesOrderLineCreate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def product_lines_are_unique(self) -> SalesOrderCreate:
        product_ids = [line.product_id for line in self.lines]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Each product may appear only once per order")
        return self


class PurchaseOrderCreate(BaseModel):
    partner_id: UUID
    warehouse_id: UUID
    notes: str | None = Field(default=None, max_length=4000)
    lines: list[PurchaseOrderLineCreate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def product_lines_are_unique(self) -> PurchaseOrderCreate:
        product_ids = [line.product_id for line in self.lines]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Each product may appear only once per order")
        return self


class SalesOrderLinePublic(BaseModel):
    id: UUID
    product: ProductReference
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class PurchaseOrderLinePublic(BaseModel):
    id: UUID
    product: ProductReference
    quantity: Decimal
    unit_cost: Decimal
    line_total: Decimal


class SalesOrderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_number: str
    partner: PartnerReference
    warehouse: WarehouseReference
    status: SalesOrderStatus
    currency: str
    notes: str | None
    created_by_user_id: UUID
    confirmed_at: datetime | None
    processing_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    total_amount: Decimal
    lines: list[SalesOrderLinePublic]


class PurchaseOrderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_number: str
    partner: PartnerReference
    warehouse: WarehouseReference
    status: PurchaseOrderStatus
    currency: str
    notes: str | None
    created_by_user_id: UUID
    ordered_at: datetime | None
    received_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    total_amount: Decimal
    lines: list[PurchaseOrderLinePublic]


class SalesOrderList(BaseModel):
    items: list[SalesOrderPublic]
    total: int
    limit: int
    offset: int


class PurchaseOrderList(BaseModel):
    items: list[PurchaseOrderPublic]
    total: int
    limit: int
    offset: int
