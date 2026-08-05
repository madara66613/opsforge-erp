from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

os.environ["OPSFORGE_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["OPSFORGE_ENVIRONMENT"] = "test"

from app import models  # noqa: E402, F401
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    test_engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    with Session(test_engine, expire_on_commit=False) as session:
        yield session
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_database() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
