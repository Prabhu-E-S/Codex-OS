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

# Create temporary directory for workspace root and db
temp_dir = tempfile.TemporaryDirectory()
temp_workspaces_root = Path(temp_dir.name) / "workspaces"
temp_workspaces_root.mkdir(parents=True, exist_ok=True)

temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{temp_db.name}"
os.environ["CODEX_WORKSPACE_ROOT"] = str(temp_workspaces_root)
os.environ["CODEX_GIT_PROVIDER"] = "mock"

from backend.config import settings
settings.CODEX_WORKSPACE_ROOT = str(temp_workspaces_root)
settings.CODEX_GIT_PROVIDER = "mock"

from backend.main import app
from backend.database import Base, engine, SessionLocal
from backend.models.project import Project
from backend.models.workspace import Workspace
from backend.models.run import EngineeringRun
from backend.workspace.git import MockGitWorkspaceProvider
from backend.workspace.manager import WorkspaceManager
from backend.workspace.exceptions import (
    InvalidWorkspaceNameError,
    WorkspacePathEscapeError,
    GitError,
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


def test_worktree_name_validation():
    """Verify regex validation on workspace names."""
    invalid_names = [
        "../escape",
        "..\\escape",
        "has space",
        "has/slash",
        "-leading-dash",
        "_leading_underscore",
        "bad$char",
        "name;rm",
        "",
        "a" * 65,  # Too long
    ]
    for bad_name in invalid_names:
        with pytest.raises((InvalidWorkspaceNameError, WorkspacePathEscapeError)):
            WorkspaceManager.validate_workspace_name(bad_name)


def test_worktree_path_escape_prevention():
    """Verify path traversal resolution check prevents root escapes."""
    # Direct path escape attempt must raise WorkspacePathEscapeError
    with pytest.raises((InvalidWorkspaceNameError, WorkspacePathEscapeError)):
        WorkspaceManager.resolve_workspace_path(1, "../escape_outside")


def test_create_worktree_workspace_flow():
    """Test full creation flow for a worktree workspace."""
    # 1. Create a project
    temp_repo = tempfile.mkdtemp()
    res = client.post("/api/projects", json={
        "name": "Phase 3 Project",
        "repository_path": temp_repo
    })
    assert res.status_code == 201
    project_id = res.json()["id"]

    # 2. Create workspace via API
    res = client.post(f"/api/projects/{project_id}/workspaces", json={
        "name": "feat-user-auth"
    })
    assert res.status_code == 201
    ws_data = res.json()
    assert ws_data["name"] == "feat-user-auth"
    assert ws_data["branch_name"] == "codex/workspace/feat-user-auth"
    assert ws_data["status"] == "READY"
    assert ws_data["project_id"] == project_id
    assert os.path.exists(ws_data["path"])

    ws_id = ws_data["id"]

    # 3. Fetch workspace by ID
    res = client.get(f"/api/workspaces/{ws_id}")
    assert res.status_code == 200
    assert res.json()["id"] == ws_id
    assert res.json()["name"] == "feat-user-auth"

    # 4. List workspaces for project
    res = client.get(f"/api/projects/{project_id}/workspaces")
    assert res.status_code == 200
    workspaces = res.json()
    assert len(workspaces) == 1
    assert workspaces[0]["id"] == ws_id

    # 5. Duplicate name within same project should be rejected
    res = client.post(f"/api/projects/{project_id}/workspaces", json={
        "name": "feat-user-auth"
    })
    assert res.status_code == 409

    # 6. Delete workspace
    res = client.delete(f"/api/workspaces/{ws_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "REMOVED"

    # Verify listing does not return deleted workspace
    res = client.get(f"/api/projects/{project_id}/workspaces")
    assert res.status_code == 200
    assert len(res.json()) == 0


def test_worktree_error_handling():
    """Verify that provider errors correctly update workspace to ERROR status."""
    db = SessionLocal()
    try:
        # Create provider that fails on worktree creation
        class FailingMockProvider(MockGitWorkspaceProvider):
            def create_worktree(self, repo_path: str, worktree_path: str, branch_name: str, base_commit: str = "HEAD"):
                raise GitError("Simulated git worktree add failure: branch already exists")

        failing_provider = FailingMockProvider()

        # Create project
        project = Project(name="Error Test Project", repository_path=str(temp_workspaces_root))
        db.add(project)
        db.commit()
        db.refresh(project)

        with pytest.raises(GitError):
            WorkspaceManager.create_workspace(
                db=db,
                project_id=project.id,
                name="failing-worktree",
                git_provider=failing_provider,
            )

        # Verify record in DB is marked ERROR
        ws = db.query(Workspace).filter(
            Workspace.project_id == project.id,
            Workspace.name == "failing-worktree"
        ).first()
        assert ws is not None
        assert ws.status == "ERROR"
        assert "Simulated git worktree add failure" in ws.error_message
    finally:
        db.close()


def test_execution_routes_to_workspace_path():
    """
    Verify that when an engineering run specifies workspace_id,
    Codex execution targets the workspace path instead of project repository path,
    and updates workspace status to IN_USE during execution and back to READY afterwards.
    """
    temp_repo = tempfile.mkdtemp()
    res = client.post("/api/projects", json={
        "name": "Execution Routing Project",
        "repository_path": temp_repo
    })
    assert res.status_code == 201
    project_id = res.json()["id"]

    # Create workspace
    res = client.post(f"/api/projects/{project_id}/workspaces", json={
        "name": "isolated-test-ws"
    })
    assert res.status_code == 201
    ws_data = res.json()
    ws_id = ws_data["id"]
    ws_path = ws_data["path"]

    # Configure mock Codex executable using python
    settings.CODEX_COMMAND = sys.executable

    # Write a test runner script in python that reports its cwd
    test_script = tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w")
    test_script.write(
        "import os\n"
        "print(f'[MOCK_CODEX] Current Working Directory: {os.getcwd()}')\n"
    )
    test_script.close()

    # Point CODEX_COMMAND to python with this script
    settings.CODEX_COMMAND = f'"{sys.executable}" "{test_script.name}"'

    # Create run with workspace_id
    res = client.post(f"/api/projects/{project_id}/runs", json={
        "goal": "Verify execution in worktree workspace",
        "workspace_id": ws_id
    })
    assert res.status_code == 201
    run_data = res.json()
    assert run_data["workspace_id"] == ws_id
    assert run_data["workspace_name"] == "isolated-test-ws"
    run_id = run_data["id"]

    # Execute run
    res = client.post(f"/api/runs/{run_id}/execute")
    assert res.status_code == 200

    # Wait briefly for execution worker to complete
    time.sleep(1.0)

    # Check run logs
    res = client.get(f"/api/runs/{run_id}/logs")
    assert res.status_code == 200
    logs = res.json()
    assert logs["workspace_id"] == ws_id
    assert logs["workspace_name"] == "isolated-test-ws"
    assert logs["status"] == "COMPLETED"

    # Verify that the output reflects cwd was indeed the workspace path
    assert "[MOCK_CODEX] Current Working Directory:" in logs["stdout"]
    # Path should match normalized ws_path
    assert Path(ws_path).resolve().name in logs["stdout"]

    # Verify workspace status returned to READY
    res = client.get(f"/api/workspaces/{ws_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "READY"

    # Clean up test script
    try:
        os.remove(test_script.name)
    except Exception:
        pass


if __name__ == "__main__":
    pytest.main(["-v", __file__])
