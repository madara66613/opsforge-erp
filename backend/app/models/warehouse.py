from __future__ import annotations

from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UuidPrimaryKeyMixin


class Warehouse(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "warehouses"
    __table_args__ = (Index("ix_warehouses_active_name", "is_active", "name"),)

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    location: Mapped[str | None] = mapped_column(String(240))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
