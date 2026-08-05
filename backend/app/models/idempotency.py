from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import UuidPrimaryKeyMixin, utc_now


class IdempotencyRecord(UuidPrimaryKeyMixin, Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("operation", "idempotency_key", name="uq_idempotency_operation_key"),
        Index("ix_idempotency_resource", "operation", "resource_id"),
    )

    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True, nullable=False
    )
