from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, require_permission
from app.core.enums import AuditOutcome
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogList, AuditLogPublic

router = APIRouter(prefix="/audit-logs", tags=["audit"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CanReadAudit = Annotated[AuthContext, Depends(require_permission(Permission.AUDIT_READ))]


@router.get("", response_model=AuditLogList)
def list_audit_logs(
    session: DatabaseSession,
    _auth: CanReadAudit,
    action: str | None = None,
    outcome: AuditOutcome | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AuditLogList:
    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if outcome:
        filters.append(AuditLog.outcome == outcome)

    total = session.scalar(select(func.count()).select_from(AuditLog).where(*filters)) or 0
    events = list(
        session.scalars(
            select(AuditLog)
            .where(*filters)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return AuditLogList(
        items=[AuditLogPublic.model_validate(event) for event in events],
        total=total,
        limit=limit,
        offset=offset,
    )
