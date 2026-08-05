from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, require_permission
from app.core.enums import AuditOutcome
from app.core.permissions import Permission
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserList, UserPublic, UserUpdate
from app.services.audit import record_audit_event
from app.services.auth import normalize_email

router = APIRouter(prefix="/users", tags=["users"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CanReadUsers = Annotated[AuthContext, Depends(require_permission(Permission.USERS_READ))]
CanManageUsers = Annotated[AuthContext, Depends(require_permission(Permission.USERS_MANAGE))]


@router.get("", response_model=UserList)
def list_users(
    session: DatabaseSession,
    _auth: CanReadUsers,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> UserList:
    total = session.scalar(select(func.count()).select_from(User)) or 0
    users = list(session.scalars(select(User).order_by(User.email).limit(limit).offset(offset)))
    return UserList(
        items=[UserPublic.model_validate(user) for user in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    session: DatabaseSession,
    auth: CanManageUsers,
) -> UserPublic:
    actor_id = auth.user.id
    user = User(
        email=normalize_email(str(payload.email)),
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    session.add(user)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        record_audit_event(
            session,
            actor_user_id=actor_id,
            action="user.create",
            entity_type="user",
            outcome=AuditOutcome.FAILURE,
            request_id=request.state.request_id,
            details={"reason": "email_already_exists"},
        )
        session.commit()
        raise HTTPException(
            status_code=409, detail="A user with this email already exists"
        ) from exc

    record_audit_event(
        session,
        actor_user_id=actor_id,
        action="user.create",
        entity_type="user",
        entity_id=str(user.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={"role": user.role.value},
    )
    session.commit()
    return UserPublic.model_validate(user)


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    request: Request,
    session: DatabaseSession,
    auth: CanManageUsers,
) -> UserPublic:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == auth.user.id and payload.is_active is False:
        record_audit_event(
            session,
            actor_user_id=auth.user.id,
            action="user.update",
            entity_type="user",
            entity_id=str(user.id),
            outcome=AuditOutcome.FAILURE,
            request_id=request.state.request_id,
            details={"reason": "self_deactivation_not_allowed"},
        )
        session.commit()
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    changed_fields: list[str] = []
    for field_name in ("full_name", "role", "is_active"):
        value = getattr(payload, field_name)
        if value is not None:
            setattr(user, field_name, value.strip() if isinstance(value, str) else value)
            changed_fields.append(field_name)
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
        changed_fields.append("password")

    record_audit_event(
        session,
        actor_user_id=auth.user.id,
        action="user.update",
        entity_type="user",
        entity_id=str(user.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={"changed_fields": changed_fields},
    )
    session.commit()
    return UserPublic.model_validate(user)
