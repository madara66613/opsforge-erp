from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import Permission, has_permission
from app.core.security import hash_session_token
from app.db.session import get_db
from app.models.auth_session import AuthSession
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False, description="Opaque OpsForge session token")
DatabaseSession = Annotated[Session, Depends(get_db)]
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


@dataclass(frozen=True)
class AuthContext:
    user: User
    token_session: AuthSession


def get_current_auth(
    request: Request,
    session: DatabaseSession,
    credentials: BearerCredentials,
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.now(UTC)
    token_session = session.scalar(
        select(AuthSession)
        .options(joinedload(AuthSession.user))
        .where(
            AuthSession.token_hash == hash_session_token(credentials.credentials),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
    )
    if token_session is None or not token_session.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )

    request.state.user_id = str(token_session.user.id)
    return AuthContext(user=token_session.user, token_session=token_session)


CurrentAuth = Annotated[AuthContext, Depends(get_current_auth)]


def require_permission(permission: Permission) -> object:
    def authorize(auth: CurrentAuth) -> AuthContext:
        if not has_permission(auth.user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission.value}",
            )
        return auth

    return authorize
