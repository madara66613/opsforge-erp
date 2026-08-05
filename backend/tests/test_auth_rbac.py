from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AuditOutcome, UserRole
from app.core.security import hash_password, hash_session_token
from app.models.audit_log import AuditLog
from app.models.auth_session import AuthSession
from app.models.user import User


def add_user(
    session: Session,
    *,
    email: str,
    role: UserRole,
    password: str = "SecureDemo!2026",
    active: bool = True,
) -> User:
    user = User(
        id=uuid4(),
        email=email,
        full_name=f"{role.value.title()} User",
        role=role,
        password_hash=hash_password(password),
        is_active=active,
    )
    session.add(user)
    session.commit()
    return user


def login(client: TestClient, email: str, password: str = "SecureDemo!2026") -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return str(response.json()["access_token"])


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_me_and_logout_use_revocable_hashed_sessions(
    client: TestClient, db_session: Session
) -> None:
    user = add_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    token = login(client, user.email)
    stored_session = db_session.scalar(select(AuthSession))

    assert stored_session is not None
    assert stored_session.token_hash == hash_session_token(token)
    assert stored_session.token_hash != token
    login_audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "auth.login",
            AuditLog.outcome == AuditOutcome.SUCCESS,
        )
    )
    assert login_audit is not None
    assert login_audit.entity_id == str(stored_session.id)
    assert client.get("/api/v1/auth/me", headers=auth_header(token)).json()["role"] == "admin"

    logout_response = client.post("/api/v1/auth/logout", headers=auth_header(token))
    assert logout_response.status_code == 200
    assert logout_response.json() == {"status": "signed_out"}
    assert client.get("/api/v1/auth/me", headers=auth_header(token)).status_code == 401


def test_invalid_and_inactive_login_attempts_are_rejected_and_audited(
    client: TestClient, db_session: Session
) -> None:
    add_user(db_session, email="inactive@example.com", role=UserRole.SUPPORT, active=False)

    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "incorrect"},
    )
    inactive = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "SecureDemo!2026"},
    )

    assert wrong_password.status_code == 401
    assert inactive.status_code == 401
    failures = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "auth.login",
                AuditLog.outcome == AuditOutcome.FAILURE,
            )
        )
    )
    assert len(failures) == 2
    assert all("password" not in event.details for event in failures)


def test_admin_can_manage_users_while_operator_cannot(
    client: TestClient, db_session: Session
) -> None:
    admin = add_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    operator = add_user(db_session, email="operator@example.com", role=UserRole.OPERATOR)
    support = add_user(db_session, email="support@example.com", role=UserRole.SUPPORT)
    admin_token = login(client, admin.email)
    operator_token = login(client, operator.email)
    support_token = login(client, support.email)

    created = client.post(
        "/api/v1/users",
        headers=auth_header(admin_token),
        json={
            "email": "new.operator@example.com",
            "full_name": "New Operator",
            "password": "NewOperator!2026",
            "role": "operator",
        },
    )
    denied = client.post(
        "/api/v1/users",
        headers=auth_header(operator_token),
        json={
            "email": "blocked@example.com",
            "full_name": "Blocked User",
            "password": "BlockedUser!2026",
            "role": "support",
        },
    )

    assert created.status_code == 201
    assert "password" not in created.json()
    assert denied.status_code == 403
    assert client.get("/api/v1/users", headers=auth_header(support_token)).status_code == 200
    assert client.get("/api/v1/users", headers=auth_header(operator_token)).status_code == 403


def test_duplicate_user_and_self_deactivation_failures_are_audited(
    client: TestClient, db_session: Session
) -> None:
    admin = add_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    token = login(client, admin.email)
    duplicate_payload = {
        "email": admin.email,
        "full_name": "Duplicate Admin",
        "password": "DuplicateAdmin!2026",
        "role": "admin",
    }

    duplicate = client.post("/api/v1/users", headers=auth_header(token), json=duplicate_payload)
    self_deactivate = client.patch(
        f"/api/v1/users/{admin.id}",
        headers=auth_header(token),
        json={"is_active": False},
    )

    assert duplicate.status_code == 409
    assert self_deactivate.status_code == 400
    failed_actions = list(
        db_session.scalars(select(AuditLog.action).where(AuditLog.outcome == AuditOutcome.FAILURE))
    )
    assert "user.create" in failed_actions
    assert "user.update" in failed_actions


def test_support_can_read_audit_log_but_operator_cannot(
    client: TestClient, db_session: Session
) -> None:
    support = add_user(db_session, email="support@example.com", role=UserRole.SUPPORT)
    operator = add_user(db_session, email="operator@example.com", role=UserRole.OPERATOR)
    support_token = login(client, support.email)
    operator_token = login(client, operator.email)

    allowed = client.get("/api/v1/audit-logs", headers=auth_header(support_token))
    denied = client.get("/api/v1/audit-logs", headers=auth_header(operator_token))

    assert allowed.status_code == 200
    assert allowed.json()["total"] >= 2
    assert denied.status_code == 403
