from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import generate_session_token, hash_session_token, verify_password
from app.models.auth_session import AuthSession
from app.models.user import User


def normalize_email(email: str) -> str:
    return email.strip().lower()


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    user = session.scalar(select(User).where(User.email == normalize_email(email)))
    if not verify_password(password, user.password_hash if user else None):
        return None
    if user is None or not user.is_active:
        return None
    return user


def issue_session(session: Session, user: User, settings: Settings) -> tuple[str, AuthSession]:
    raw_token = generate_session_token()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.session_ttl_minutes)
    token_session = AuthSession(
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        expires_at=expires_at,
    )
    session.add(token_session)
    session.flush()
    return raw_token, token_session
