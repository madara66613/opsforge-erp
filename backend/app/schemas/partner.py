from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.enums import PartnerType


class PartnerBase(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=2, max_length=180)
    partner_type: PartnerType
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=60)
    address: str | None = Field(default=None, max_length=4000)
    tax_id: str | None = Field(default=None, max_length=60)
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        return value.strip()


class PartnerCreate(PartnerBase):
    pass


class PartnerUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=40)
    name: str | None = Field(default=None, min_length=2, max_length=180)
    partner_type: PartnerType | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=60)
    address: str | None = Field(default=None, max_length=4000)
    tax_id: str | None = Field(default=None, max_length=60)
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def normalize_optional_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("name")
    @classmethod
    def trim_optional_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class PartnerPublic(PartnerBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class PartnerList(BaseModel):
    items: list[PartnerPublic]
    total: int
    limit: int
    offset: int


class PartnerReference(BaseModel):
    id: UUID
    code: str
    name: str
    partner_type: PartnerType
