from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentAuth
from app.core.config import Settings, get_settings
from app.core.enums import AuditOutcome
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LogoutResponse, TokenResponse
from app.schemas.user import UserPublic
from app.services.audit import record_audit_event
from app.services.auth import authenticate_user, issue_session

router = APIRouter(prefix="/auth", tags=["authentication"])
DatabaseSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    session: DatabaseSession,
    settings: AppSettings,
) -> TokenResponse:
    user = authenticate_user(session, str(payload.email), payload.password)
    if user is None:
        record_audit_event(
            session,
            action="auth.login",
            entity_type="session",
            outcome=AuditOutcome.FAILURE,
            request_id=request.state.request_id,
            details={"reason": "invalid_credentials_or_inactive_user"},
        )
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_token, token_session = issue_session(session, user, settings)
    user.last_login_at = datetime.now(UTC)
    record_audit_event(
        session,
        actor_user_id=user.id,
        action="auth.login",
        entity_type="session",
        entity_id=str(token_session.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
    )
    session.commit()
    return TokenResponse(
        access_token=raw_token,
        expires_at=token_session.expires_at,
        user=UserPublic.model_validate(user),
    )


@router.get("/me", response_model=UserPublic)
def current_user(auth: CurrentAuth) -> UserPublic:
    return UserPublic.model_validate(auth.user)


@router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    session: DatabaseSession,
    auth: CurrentAuth,
) -> LogoutResponse:
    auth.token_session.revoked_at = datetime.now(UTC)
    record_audit_event(
        session,
        actor_user_id=auth.user.id,
        action="auth.logout",
        entity_type="session",
        entity_id=str(auth.token_session.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
    )
    session.commit()
    return LogoutResponse()
