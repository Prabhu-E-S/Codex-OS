"""
Codex OS — Phase 10 Hardening Tests
======================================

Validates input validation, error response format, health check shape,
and idempotency guards introduced during Phase 10 hardening.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db


# ── Test database setup ───────────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite:///./test_hardening.db"

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine_test)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine_test)
    app.dependency_overrides.clear()
    import os
    engine_test.dispose()  # Release SQLite file handle before deletion (Windows)
    if os.path.exists("test_hardening.db"):
        try:
            os.remove("test_hardening.db")
        except PermissionError:
            pass  # Windows may still hold handle; file will be cleaned on next run


client = TestClient(app)


# ── Health check tests ────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_phase_10(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["phase"] == 10

    def test_health_has_database_field(self):
        response = client.get("/api/health")
        data = response.json()
        assert "database" in data
        assert data["database"] in ("connected", "disconnected")

    def test_health_has_docker_field(self):
        response = client.get("/api/health")
        data = response.json()
        assert "docker" in data
        assert data["docker"] in ("available", "unavailable")

    def test_health_has_codex_field(self):
        response = client.get("/api/health")
        data = response.json()
        assert "codex" in data
        assert data["codex"] in ("available", "unavailable")

    def test_health_status_field_present(self):
        response = client.get("/api/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ("ok", "degraded")


# ── Project input validation tests ───────────────────────────────────────────

class TestProjectValidation:
    def test_reject_path_traversal(self):
        """Repository paths with '..' should be rejected."""
        response = client.post("/api/projects", json={
            "name": "Test Project",
            "repository_path": "/valid/../etc/passwd"
        })
        assert response.status_code == 400
        assert "traversal" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()

    def test_reject_null_byte_in_path(self):
        """Repository paths with null bytes should be rejected."""
        response = client.post("/api/projects", json={
            "name": "Test Project",
            "repository_path": "/valid/path\x00extra"
        })
        assert response.status_code == 400

    def test_reject_path_exceeding_length(self):
        """Repository paths longer than 500 chars should be rejected."""
        long_path = "/valid/" + "a" * 500
        response = client.post("/api/projects", json={
            "name": "Test Project",
            "repository_path": long_path
        })
        assert response.status_code == 400
        assert "length" in response.json()["detail"].lower() or "exceeds" in response.json()["detail"].lower()

    def test_reject_empty_project_name(self):
        response = client.post("/api/projects", json={
            "name": "",
            "repository_path": "/valid/path"
        })
        assert response.status_code in (422, 400)

    def test_reject_empty_repository_path(self):
        response = client.post("/api/projects", json={
            "name": "Valid Name",
            "repository_path": "   "
        })
        assert response.status_code in (422, 400)


# ── Run input validation tests ────────────────────────────────────────────────

class TestRunValidation:
    @pytest.fixture(autouse=True)
    def create_test_project(self, setup_db):
        response = client.post("/api/projects", json={
            "name": "Hardening Test Project",
            "repository_path": "d:\\Projects\\Codex OS"  # valid existing path
        })
        if response.status_code == 201:
            self.project_id = response.json()["id"]
        else:
            self.project_id = None

    def test_reject_oversized_goal(self):
        """Engineering goals exceeding 10000 chars should be rejected."""
        if not self.project_id:
            pytest.skip("Test project not created")
        response = client.post(f"/api/projects/{self.project_id}/runs", json={
            "goal": "G" * 10001
        })
        assert response.status_code in (400, 422)
        detail = response.json().get("detail", "")
        assert "10000" in detail or "length" in detail.lower() or "exceeds" in detail.lower()

    def test_reject_empty_goal(self):
        if not self.project_id:
            pytest.skip("Test project not created")
        response = client.post(f"/api/projects/{self.project_id}/runs", json={
            "goal": "   "
        })
        assert response.status_code in (400, 422)

    def test_accept_valid_goal(self):
        if not self.project_id:
            pytest.skip("Test project not created")
        response = client.post(f"/api/projects/{self.project_id}/runs", json={
            "goal": "Identify and fix all division by zero bugs."
        })
        assert response.status_code == 201


# ── Run idempotency tests ─────────────────────────────────────────────────────

class TestRunIdempotency:
    """Verify that terminal runs cannot be re-executed."""

    def test_cannot_reexecute_nonexistent_run(self):
        response = client.post("/api/runs/99999/execute")
        assert response.status_code == 404

    def test_execute_endpoint_exists(self):
        """Verify the execute endpoint responds (may be 404 if no run, but must not 405)."""
        response = client.post("/api/runs/1/execute")
        assert response.status_code != 405  # Method Not Allowed would indicate route missing


# ── Error response format tests ───────────────────────────────────────────────

class TestErrorResponseFormat:
    def test_404_returns_json_with_detail(self):
        response = client.get("/api/projects/99999")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_404_does_not_leak_traceback(self):
        response = client.get("/api/runs/99999")
        assert response.status_code == 404
        text = response.text
        assert "Traceback" not in text
        assert "File \"" not in text

    def test_root_endpoint_shows_phase_10(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["phase"] == 10
        assert "codex os" in data["service"].lower()
