from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, Enum, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import PartnerType
from app.db.base import Base
from app.models.base import TimestampMixin, UuidPrimaryKeyMixin


class Partner(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "partners"
    __table_args__ = (
        CheckConstraint(
            "partner_type IN ('customer', 'supplier', 'both')",
            name="ck_partners_type",
        ),
        Index("ix_partners_active_name", "is_active", "name"),
    )

    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    partner_type: Mapped[PartnerType] = mapped_column(
        Enum(
            PartnerType,
            name="partner_type",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
            create_constraint=False,
        ),
        index=True,
        nullable=False,
    )
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(60))
    address: Mapped[str | None] = mapped_column(Text)
    tax_id: Mapped[str | None] = mapped_column(String(60), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
