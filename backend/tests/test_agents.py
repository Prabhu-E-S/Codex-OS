import os
import shutil
import tempfile
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models.project import Project
from backend.models.run import EngineeringRun
from backend.models.workspace import Workspace
from backend.models.sandbox import Sandbox
from backend.models.agent_execution import AgentExecution
from backend.agents.models import AgentType, AgentStatus, AgentResult
from backend.agents.context import AgentContext
from backend.agents.architect import ArchitectAgent
from backend.agents.builder import BuilderAgent
from backend.agents.tester import TesterAgent
from backend.agents.manager import AgentManager
from backend.codex.models import RunStatus, ExecutionResult
from backend.workspace.git import MockGitWorkspaceProvider
from backend.sandbox.docker import MockDockerProvider
from backend.sandbox.manager import SandboxManager

from backend.database import Base, engine, SessionLocal

client = TestClient(app)

def make_exec_result(status=RunStatus.COMPLETED, exit_code=0, stdout="", stderr="", error_message=None):
    now = datetime.now(timezone.utc)
    return ExecutionResult(
        status=status,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        error_message=error_message,
        started_at=now,
        completed_at=now
    )

@pytest.fixture(autouse=True)
def setup_teardown():
    Base.metadata.create_all(bind=engine)
    temp_dir = tempfile.mkdtemp(prefix="codex_agents_repo_")
    yield temp_dir
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_agent_context_and_previous_results(setup_teardown):
    """Test AgentContext initialization and previous results retrieval."""
    temp_dir = setup_teardown
    arch_result = AgentResult(
        agent_type=AgentType.ARCHITECT,
        agent_name="Architect Agent",
        status=AgentStatus.COMPLETED,
        output="Plan: 1. Update login logic."
    )
    context = AgentContext(
        project_id=1,
        project_name="AuthProject",
        repository_path=temp_dir,
        engineering_run_id=42,
        engineering_goal="Fix login validation",
        previous_results={AgentType.ARCHITECT: arch_result}
    )

    assert context.project_name == "AuthProject"
    assert context.get_previous_result(AgentType.ARCHITECT) == arch_result
    assert context.get_previous_result(AgentType.BUILDER) is None


def test_architect_agent_execution(setup_teardown):
    """Verify ArchitectAgent generates a plan without modifying code."""
    temp_dir = setup_teardown
    agent = ArchitectAgent()
    context = AgentContext(
        project_id=1,
        project_name="TestApp",
        repository_path=temp_dir,
        engineering_run_id=10,
        engineering_goal="Implement user sessions"
    )

    mock_exec = make_exec_result(
        status=RunStatus.COMPLETED,
        exit_code=0,
        stdout="### Architecture Overview\nSession handling in session.py.\n\n### Step-by-Step Implementation Plan\n1. Add Redis session store.",
        stderr=""
    )

    with patch("backend.codex.runner.CodexRunner.execute", return_value=mock_exec) as mock_runner:
        result = agent.run(context)
        assert result.status == AgentStatus.COMPLETED
        assert "Step-by-Step Implementation Plan" in result.output
        mock_runner.assert_called_once()


def test_builder_agent_execution_with_architect_plan(setup_teardown):
    """Verify BuilderAgent receives Architect plan and implements changes."""
    temp_dir = setup_teardown
    agent = BuilderAgent()
    arch_result = AgentResult(
        agent_type=AgentType.ARCHITECT,
        agent_name="Architect Agent",
        status=AgentStatus.COMPLETED,
        output="Step 1: Edit auth.py"
    )
    context = AgentContext(
        project_id=1,
        project_name="TestApp",
        repository_path=temp_dir,
        engineering_run_id=11,
        engineering_goal="Fix auth issue",
        previous_results={AgentType.ARCHITECT: arch_result}
    )

    mock_exec = make_exec_result(
        status=RunStatus.COMPLETED,
        exit_code=0,
        stdout="### Summary of Implemented Changes\nUpdated auth.py validation rules.",
        stderr=""
    )

    with patch("backend.codex.runner.CodexRunner.execute", return_value=mock_exec):
        result = agent.run(context)
        assert result.status == AgentStatus.COMPLETED
        assert "Updated auth.py validation rules" in result.output

    # Test missing Architect plan
    bad_context = AgentContext(
        project_id=1,
        project_name="TestApp",
        repository_path=temp_dir,
        engineering_run_id=12,
        engineering_goal="Fix auth issue"
    )
    fail_result = agent.run(bad_context)
    assert fail_result.status == AgentStatus.FAILED
    assert "Architect plan is missing" in fail_result.error_message


def test_tester_agent_execution_and_metrics(setup_teardown):
    """Verify TesterAgent reports structured test status and failure detection."""
    temp_dir = setup_teardown
    agent = TesterAgent()
    arch_res = AgentResult(AgentType.ARCHITECT, "Architect", AgentStatus.COMPLETED, "Plan...")
    build_res = AgentResult(AgentType.BUILDER, "Builder", AgentStatus.COMPLETED, "Implementation...")

    context = AgentContext(
        project_id=1,
        project_name="TestApp",
        repository_path=temp_dir,
        engineering_run_id=13,
        engineering_goal="Verify tests",
        previous_results={AgentType.ARCHITECT: arch_res, AgentType.BUILDER: build_res}
    )

    # 1. Success case
    pass_exec = make_exec_result(
        status=RunStatus.COMPLETED,
        exit_code=0,
        stdout="Tests Run: 12\nPassed: 12\nFailed: 0\nStatus: PASSED\n\n### Test Results Breakdown\nAll 12 passed.",
        stderr=""
    )
    with patch("backend.codex.runner.CodexRunner.execute", return_value=pass_exec):
        res = agent.run(context)
        assert res.status == AgentStatus.COMPLETED
        assert res.exit_code == 0

    # 2. Failure detection in test output
    fail_exec = make_exec_result(
        status=RunStatus.COMPLETED,
        exit_code=0,
        stdout="Tests Run: 12\nPassed: 10\nFailed: 2\nStatus: FAILED\n\n### Failure Details\nAssertionError in test_login",
        stderr=""
    )
    with patch("backend.codex.runner.CodexRunner.execute", return_value=fail_exec):
        res = agent.run(context)
        assert res.status == AgentStatus.FAILED
        assert res.exit_code == 1


def test_sequential_workflow_and_agent_isolation(setup_teardown):
    """
    Test full sequential workflow: Architect -> Builder -> Tester.
    Verifies that each agent executes in its own distinct isolated workspace.
    """
    temp_dir = setup_teardown
    db = SessionLocal()
    project = Project(name="WorkflowProject", repository_path=temp_dir)
    db.add(project)
    db.commit()

    run = EngineeringRun(project_id=project.id, goal="Build payment integration")
    db.add(run)
    db.commit()

    arch_res = make_exec_result(RunStatus.COMPLETED, 0, "Architect Plan: build payment gateway", "")
    build_res = make_exec_result(RunStatus.COMPLETED, 0, "Builder Implemented: added gateway.py", "")
    test_res = make_exec_result(RunStatus.COMPLETED, 0, "Tests Run: 5\nPassed: 5\nFailed: 0\nStatus: PASSED", "")
    breaker_res = make_exec_result(RunStatus.COMPLETED, 0, "Tests Generated: 2\nTests Executed: 2\nTests Passed: 2\nTests Failed: 0\n```json\n[]\n```", "")
    sec_res = make_exec_result(RunStatus.COMPLETED, 0, "Security Posture Summary: No vulnerabilities found.\n```json\n[]\n```", "")

    side_effects = [arch_res, build_res, test_res, breaker_res, sec_res]

    with patch("backend.codex.runner.CodexRunner.execute", side_effect=side_effects):
        with patch("backend.workspace.manager.get_git_provider", return_value=MockGitWorkspaceProvider()):
            with patch("backend.sandbox.manager.get_docker_provider", return_value=MockDockerProvider()):
                AgentManager._workflow_worker(run.id, db=db)

    db.refresh(run)
    assert run.status == RunStatus.COMPLETED.value
    assert "Autonomous Agent Team Workflow Completed" in run.stdout

    # Verify agent executions
    execs = db.query(AgentExecution).filter(AgentExecution.engineering_run_id == run.id).order_by(AgentExecution.id.asc()).all()
    assert len(execs) == 5
    assert [e.agent_type for e in execs] == ["ARCHITECT", "BUILDER", "TESTER", "BREAKER", "SECURITY"]
    assert all(e.status == AgentStatus.COMPLETED.value for e in execs)

    # Verify workspace isolation: agents must not share the same workspace
    ws_ids = [e.workspace_id for e in execs]
    assert len(set(ws_ids)) == 5, f"Agents must operate in separate workspaces, got: {ws_ids}"
    db.close()


def test_downstream_agents_receive_builder_target_snapshot(setup_teardown):
    """
    Builder changes must be propagated into downstream isolated workspaces so
    Tester/Breaker/Security verify the implementation rather than a fresh baseline.
    """
    temp_dir = setup_teardown
    db = SessionLocal()
    project = Project(name="TargetSnapshotProject", repository_path=temp_dir)
    db.add(project)
    db.commit()

    run = EngineeringRun(
        project_id=project.id,
        goal="Update demo calculator",
        target_subpath="demo-project",
    )
    db.add(run)
    db.commit()

    marker_file = os.path.join("app", "calculator.py")

    def fake_execute(run_id, goal, repository_path, project_name, timeout_seconds=None):
        os.makedirs(os.path.join(repository_path, "app"), exist_ok=True)
        if "run" in repository_path and "builder" in repository_path:
            with open(os.path.join(repository_path, marker_file), "w", encoding="utf-8") as f:
                f.write("def divide(a, b):\n    return 'builder-change'\n")
            return make_exec_result(RunStatus.COMPLETED, 0, "Builder Implemented: changed calculator.py", "")

        if "tester" in repository_path or "breaker" in repository_path or "security" in repository_path:
            assert os.path.exists(os.path.join(repository_path, marker_file))

        if "architect" in repository_path:
            return make_exec_result(RunStatus.COMPLETED, 0, "Architect Plan: change calculator.py", "")
        if "tester" in repository_path:
            return make_exec_result(RunStatus.COMPLETED, 0, "Tests Run: 1\nPassed: 1\nFailed: 0\nStatus: PASSED", "")
        if "breaker" in repository_path:
            return make_exec_result(RunStatus.COMPLETED, 0, "Tests Generated: 1\nTests Executed: 1\nTests Passed: 1\nTests Failed: 0\n```json\n[]\n```", "")
        return make_exec_result(RunStatus.COMPLETED, 0, "Security Posture Summary: No vulnerabilities found.\n```json\n[]\n```", "")

    with patch("backend.codex.runner.CodexRunner.execute", side_effect=fake_execute):
        with patch("backend.workspace.manager.get_git_provider", return_value=MockGitWorkspaceProvider()):
            with patch("backend.sandbox.manager.get_docker_provider", return_value=MockDockerProvider()):
                with patch.object(SandboxManager, "execute_command") as mock_sandbox_execute:
                    AgentManager._workflow_worker(run.id, db=db)
                    mock_sandbox_execute.assert_not_called()

    db.refresh(run)
    assert run.status == RunStatus.COMPLETED.value
    execs = db.query(AgentExecution).filter(AgentExecution.engineering_run_id == run.id).order_by(AgentExecution.id.asc()).all()
    assert len(execs) == 5
    assert all(e.status == AgentStatus.COMPLETED.value for e in execs)
    assert len({e.workspace_id for e in execs}) == 5
    assert all(e.sandbox_id is not None for e in execs)
    db.close()


def test_workflow_halts_on_failure_no_retries(setup_teardown):
    """
    Verify that if an agent fails (e.g. Builder), the workflow HALTS immediately.
    Tester, Breaker, and Security must NOT be executed, and no automatic retries occur.
    """
    temp_dir = setup_teardown
    db = SessionLocal()
    project = Project(name="FailProject", repository_path=temp_dir)
    db.add(project)
    db.commit()

    run = EngineeringRun(project_id=project.id, goal="Buggy feature")
    db.add(run)
    db.commit()

    arch_res = make_exec_result(RunStatus.COMPLETED, 0, "Architect Plan: build feature", "")
    build_fail = make_exec_result(RunStatus.FAILED, 1, "", "SyntaxError in builder execution", error_message="SyntaxError in builder execution")

    with patch("backend.codex.runner.CodexRunner.execute", side_effect=[arch_res, build_fail]):
        with patch("backend.workspace.manager.get_git_provider", return_value=MockGitWorkspaceProvider()):
            with patch("backend.sandbox.manager.get_docker_provider", return_value=MockDockerProvider()):
                AgentManager._workflow_worker(run.id, db=db)

    db.refresh(run)
    assert run.status == RunStatus.FAILED.value
    assert "Builder Agent failed" in run.error_message

    execs = db.query(AgentExecution).filter(AgentExecution.engineering_run_id == run.id).order_by(AgentExecution.id.asc()).all()
    assert len(execs) == 5
    assert execs[0].status == AgentStatus.COMPLETED.value
    assert execs[1].status == AgentStatus.FAILED.value
    assert execs[2].status == AgentStatus.PENDING.value  # Tester was NOT executed!
    assert execs[3].status == AgentStatus.PENDING.value  # Breaker was NOT executed!
    assert execs[4].status == AgentStatus.PENDING.value  # Security was NOT executed!
    db.close()


def test_agent_rest_api_flow(setup_teardown):
    """Test REST API endpoints for agent workflow execution, status, and cancellation."""
    temp_dir = setup_teardown
    db = SessionLocal()
    project = Project(name="ApiProject", repository_path=temp_dir)
    db.add(project)
    db.commit()

    run = EngineeringRun(project_id=project.id, goal="API workflow test")
    db.add(run)
    db.commit()
    run_id = run.id
    db.close()

    # 1. Trigger agent workflow
    resp = client.post(f"/api/runs/{run_id}/agents/execute")
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == run_id
    assert len(data["agents"]) == 5
    assert data["agents"][0]["agent_type"] == "ARCHITECT"

    # 2. Get run agents
    resp = client.get(f"/api/runs/{run_id}/agents")
    assert resp.status_code == 200
    agents_list = resp.json()
    assert len(agents_list) == 5

    # 3. Get single agent execution
    exec_id = agents_list[0]["id"]
    resp = client.get(f"/api/agent-executions/{exec_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == exec_id

    # 4. Cancel agent workflow
    resp = client.post(f"/api/runs/{run_id}/agents/cancel")
    assert resp.status_code == 200
    assert resp.json()["run_status"] == "CANCELLED"
