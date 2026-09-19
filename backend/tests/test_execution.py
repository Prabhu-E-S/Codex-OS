import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import time
import tempfile
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient


# Set test database
temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{temp_db.name}"

from backend.main import app
from backend.database import Base, engine, SessionLocal
from backend.models import Project, EngineeringRun
from backend.codex.runner import CodexRunner
from backend.codex.models import RunStatus

client = TestClient(app)

def setup_module():
    Base.metadata.create_all(bind=engine)

def teardown_module():
    try:
        os.remove(temp_db.name)
    except Exception:
        pass

def test_codex_availability_detection():
    # When CODEX_COMMAND is not set and codex binary is absent
    os.environ.pop("CODEX_COMMAND", None)
    from backend.config import settings
    settings.CODEX_COMMAND = None

    is_avail, cmd, err = CodexRunner.is_available()
    assert is_avail is False
    assert "Codex is not available" in err

def test_codex_unavailable_flow():
    # Setup test project and run
    from backend.config import settings
    settings.CODEX_COMMAND = None

    temp_repo = tempfile.mkdtemp()
    
    # 1. Create project
    res = client.post("/api/projects", json={
        "name": "Test Project Unavail",
        "repository_path": temp_repo
    })
    assert res.status_code == 201
    project_id = res.json()["id"]

    # 2. Create run
    res = client.post(f"/api/projects/{project_id}/runs", json={
        "goal": "Test unavailable execution"
    })
    assert res.status_code == 201
    run_id = res.json()["id"]

    # 3. Execute run
    res = client.post(f"/api/runs/{run_id}/execute")
    assert res.status_code == 200
    assert res.json()["status"] in ("STARTING", "FAILED")

    # Give background thread time to process
    time.sleep(0.5)

    # 4. Check run status & logs
    res = client.get(f"/api/runs/{run_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "FAILED"
    assert "Codex is not available in the current environment" in data["error_message"]

    res = client.get(f"/api/runs/{run_id}/logs")
    assert res.status_code == 200
    logs = res.json()
    assert logs["status"] == "FAILED"
    assert "Codex is not available" in logs["stderr"]

def test_invalid_repository_path_flow():
    from backend.config import settings
    # Set a valid executable (python) so it passes the availability check
    settings.CODEX_COMMAND = sys.executable

    # 1. Create project with non-existent path
    non_existent_path = os.path.join(tempfile.gettempdir(), "non_existent_codex_dir_xyz_123")
    if os.path.exists(non_existent_path):
        os.rmdir(non_existent_path)

    res = client.post("/api/projects", json={
        "name": "Invalid Path Project",
        "repository_path": non_existent_path
    })
    assert res.status_code == 201
    project_id = res.json()["id"]

    # 2. Create run
    res = client.post(f"/api/projects/{project_id}/runs", json={
        "goal": "Test invalid repository path"
    })
    assert res.status_code == 201
    run_id = res.json()["id"]

    # 3. Execute run
    res = client.post(f"/api/runs/{run_id}/execute")
    assert res.status_code == 200

    time.sleep(0.5)

    # 4. Verify run failed with clear path error
    res = client.get(f"/api/runs/{run_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "FAILED"
    assert res.json()["error_message"] == "The configured project path does not exist."

def test_successful_execution_and_logs():
    from backend.config import settings
    temp_repo = tempfile.mkdtemp()

    # Configure a command that outputs text and exits cleanly
    test_script = "import time; print('Analyzing codebase...'); time.sleep(0.2); print('Changes applied successfully.')"
    settings.CODEX_COMMAND = f'"{sys.executable}" -c "{test_script}"'

    res = client.post("/api/projects", json={
        "name": "Success Project",
        "repository_path": temp_repo
    })
    project_id = res.json()["id"]

    res = client.post(f"/api/projects/{project_id}/runs", json={
        "goal": "Refactor data models"
    })
    run_id = res.json()["id"]

    # Execute
    res = client.post(f"/api/runs/{run_id}/execute")
    assert res.status_code == 200

    # Wait for completion
    for _ in range(30):
        time.sleep(0.2)
        res = client.get(f"/api/runs/{run_id}")
        if res.json()["status"] in ("COMPLETED", "FAILED"):
            break

    run_data = res.json()
    assert run_data["status"] == "COMPLETED"
    assert run_data["exit_code"] == 0
    assert "Analyzing codebase..." in run_data["stdout"]
    assert "Changes applied successfully." in run_data["stdout"]

    # Check logs endpoint
    res = client.get(f"/api/runs/{run_id}/logs")
    assert res.status_code == 200
    logs = res.json()
    assert logs["status"] == "COMPLETED"
    assert "Analyzing codebase..." in logs["stdout"]

def test_cancel_execution():
    from backend.config import settings
    temp_repo = tempfile.mkdtemp()

    # Long running command (10 seconds)
    long_script = "import time; print('Starting long process...'); time.sleep(10); print('Finished')"
    settings.CODEX_COMMAND = f'"{sys.executable}" -c "{long_script}"'

    res = client.post("/api/projects", json={
        "name": "Cancel Project",
        "repository_path": temp_repo
    })
    project_id = res.json()["id"]

    res = client.post(f"/api/projects/{project_id}/runs", json={
        "goal": "Long running task to cancel"
    })
    run_id = res.json()["id"]

    # Execute
    client.post(f"/api/runs/{run_id}/execute")
    time.sleep(0.5)

    # Verify running
    res = client.get(f"/api/runs/{run_id}")
    assert res.json()["status"] in ("STARTING", "RUNNING")

    # Cancel
    cancel_res = client.post(f"/api/runs/{run_id}/cancel")
    assert cancel_res.status_code == 200

    # Verify status is CANCELLED
    time.sleep(0.5)
    res = client.get(f"/api/runs/{run_id}")
    assert res.json()["status"] == "CANCELLED"
    assert "cancelled" in res.json()["error_message"].lower()

def test_timeout_execution():
    from backend.config import settings
    temp_repo = tempfile.mkdtemp()

    # Configure short timeout (1 second) and a 5-second script
    settings.CODEX_EXECUTION_TIMEOUT = 1
    sleep_script = "import time; print('Sleeping...'); time.sleep(5); print('Awake')"
    settings.CODEX_COMMAND = f'"{sys.executable}" -c "{sleep_script}"'


    res = client.post("/api/projects", json={
        "name": "Timeout Project",
        "repository_path": temp_repo
    })
    project_id = res.json()["id"]

    res = client.post(f"/api/projects/{project_id}/runs", json={
        "goal": "Task that will timeout"
    })
    run_id = res.json()["id"]

    # Execute
    client.post(f"/api/runs/{run_id}/execute")

    # Wait up to 3 seconds
    for _ in range(15):
        time.sleep(0.3)
        res = client.get(f"/api/runs/{run_id}")
        if res.json()["status"] in ("TIMEOUT", "FAILED"):
            break

    run_data = res.json()
    assert run_data["status"] == "TIMEOUT"
    assert "exceeded the configured time limit" in run_data["error_message"]

if __name__ == "__main__":
    setup_module()
    try:
        print("1. Testing availability detection...")
        test_codex_availability_detection()
        print("OK")

        print("2. Testing unavailable flow...")
        test_codex_unavailable_flow()
        print("OK")

        print("3. Testing invalid repository path...")
        test_invalid_repository_path_flow()
        print("OK")

        print("4. Testing successful execution and logs...")
        test_successful_execution_and_logs()
        print("OK")

        print("5. Testing cancellation...")
        test_cancel_execution()
        print("OK")

        print("6. Testing timeout...")
        test_timeout_execution()
        print("OK")

        print("\nALL PHASE 2 EXECUTION TESTS PASSED SUCCESSFULLY!")
    finally:
        teardown_module()
