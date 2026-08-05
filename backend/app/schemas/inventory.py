from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import StockMovementType


class ProductReference(BaseModel):
    id: UUID
    sku: str
    name: str
    unit: str
    reorder_threshold: Decimal


class WarehouseReference(BaseModel):
    id: UUID
    code: str
    name: str


class InventoryBalancePublic(BaseModel):
    id: UUID
    product: ProductReference
    warehouse: WarehouseReference
    quantity: Decimal
    updated_at: datetime


class InventoryBalanceList(BaseModel):
    items: list[InventoryBalancePublic]
    total: int
    limit: int
    offset: int


class StockMovementCreate(BaseModel):
    movement_type: StockMovementType
    product_id: UUID
    warehouse_id: UUID
    destination_warehouse_id: UUID | None = None
    quantity: Decimal = Field(max_digits=14, decimal_places=3)
    unit_cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=4000)
    allow_negative_override: bool = False

    @model_validator(mode="after")
    def validate_movement_shape(self) -> StockMovementCreate:
        if self.movement_type == StockMovementType.ADJUSTMENT:
            if self.quantity == 0:
                raise ValueError("Adjustment quantity must be non-zero")
        elif self.quantity <= 0:
            raise ValueError("Movement quantity must be positive")

        if self.movement_type == StockMovementType.TRANSFER:
            if self.destination_warehouse_id is None:
                raise ValueError("Transfer requires a destination warehouse")
            if self.destination_warehouse_id == self.warehouse_id:
                raise ValueError("Transfer destination must differ from the source warehouse")
        elif self.destination_warehouse_id is not None:
            raise ValueError("Destination warehouse is only valid for transfers")
        return self


class StockMovementPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    movement_type: StockMovementType
    product_id: UUID
    warehouse_id: UUID
    destination_warehouse_id: UUID | None
    quantity: Decimal
    unit_cost: Decimal | None
    reference: str | None
    notes: str | None
    created_by_user_id: UUID
    allow_negative_override: bool
    created_at: datetime


class StockMovementList(BaseModel):
    items: list[StockMovementPublic]
    total: int
    limit: int
    offset: int


class InventoryOperationResult(BaseModel):
    movement: StockMovementPublic
    source_quantity: Decimal
    destination_quantity: Decimal | None = None
