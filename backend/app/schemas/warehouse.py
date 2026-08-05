from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WarehouseBase(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=2, max_length=120)
    location: str | None = Field(default=None, max_length=240)
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        return value.strip()


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    location: str | None = Field(default=None, max_length=240)
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def normalize_optional_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("name")
    @classmethod
    def trim_optional_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class WarehousePublic(WarehouseBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class WarehouseList(BaseModel):
    items: list[WarehousePublic]
    total: int
    limit: int
    offset: int
