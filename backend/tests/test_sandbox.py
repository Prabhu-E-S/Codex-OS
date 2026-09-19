import os
import sys
import tempfile
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# Create temporary directory for workspace root and test db
temp_dir = tempfile.TemporaryDirectory()
temp_workspaces_root = Path(temp_dir.name) / "workspaces"
temp_workspaces_root.mkdir(parents=True, exist_ok=True)

temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{temp_db.name}"
os.environ["CODEX_WORKSPACE_ROOT"] = str(temp_workspaces_root)
os.environ["CODEX_GIT_PROVIDER"] = "mock"
os.environ["DOCKER_SANDBOX_PROVIDER"] = "mock"

from backend.config import settings
settings.CODEX_WORKSPACE_ROOT = str(temp_workspaces_root)
settings.CODEX_GIT_PROVIDER = "mock"
settings.DOCKER_SANDBOX_PROVIDER = "mock"

from backend.main import app
from backend.database import Base, engine, SessionLocal
from backend.models.project import Project
from backend.models.workspace import Workspace
from backend.models.sandbox import Sandbox
from backend.models.run import EngineeringRun
from backend.sandbox.models import SandboxStatus, SandboxSpec, CommandResult
from backend.sandbox.docker import (
    MockDockerProvider,
    RealDockerProvider,
    validate_mount_security,
    get_docker_provider,
)
from backend.sandbox.manager import SandboxManager
from backend.sandbox.executor import SandboxExecutor
from backend.sandbox.exceptions import (
    MountSecurityError,
    DockerUnavailableError,
    SandboxNotFoundError,
)

client = TestClient(app)

def setup_module():
    Base.metadata.create_all(bind=engine)

def teardown_module():
    temp_dir.cleanup()
    try:
        os.remove(temp_db.name)
    except Exception:
        pass


def test_docker_availability_detection():
    """Verify Docker availability check returns accurate status."""
    mock_provider = MockDockerProvider()
    is_avail, msg = mock_provider.is_available()
    assert is_avail is True
    assert "Mock Docker Provider Active" in msg

    # Simulate daemon offline
    mock_provider.available = False
    is_avail, msg = mock_provider.is_available()
    assert is_avail is False
    assert "Docker daemon unavailable" in msg

    # Test API endpoint
    res = client.get("/api/sandboxes/status")
    assert res.status_code == 200
    data = res.json()
    assert "available" in data
    assert "provider" in data


def test_mount_security_validation():
    """Verify mount security rejects root paths, system paths, and docker.sock."""
    # 1. Non-existent path must be rejected
    with pytest.raises(MountSecurityError):
        validate_mount_security("/non/existent/codex/path/xyz")

    # 2. Root directories must be rejected
    for root_path in ["/", "C:\\", "D:\\", "C:/"]:
        if os.path.exists(root_path):
            with pytest.raises(MountSecurityError) as exc_info:
                validate_mount_security(root_path)
            assert "strictly prohibited" in str(exc_info.value)

    # 3. Relative path traversal must be rejected
    with pytest.raises(MountSecurityError):
        validate_mount_security("../relative/path")

    # 4. Docker socket path must be rejected
    with pytest.raises(MountSecurityError) as exc_info:
        validate_mount_security("/var/run/docker.sock")
    assert "Docker daemon socket" in str(exc_info.value)

    # 5. Valid existing workspace directory must pass
    valid_dir = temp_workspaces_root / "test-valid-ws"
    valid_dir.mkdir(parents=True, exist_ok=True)
    safe_path = validate_mount_security(str(valid_dir))
    assert safe_path == str(valid_dir.resolve())


def test_sandbox_lifecycle():
    """Test full sandbox lifecycle: CREATE -> START -> EXECUTE -> STOP -> REMOVE."""
    # 1. Set up project and workspace
    ws_dir = temp_workspaces_root / "project-lifecycle" / "feat-sandbox-test"
    ws_dir.mkdir(parents=True, exist_ok=True)

    # Create a test file inside the workspace
    test_file = ws_dir / "app.py"
    test_file.write_text("print('Hello from isolated sandbox workspace!')\n")

    db = SessionLocal()
    try:
        project = Project(name="Lifecycle Project", repository_path=str(temp_workspaces_root))
        db.add(project)
        db.commit()
        db.refresh(project)

        workspace = Workspace(
            project_id=project.id,
            name="feat-sandbox-test",
            path=str(ws_dir),
            branch_name="codex/workspace/feat-sandbox-test",
            status="READY"
        )
        db.add(workspace)
        db.commit()
        db.refresh(workspace)

        mock_provider = MockDockerProvider()

        # 2. CREATE Sandbox
        spec = SandboxSpec(
            image="python:3.12-slim",
            cpu_limit=1.0,
            memory_limit="512m",
            timeout_seconds=30,
            network_enabled=False
        )
        sandbox = SandboxManager.create_sandbox(
            db=db,
            workspace_id=workspace.id,
            spec=spec,
            provider=mock_provider
        )
        assert sandbox.id is not None
        assert sandbox.status == SandboxStatus.CREATED.value
        assert sandbox.container_id is not None
        assert "mock-container" in sandbox.container_id

        # 3. START Sandbox
        sandbox = SandboxManager.start_sandbox(db=db, sandbox_id=sandbox.id, provider=mock_provider)
        assert sandbox.status == SandboxStatus.RUNNING.value
        assert sandbox.started_at is not None

        # 4. EXECUTE Command inside Sandbox
        exec_res = SandboxManager.execute_command(
            db=db,
            sandbox_id=sandbox.id,
            command="python app.py",
            provider=mock_provider
        )
        assert exec_res.exit_code == 0
        assert "Hello from isolated sandbox workspace!" in exec_res.stdout
        assert exec_res.timed_out is False
        assert exec_res.duration_ms > 0

        # 5. STOP Sandbox
        sandbox = SandboxManager.stop_sandbox(db=db, sandbox_id=sandbox.id, provider=mock_provider)
        assert sandbox.status == SandboxStatus.STOPPED.value
        assert sandbox.stopped_at is not None

        # 6. REMOVE Sandbox
        sandbox = SandboxManager.remove_sandbox(db=db, sandbox_id=sandbox.id, provider=mock_provider)
        assert sandbox.status == SandboxStatus.REMOVED.value
        assert sandbox.container_id is None

        # 7. CRITICAL VERIFICATION: Workspace files are PRESERVED!
        assert os.path.exists(str(test_file))
        assert test_file.read_text().strip() == "print('Hello from isolated sandbox workspace!')"

        # 8. RECREATION: A new sandbox can be created for the same workspace
        sandbox_2 = SandboxManager.create_sandbox(
            db=db,
            workspace_id=workspace.id,
            spec=spec,
            provider=mock_provider
        )
        assert sandbox_2.id != sandbox.id
        assert sandbox_2.status == SandboxStatus.CREATED.value
        assert sandbox_2.container_id is not None
    finally:
        db.close()


def test_command_timeout():
    """Verify command execution enforces timeouts and reports timeout flag."""
    ws_dir = temp_workspaces_root / "project-timeout" / "feat-timeout-test"
    ws_dir.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        project = Project(name="Timeout Project", repository_path=str(temp_workspaces_root))
        db.add(project)
        db.commit()

        workspace = Workspace(
            project_id=project.id,
            name="feat-timeout-test",
            path=str(ws_dir),
            branch_name="codex/workspace/feat-timeout-test",
            status="READY"
        )
        db.add(workspace)
        db.commit()

        mock_provider = MockDockerProvider()
        sandbox = SandboxManager.create_sandbox(db=db, workspace_id=workspace.id, provider=mock_provider)
        SandboxManager.start_sandbox(db=db, sandbox_id=sandbox.id, provider=mock_provider)

        # Execute command with 1s timeout that sleeps for 5s
        res = SandboxManager.execute_command(
            db=db,
            sandbox_id=sandbox.id,
            command="python -c \"import time; time.sleep(5)\"",
            timeout=1,
            provider=mock_provider
        )
        assert res.timed_out is True
        assert res.exit_code == 124
        assert "exceeded timeout limit" in res.stderr
    finally:
        db.close()


def test_sandbox_rest_api_flow():
    """Test REST API endpoints for sandbox management."""
    # 1. Create project
    temp_repo = tempfile.mkdtemp()
    res = client.post("/api/projects", json={
        "name": "Sandbox API Test Project",
        "repository_path": temp_repo
    })
    assert res.status_code == 201
    project_id = res.json()["id"]

    # 2. Create workspace
    res = client.post(f"/api/projects/{project_id}/workspaces", json={
        "name": "api-sandbox-ws"
    })
    assert res.status_code == 201
    ws_id = res.json()["id"]

    # 3. Create sandbox via POST /api/workspaces/{ws_id}/sandbox
    res = client.post(f"/api/workspaces/{ws_id}/sandbox", json={
        "image": "python:3.12-slim",
        "cpu_limit": 1.0,
        "memory_limit": "512m",
        "timeout_seconds": 45,
        "network_enabled": False
    })
    assert res.status_code == 201
    sb_data = res.json()
    assert sb_data["workspace_id"] == ws_id
    assert sb_data["status"] == "CREATED"
    sandbox_id = sb_data["id"]

    # 4. Get active sandbox for workspace
    res = client.get(f"/api/workspaces/{ws_id}/sandbox")
    assert res.status_code == 200
    assert res.json()["id"] == sandbox_id

    # 5. Get sandbox by ID
    res = client.get(f"/api/sandboxes/{sandbox_id}")
    assert res.status_code == 200
    assert res.json()["id"] == sandbox_id

    # 6. Start sandbox
    res = client.post(f"/api/sandboxes/{sandbox_id}/start")
    assert res.status_code == 200
    assert res.json()["status"] == "RUNNING"

    # 7. Execute command inside sandbox
    res = client.post(f"/api/sandboxes/{sandbox_id}/execute", json={
        "command": "python -c \"print('API test inside sandbox')\"",
        "timeout": 10
    })
    assert res.status_code == 200
    exec_data = res.json()
    assert exec_data["exit_code"] == 0
    assert "API test inside sandbox" in exec_data["stdout"]

    # 8. Stop sandbox
    res = client.post(f"/api/sandboxes/{sandbox_id}/stop")
    assert res.status_code == 200
    assert res.json()["status"] == "STOPPED"

    # 9. Remove sandbox
    res = client.delete(f"/api/sandboxes/{sandbox_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "REMOVED"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
