from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.enums import AuditOutcome
from app.models.audit_log import AuditLog


def record_audit_event(
    session: Session,
    *,
    action: str,
    entity_type: str,
    outcome: AuditOutcome,
    actor_user_id: UUID | None = None,
    entity_id: str | None = None,
    request_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    event = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        outcome=outcome,
        request_id=request_id,
        details=details or {},
    )
    session.add(event)
    return event
