from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import AuditOutcome
from app.db.base import Base
from app.models.base import UuidPrimaryKeyMixin, utc_now


class AuditLog(UuidPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('success', 'failure')",
            name="ck_audit_logs_outcome",
        ),
        Index("ix_audit_logs_created_action", "created_at", "action"),
        Index("ix_audit_logs_actor_created", "actor_user_id", "created_at"),
    )

    actor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64))
    outcome: Mapped[AuditOutcome] = mapped_column(
        Enum(
            AuditOutcome,
            name="audit_outcome",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
            create_constraint=False,
        ),
        nullable=False,
    )
    request_id: Mapped[str | None] = mapped_column(String(64), index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True, nullable=False
    )
