from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import app


def test_health_is_live_and_has_request_id(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_ready_checks_database(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_reports_database_failure(client: TestClient) -> None:
    class BrokenSession:
        def execute(self, _statement: object) -> None:
            raise OperationalError("SELECT 1", {}, Exception("offline"))

    def broken_database() -> BrokenSession:
        return BrokenSession()

    previous_override = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = broken_database
    try:
        response = client.get("/ready")
    finally:
        app.dependency_overrides[get_db] = previous_override

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is unavailable"}


def test_version_exposes_non_secret_build_metadata(client: TestClient) -> None:
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "name": "OpsForge ERP",
        "version": "0.1.0",
        "environment": "test",
    }
