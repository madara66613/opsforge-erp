from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.core.enums import UserRole
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


@dataclass(frozen=True)
class DemoUser:
    id: UUID
    email: str
    full_name: str
    role: UserRole
    password: str


DEMO_USERS = (
    DemoUser(
        id=UUID("10000000-0000-0000-0000-000000000001"),
        email="admin@demo.opsforge.dev",
        full_name="Alex Morgan",
        role=UserRole.ADMIN,
        password="AdminDemo!2026",
    ),
    DemoUser(
        id=UUID("10000000-0000-0000-0000-000000000002"),
        email="operator@demo.opsforge.dev",
        full_name="Olivia Chen",
        role=UserRole.OPERATOR,
        password="OperatorDemo!2026",
    ),
    DemoUser(
        id=UUID("10000000-0000-0000-0000-000000000003"),
        email="support@demo.opsforge.dev",
        full_name="Sam Rivera",
        role=UserRole.SUPPORT,
        password="SupportDemo!2026",
    ),
)


def seed_demo_users() -> None:
    settings = get_settings()
    if settings.environment not in {"local", "test"}:
        raise RuntimeError("Demo data can only be seeded in local or test environments")

    with SessionLocal() as session:
        for demo_user in DEMO_USERS:
            existing = session.scalar(select(User).where(User.email == demo_user.email))
            if existing is None:
                session.add(
                    User(
                        id=demo_user.id,
                        email=demo_user.email,
                        full_name=demo_user.full_name,
                        role=demo_user.role,
                        password_hash=hash_password(demo_user.password),
                        is_active=True,
                    )
                )
        session.commit()


if __name__ == "__main__":
    seed_demo_users()
    print("Seeded OpsForge ERP demo users.")
