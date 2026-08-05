from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import AuditOutcome


class AuditLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    outcome: AuditOutcome
    request_id: str | None
    details: dict[str, Any]
    created_at: datetime


class AuditLogList(BaseModel):
    items: list[AuditLogPublic]
    total: int
    limit: int
    offset: int
