import os
import shutil
import tempfile
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import Base, engine, SessionLocal
from backend.models.project import Project
from backend.models.run import EngineeringRun
from backend.models.agent_execution import AgentExecution
from backend.models.finding import Finding
from backend.models.orchestration import OrchestrationState
from backend.agents.models import AgentType, AgentStatus, AgentResult
from backend.agents.context import AgentContext
from backend.agents.prompts import build_builder_retry_prompt
from backend.codex.models import RunStatus, ExecutionResult
from backend.workspace.git import MockGitWorkspaceProvider
from backend.sandbox.docker import MockDockerProvider
from backend.orchestrator.models import (
    WorkflowState,
    OrchestratorDecision,
    DecisionResult,
    OrchestrationEvent,
)
from backend.orchestrator.state_machine import WorkflowStateMachine
from backend.orchestrator.policy import OrchestratorPolicy
from backend.orchestrator.feedback import IterationFeedbackCollector
from backend.orchestrator.manager import OrchestratorManager
from backend.orchestrator.exceptions import InvalidStateTransitionError

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
    from backend.main import _migrate_schema
    _migrate_schema()
    temp_dir = tempfile.mkdtemp(prefix="codex_p7_test_")
    yield temp_dir
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)


# =======================================================
# 1. WORKFLOW STATE MACHINE TESTS
# =======================================================

def test_state_machine_valid_transitions():
    """Verify standard happy-path progression through state machine."""
    s = WorkflowState.PENDING
    s = WorkflowStateMachine.transition(s, WorkflowState.ARCHITECTING)
    assert s == WorkflowState.ARCHITECTING

    s = WorkflowStateMachine.transition(s, WorkflowState.BUILDING)
    assert s == WorkflowState.BUILDING

    s = WorkflowStateMachine.transition(s, WorkflowState.TESTING)
    assert s == WorkflowState.TESTING

    s = WorkflowStateMachine.transition(s, WorkflowState.BREAKING)
    assert s == WorkflowState.BREAKING

    s = WorkflowStateMachine.transition(s, WorkflowState.SECURITY_SCANNING)
    assert s == WorkflowState.SECURITY_SCANNING

    s = WorkflowStateMachine.transition(s, WorkflowState.DECIDING)
    assert s == WorkflowState.DECIDING

    # Iteration loop transition
    s = WorkflowStateMachine.transition(s, WorkflowState.ITERATING)
    assert s == WorkflowState.ITERATING

    s = WorkflowStateMachine.transition(s, WorkflowState.BUILDING)
    assert s == WorkflowState.BUILDING

    # Skip to DECIDING then COMPLETED
    s = WorkflowStateMachine.transition(s, WorkflowState.TESTING)
    s = WorkflowStateMachine.transition(s, WorkflowState.DECIDING)
    s = WorkflowStateMachine.transition(s, WorkflowState.COMPLETED)
    assert s == WorkflowState.COMPLETED
    assert WorkflowStateMachine.is_terminal(s)


def test_state_machine_invalid_transitions_rejected():
    """Verify illegal transitions raise InvalidStateTransitionError."""
    # Cannot jump directly from PENDING to COMPLETED
    with pytest.raises(InvalidStateTransitionError):
        WorkflowStateMachine.transition(WorkflowState.PENDING, WorkflowState.COMPLETED)

    # Cannot jump directly from BUILDING to DECIDING
    with pytest.raises(InvalidStateTransitionError):
        WorkflowStateMachine.transition(WorkflowState.BUILDING, WorkflowState.DECIDING)

    # Terminal state cannot transition to anything
    with pytest.raises(InvalidStateTransitionError):
        WorkflowStateMachine.transition(WorkflowState.COMPLETED, WorkflowState.BUILDING)

    with pytest.raises(InvalidStateTransitionError):
        WorkflowStateMachine.transition(WorkflowState.FAILED, WorkflowState.PENDING)


def test_state_machine_pause_and_resume_transitions():
    """Verify transitions to and from PAUSED state."""
    # Any active running state can pause
    paused = WorkflowStateMachine.transition(WorkflowState.BUILDING, WorkflowState.PAUSED)
    assert paused == WorkflowState.PAUSED

    # Resume back to BUILDING
    resumed = WorkflowStateMachine.transition(paused, WorkflowState.BUILDING)
    assert resumed == WorkflowState.BUILDING

    # Can also cancel from PAUSED
    paused2 = WorkflowStateMachine.transition(WorkflowState.TESTING, WorkflowState.PAUSED)
    cancelled = WorkflowStateMachine.transition(paused2, WorkflowState.CANCELLED)
    assert cancelled == WorkflowState.CANCELLED


# =======================================================
# 2. ORCHESTRATOR DECISION POLICY TESTS
# =======================================================

def test_policy_builder_failure():
    """Verify policy halts immediately if Builder failed."""
    b_res = AgentResult(
        agent_type=AgentType.BUILDER,
        agent_name="Builder Agent",
        status=AgentStatus.FAILED,
        output="",
        error_message="SyntaxError in generated code"
    )
    res = OrchestratorPolicy.evaluate(
        iteration=1,
        max_iterations=3,
        builder_result=b_res
    )
    assert res.decision == OrchestratorDecision.STOP_FAILURE
    assert "Builder failed" in res.reason
    assert "SyntaxError" in res.reason


def test_policy_tester_failure_retries_builder():
    """Verify failing tests trigger RETRY_BUILDER when iteration < max."""
    b_res = AgentResult(AgentType.BUILDER, "Builder", AgentStatus.COMPLETED, "code done")
    t_res = AgentResult(
        AgentType.TESTER,
        "Tester",
        AgentStatus.FAILED,
        "FAILED (failures=2)",
        error_message="2 unit tests failed"
    )

    res = OrchestratorPolicy.evaluate(
        iteration=1,
        max_iterations=3,
        builder_result=b_res,
        tester_result=t_res
    )
    assert res.decision == OrchestratorDecision.RETRY_BUILDER
    assert res.test_failed is True
    assert "Tester reported failing cases" in res.reason


def test_policy_breaker_high_finding_retries_builder():
    """Verify HIGH Breaker finding triggers RETRY_BUILDER."""
    b_res = AgentResult(AgentType.BUILDER, "Builder", AgentStatus.COMPLETED, "code done")
    t_res = AgentResult(AgentType.TESTER, "Tester", AgentStatus.COMPLETED, "tests passed")
    breaker_findings = [
        {"severity": "HIGH", "title": "Crash on Null Byte", "description": "Unchecked null pointer"}
    ]

    res = OrchestratorPolicy.evaluate(
        iteration=1,
        max_iterations=3,
        builder_result=b_res,
        tester_result=t_res,
        breaker_findings=breaker_findings
    )
    assert res.decision == OrchestratorDecision.RETRY_BUILDER
    assert res.blocking_findings_count == 1
    assert "Breaker reported 1 HIGH/CRITICAL issue(s)" in res.reason


def test_policy_security_critical_finding_retries_builder():
    """Verify CRITICAL Security finding triggers RETRY_BUILDER."""
    b_res = AgentResult(AgentType.BUILDER, "Builder", AgentStatus.COMPLETED, "code done")
    t_res = AgentResult(AgentType.TESTER, "Tester", AgentStatus.COMPLETED, "tests passed")
    security_findings = [
        {"severity": "CRITICAL", "title": "SQL Injection", "description": "Raw string concatenation in query"}
    ]

    res = OrchestratorPolicy.evaluate(
        iteration=1,
        max_iterations=3,
        builder_result=b_res,
        tester_result=t_res,
        security_findings=security_findings
    )
    assert res.decision == OrchestratorDecision.RETRY_BUILDER
    assert res.blocking_findings_count == 1
    assert "Security reported 1 HIGH/CRITICAL vulnerability(ies)" in res.reason


def test_policy_info_and_low_findings_do_not_block_success():
    """Verify non-blocking findings (INFO, LOW) allow successful completion."""
    b_res = AgentResult(AgentType.BUILDER, "Builder", AgentStatus.COMPLETED, "code done")
    t_res = AgentResult(AgentType.TESTER, "Tester", AgentStatus.COMPLETED, "tests passed")
    findings = [
        {"severity": "INFO", "title": "Notice", "description": "Minor doc note"},
        {"severity": "LOW", "title": "Style", "description": "Line length"},
    ]

    res = OrchestratorPolicy.evaluate(
        iteration=1,
        max_iterations=3,
        builder_result=b_res,
        tester_result=t_res,
        breaker_findings=findings,
        security_findings=[]
    )
    assert res.decision == OrchestratorDecision.STOP_SUCCESS
    assert res.blocking_findings_count == 0
    assert "All tests passed" in res.reason


def test_policy_max_iterations_reached_halts_safely():
    """Verify that when iteration reaches max_iterations with issues, it halts with STOP_FAILURE."""
    b_res = AgentResult(AgentType.BUILDER, "Builder", AgentStatus.COMPLETED, "code done")
    t_res = AgentResult(AgentType.TESTER, "Tester", AgentStatus.COMPLETED, "tests passed")
    sec_findings = [
        {"severity": "HIGH", "title": "Insecure Secret", "description": "Hardcoded API key"}
    ]

    # iteration 3 of 3
    res = OrchestratorPolicy.evaluate(
        iteration=3,
        max_iterations=3,
        builder_result=b_res,
        tester_result=t_res,
        security_findings=sec_findings
    )
    assert res.decision == OrchestratorDecision.STOP_FAILURE
    assert "maximum iteration limit (3) was reached" in res.reason
    assert "unresolved issues" in res.reason


# =======================================================
# 3. BUILDER FEEDBACK & PROMPTS
# =======================================================

def test_builder_retry_prompt_contains_feedback():
    """Verify Builder retry prompt incorporates test failures, breaker, and security findings."""
    ctx = AgentContext(
        project_id=1,
        project_name="Test Project",
        repository_path="/repo",
        engineering_run_id=10,
        engineering_goal="Fix edge cases",
        iteration=2,
        previous_failure_reason="Tester reported 1 failing case; Security found 1 HIGH vulnerability",
        tester_feedback="test_edge_case failed: AssertionError: 5 != 0",
        breaker_findings=[
            {
                "severity": "HIGH",
                "title": "Division by Zero",
                "description": "divide(5, 0) raises unhandled ZeroDivisionError",
                "reproduction": "divide(5, 0)",
                "evidence": "ZeroDivisionError: division by zero"
            }
        ],
        security_findings=[
            {
                "severity": "HIGH",
                "title": "Hardcoded Password",
                "file_path": "auth.py",
                "line_number": 42,
                "remediation": "Use os.environ for credentials"
            }
        ]
    )

    prompt = build_builder_retry_prompt(ctx, "Initial Architect Plan")
    assert "Iteration 2 Retry" in prompt
    assert "FEEDBACK FROM PREVIOUS ITERATION" in prompt
    assert "AssertionError: 5 != 0" in prompt
    assert "[HIGH] Division by Zero" in prompt
    assert "[HIGH] Hardcoded Password" in prompt
    assert "`auth.py:42`" in prompt
    assert "DO NOT EXECUTE ANY GIT COMMANDS" in prompt


# =======================================================
# 4. ORCHESTRATION MANAGER AUTONOMOUS EXECUTION
# =======================================================

@patch("backend.workspace.manager.get_git_provider", return_value=MockGitWorkspaceProvider())
@patch("backend.sandbox.manager.get_docker_provider", return_value=MockDockerProvider())
@patch("backend.codex.runner.CodexRunner.execute")
def test_autonomous_orchestration_happy_path(mock_codex, mock_sb_prov, mock_ws_prov, setup_teardown):
    """
    Test a full successful 1-iteration autonomous run:
    Architect -> Builder -> Tester (pass) -> Breaker (clean) -> Security (clean) -> Complete.
    """
    temp_dir = setup_teardown
    db = SessionLocal()

    # Create project and run
    proj = Project(name="AutoTestProj", repository_path=temp_dir, status="ACTIVE")
    db.add(proj)
    db.commit()
    db.refresh(proj)

    run = EngineeringRun(project_id=proj.id, goal="Add user login helper", status="PENDING")
    db.add(run)
    db.commit()
    db.refresh(run)

    # Mock agent outputs
    mock_codex.side_effect = [
        make_exec_result(stdout="Architect: Created modular plan for login helper"),
        make_exec_result(stdout="Builder: Implemented login helper in auth.py"),
        make_exec_result(stdout="Tester: All 4 tests passed successfully.\nstatus: completed\nfailed: 0"),
        make_exec_result(stdout="Breaker: Edge cases explored, none found"),
        make_exec_result(stdout="Security: No vulnerabilities discovered"),
    ]

    # Run orchestrator synchronously in test via worker
    orch_state = OrchestratorManager.start_autonomous_run(run_id=run.id, max_iterations=3, db=db, spawn_worker=False)
    # Execute worker inline
    OrchestratorManager._orchestration_worker(run.id, db=db)

    db.refresh(run)
    db.refresh(orch_state)

    assert orch_state.state == WorkflowState.COMPLETED.value
    assert run.status == RunStatus.COMPLETED.value
    assert orch_state.iteration == 1
    assert orch_state.last_decision == OrchestratorDecision.STOP_SUCCESS.value
    assert "All tests passed" in orch_state.last_decision_reason

    # Verify AgentExecution records exist for iteration 1
    execs = db.query(AgentExecution).filter(AgentExecution.engineering_run_id == run.id).all()
    assert len(execs) == 5
    for e in execs:
        assert e.iteration == 1
        assert e.status == AgentStatus.COMPLETED.value

    # Verify events
    events = json.loads(orch_state.events_json)
    event_types = [e["event_type"] for e in events]
    assert "run.started" in event_types
    assert "agent.started" in event_types
    assert "agent.completed" in event_types
    assert "decision.made" in event_types
    assert "run.completed" in event_types

    db.close()


@patch("backend.workspace.manager.get_git_provider", return_value=MockGitWorkspaceProvider())
@patch("backend.sandbox.manager.get_docker_provider", return_value=MockDockerProvider())
@patch("backend.codex.runner.CodexRunner.execute")
def test_autonomous_orchestration_tester_failure_retries_builder(mock_codex, mock_sb_prov, mock_ws_prov, setup_teardown):
    """
    Test multi-iteration retry on Tester failure:
    Iteration 1: Architect -> Builder -> Tester (FAILS) -> Breaker -> Security -> Decision: RETRY_BUILDER.
    Iteration 2: Builder -> Tester (PASSES) -> Breaker -> Security -> Decision: STOP_SUCCESS.
    """
    temp_dir = setup_teardown
    db = SessionLocal()

    proj = Project(name="RetryProj", repository_path=temp_dir, status="ACTIVE")
    db.add(proj)
    db.commit()
    db.refresh(proj)

    run = EngineeringRun(project_id=proj.id, goal="Fix string parsing", status="PENDING")
    db.add(run)
    db.commit()
    db.refresh(run)

    # Sequence of CodexRunner outputs across both iterations:
    # Iteration 1:
    # 1. Architect
    # 2. Builder (iter 1)
    # 3. Tester (iter 1 - FAILS)
    # 4. Breaker (iter 1)
    # 5. Security (iter 1)
    # Iteration 2:
    # 6. Builder (iter 2 - retried with feedback)
    # 7. Tester (iter 2 - PASSES)
    # 8. Breaker (iter 2)
    # 9. Security (iter 2)
    mock_codex.side_effect = [
        make_exec_result(stdout="Architect: Architecture plan"),
        make_exec_result(stdout="Builder 1: Initial implementation"),
        make_exec_result(stdout="Tester 1: Status: failed\nfailed: 1\nAssertionError in test_parse"),
        make_exec_result(stdout="Breaker 1: Adversarial analysis"),
        make_exec_result(stdout="Security 1: Security audit clean"),
        # Iteration 2
        make_exec_result(stdout="Builder 2: Remediated parsing error based on tester feedback"),
        make_exec_result(stdout="Tester 2: Status: completed\nfailed: 0\nAll tests pass"),
        make_exec_result(stdout="Breaker 2: Adversarial analysis pass"),
        make_exec_result(stdout="Security 2: Security audit pass"),
    ]

    orch_state = OrchestratorManager.start_autonomous_run(run_id=run.id, max_iterations=3, db=db, spawn_worker=False)
    OrchestratorManager._orchestration_worker(run.id, db=db)

    db.refresh(run)
    db.refresh(orch_state)

    assert orch_state.state == WorkflowState.COMPLETED.value
    assert run.status == RunStatus.COMPLETED.value
    assert orch_state.iteration == 2
    assert orch_state.last_decision == OrchestratorDecision.STOP_SUCCESS.value

    # Verify AgentExecution records: Architect (1), Builder (2), Tester (2), Breaker (2), Security (2) = 9 total
    execs = db.query(AgentExecution).filter(AgentExecution.engineering_run_id == run.id).all()
    assert len(execs) == 9

    # Iteration 1 should have tester failed
    iter1_tester = [e for e in execs if e.agent_type == "TESTER" and e.iteration == 1][0]
    assert iter1_tester.status == AgentStatus.FAILED.value

    # Iteration 2 should have tester completed
    iter2_tester = [e for e in execs if e.agent_type == "TESTER" and e.iteration == 2][0]
    assert iter2_tester.status == AgentStatus.COMPLETED.value

    db.close()


@patch("backend.workspace.manager.get_git_provider", return_value=MockGitWorkspaceProvider())
@patch("backend.sandbox.manager.get_docker_provider", return_value=MockDockerProvider())
@patch("backend.codex.runner.CodexRunner.execute")
def test_autonomous_orchestration_breaker_high_finding_retries_builder(mock_codex, mock_sb_prov, mock_ws_prov, setup_teardown):
    """
    Test retry triggered by Breaker discovering a HIGH finding in Iteration 1.
    Verify findings from Iteration 1 are strictly preserved in DB!
    """
    temp_dir = setup_teardown
    db = SessionLocal()

    proj = Project(name="BreakerRetryProj", repository_path=temp_dir, status="ACTIVE")
    db.add(proj)
    db.commit()
    db.refresh(proj)

    run = EngineeringRun(project_id=proj.id, goal="Safe parser", status="PENDING")
    db.add(run)
    db.commit()
    db.refresh(run)

    # Iteration 1 breaker output with HIGH finding JSON block
    breaker_iter1_json = """
    Explored edge cases.
    ```json
    [
      {
        "type": "BREAKER",
        "severity": "HIGH",
        "category": "INPUT_VALIDATION",
        "title": "Buffer Overflow in Input",
        "description": "Large string causes overflow",
        "reproduction": "parse('A' * 10000)"
      }
    ]
    ```
    """

    mock_codex.side_effect = [
        make_exec_result(stdout="Architect plan"),
        make_exec_result(stdout="Builder 1 implementation"),
        make_exec_result(stdout="Tester 1: Status: completed\nfailed: 0"),
        make_exec_result(stdout=breaker_iter1_json),
        make_exec_result(stdout="Security 1 clean"),
        # Iteration 2:
        make_exec_result(stdout="Builder 2: Fixed input validation buffer check"),
        make_exec_result(stdout="Tester 2: All tests pass"),
        make_exec_result(stdout="Breaker 2: All edge cases handled"),
        make_exec_result(stdout="Security 2 clean"),
    ]

    orch_state = OrchestratorManager.start_autonomous_run(run_id=run.id, max_iterations=3, db=db, spawn_worker=False)
    OrchestratorManager._orchestration_worker(run.id, db=db)

    db.refresh(run)
    db.refresh(orch_state)

    assert orch_state.state == WorkflowState.COMPLETED.value
    assert orch_state.iteration == 2

    # Verify the finding from Iteration 1 is preserved and has iteration=1
    findings = db.query(Finding).filter(Finding.engineering_run_id == run.id).all()
    assert len(findings) >= 1
    assert any(f.iteration == 1 and f.severity == "HIGH" and "Buffer Overflow" in f.title for f in findings)

    db.close()


@patch("backend.workspace.manager.get_git_provider", return_value=MockGitWorkspaceProvider())
@patch("backend.sandbox.manager.get_docker_provider", return_value=MockDockerProvider())
@patch("backend.codex.runner.CodexRunner.execute")
def test_autonomous_orchestration_max_iteration_limit(mock_codex, mock_sb_prov, mock_ws_prov, setup_teardown):
    """
    Verify loop protection: when max_iterations is reached with unresolved issues,
    execution halts safely with FAILED and does not loop infinitely.
    """
    temp_dir = setup_teardown
    db = SessionLocal()

    proj = Project(name="LimitProj", repository_path=temp_dir, status="ACTIVE")
    db.add(proj)
    db.commit()
    db.refresh(proj)

    run = EngineeringRun(project_id=proj.id, goal="Fix stubborn bug", status="PENDING")
    db.add(run)
    db.commit()
    db.refresh(run)

    # Max iterations set to 2; Tester fails on both
    mock_codex.side_effect = [
        # Iteration 1
        make_exec_result(stdout="Architect"),
        make_exec_result(stdout="Builder 1"),
        make_exec_result(stdout="Tester 1: Status: failed\nfailed: 2"),
        make_exec_result(stdout="Breaker 1"),
        make_exec_result(stdout="Security 1"),
        # Iteration 2
        make_exec_result(stdout="Builder 2"),
        make_exec_result(stdout="Tester 2: Status: failed\nfailed: 2"),
        make_exec_result(stdout="Breaker 2"),
        make_exec_result(stdout="Security 2"),
    ]

    orch_state = OrchestratorManager.start_autonomous_run(run_id=run.id, max_iterations=2, db=db, spawn_worker=False)
    OrchestratorManager._orchestration_worker(run.id, db=db)

    db.refresh(run)
    db.refresh(orch_state)

    assert orch_state.state == WorkflowState.FAILED.value
    assert run.status == RunStatus.FAILED.value
    assert orch_state.iteration == 2
    assert orch_state.last_decision == OrchestratorDecision.STOP_FAILURE.value
    assert "maximum iteration limit (2) was reached" in orch_state.last_decision_reason

    db.close()


@patch("backend.workspace.manager.get_git_provider", return_value=MockGitWorkspaceProvider())
@patch("backend.sandbox.manager.get_docker_provider", return_value=MockDockerProvider())
@patch("backend.codex.runner.CodexRunner.execute")
def test_autonomous_orchestration_cancellation(mock_codex, mock_sb_prov, mock_ws_prov, setup_teardown):
    """
    Verify user cancellation marks the run CANCELLED safely.
    """
    temp_dir = setup_teardown
    db = SessionLocal()

    proj = Project(name="CancelProj", repository_path=temp_dir, status="ACTIVE")
    db.add(proj)
    db.commit()
    db.refresh(proj)

    run = EngineeringRun(project_id=proj.id, goal="Cancel test", status="PENDING")
    db.add(run)
    db.commit()
    db.refresh(run)

    orch_state = OrchestratorManager.start_autonomous_run(run_id=run.id, max_iterations=3, db=db, spawn_worker=False)
    # Cancel before worker runs
    cancelled_state = OrchestratorManager.cancel_run(run_id=run.id, db=db)

    assert cancelled_state.state == WorkflowState.CANCELLED.value
    assert cancelled_state.cancel_requested is True

    db.refresh(run)
    assert run.status == RunStatus.CANCELLED.value

    db.close()


@patch("backend.workspace.manager.get_git_provider", return_value=MockGitWorkspaceProvider())
@patch("backend.sandbox.manager.get_docker_provider", return_value=MockDockerProvider())
@patch("backend.codex.runner.CodexRunner.execute")
def test_autonomous_orchestration_pause_and_resume(mock_codex, mock_sb_prov, mock_ws_prov, setup_teardown):
    """
    Verify boundary pause requests and resume capabilities.
    """
    temp_dir = setup_teardown
    db = SessionLocal()

    proj = Project(name="PauseResumeProj", repository_path=temp_dir, status="ACTIVE")
    db.add(proj)
    db.commit()
    db.refresh(proj)

    run = EngineeringRun(project_id=proj.id, goal="Pause resume test", status="PENDING")
    db.add(run)
    db.commit()
    db.refresh(run)

    orch_state = OrchestratorManager.start_autonomous_run(run_id=run.id, max_iterations=3, db=db, spawn_worker=False)
    
    # Request pause
    paused_state = OrchestratorManager.pause_run(run_id=run.id, db=db)
    assert paused_state.pause_requested is True

    # Manually transition state to PAUSED to simulate boundary pause reached
    paused_state.state = WorkflowState.PAUSED.value
    db.commit()

    # Resume run
    resumed_state = OrchestratorManager.resume_run(run_id=run.id, db=db, spawn_worker=False)
    assert resumed_state.pause_requested is False

    db.close()


# =======================================================
# 5. REST API ENDPOINTS
# =======================================================

def test_orchestrator_rest_api_flow(setup_teardown):
    """
    Verify REST API endpoints:
    POST /runs/{id}/start-autonomous
    GET /runs/{id}/orchestration
    POST /runs/{id}/pause
    POST /runs/{id}/resume
    POST /runs/{id}/orchestration/cancel
    """
    temp_dir = setup_teardown
    db = SessionLocal()

    proj = Project(name="ApiTestProj", repository_path=temp_dir, status="ACTIVE")
    db.add(proj)
    db.commit()
    db.refresh(proj)

    run = EngineeringRun(project_id=proj.id, goal="Test REST API", status="PENDING")
    db.add(run)
    db.commit()
    db.refresh(run)
    db.close()

    with patch("backend.orchestrator.manager.threading.Thread"):
        # 1. Start autonomous run
        start_resp = client.post(
            f"/api/runs/{run.id}/start-autonomous",
            json={"max_iterations": 4}
        )
        assert start_resp.status_code == 200
        data = start_resp.json()
        assert data["engineering_run_id"] == run.id
        assert data["max_iterations"] == 4
        assert data["state"] == "PENDING"

        # 2. Get status
        get_resp = client.get(f"/api/runs/{run.id}/orchestration")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["engineering_run_id"] == run.id
        assert len(get_data["events"]) >= 1

        # 3. Pause run
        pause_resp = client.post(f"/api/runs/{run.id}/pause")
        assert pause_resp.status_code == 200
        assert pause_resp.json()["pause_requested"] is True

        # 4. Cancel run
        cancel_resp = client.post(f"/api/runs/{run.id}/orchestration/cancel")
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["state"] == "CANCELLED"


def test_get_orchestration_valid_run_without_orchestration_state(setup_teardown):
    """
    Regression Test:
    Verify GET /api/runs/{id}/orchestration succeeds for a valid run that does NOT
    have an explicit OrchestrationState record in the DB (e.g. Run 381 pattern).
    Ensures:
    1. Returns 200 OK
    2. Does NOT create duplicate records in DB
    3. Does NOT modify the run state
    4. Accurately reflects run's stored status and iteration info
    """
    temp_dir = setup_teardown
    db = SessionLocal()

    proj = Project(name="ValidRunProj", repository_path=temp_dir, status="ACTIVE")
    db.add(proj)
    db.commit()
    db.refresh(proj)

    run = EngineeringRun(
        project_id=proj.id,
        goal="Test direct run orchestration compatibility",
        status="COMPLETED"
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Confirm no orchestration record exists beforehand
    orch_count_before = db.query(OrchestrationState).filter(
        OrchestrationState.engineering_run_id == run.id
    ).count()
    assert orch_count_before == 0
    db.close()

    # GET /api/runs/{run_id}/orchestration
    resp = client.get(f"/api/runs/{run.id}/orchestration")
    assert resp.status_code == 200
    data = resp.json()

    # Verify fields
    assert data["id"] == run.id
    assert data["engineering_run_id"] == run.id
    assert data["state"] == "COMPLETED"
    assert data["current_agent"] is None
    assert data["iteration"] == 1
    assert data["max_iterations"] == 1
    assert data["last_decision"] is None
    assert data["last_decision_reason"] is None
    assert data["pause_requested"] is False
    assert data["cancel_requested"] is False
    assert data["failure_reason"] is None
    assert data["events"] == []
    assert data["created_at"] is not None
    assert data["updated_at"] is not None

    # Verify no DB records were created as a side effect
    db2 = SessionLocal()
    orch_count_after = db2.query(OrchestrationState).filter(
        OrchestrationState.engineering_run_id == run.id
    ).count()
    assert orch_count_after == 0

    # Verify run status was not mutated
    fresh_run = db2.query(EngineeringRun).filter(EngineeringRun.id == run.id).first()
    assert fresh_run.status == "COMPLETED"
    db2.close()


def test_get_orchestration_nonexistent_run_404():
    """
    Regression Test:
    Verify GET /api/runs/{id}/orchestration returns 404 ONLY when the requested
    run genuinely does not exist.
    """
    resp = client.get("/api/runs/999999/orchestration")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_get_orchestration_frontend_schema_contract(setup_teardown):
    """
    Regression Test:
    Verify the response contains every field and correct data types expected by the
    frontend OrchestrationResponse interface in frontend/src/api/types.ts.
    """
    temp_dir = setup_teardown
    db = SessionLocal()

    proj = Project(name="ContractProj", repository_path=temp_dir, status="ACTIVE")
    db.add(proj)
    db.commit()
    db.refresh(proj)

    run = EngineeringRun(
        project_id=proj.id,
        goal="Verify frontend TypeScript contract",
        status="RUNNING"
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    db.close()

    resp = client.get(f"/api/runs/{run.id}/orchestration")
    assert resp.status_code == 200
    data = resp.json()

    # Exact field contract expected by frontend OrchestrationResponse
    expected_fields = {
        "id": int,
        "engineering_run_id": int,
        "state": str,
        "iteration": int,
        "max_iterations": int,
        "pause_requested": bool,
        "cancel_requested": bool,
        "events": list,
        "created_at": str,
        "updated_at": str,
    }
    for field_name, expected_type in expected_fields.items():
        assert field_name in data, f"Missing expected field '{field_name}'"
        assert isinstance(data[field_name], expected_type), (
            f"Field '{field_name}' type mismatch: expected {expected_type}, got {type(data[field_name])}"
        )

    # Optional fields present in schema
    assert "current_agent" in data
    assert "last_decision" in data
    assert "last_decision_reason" in data
    assert "failure_reason" in data


def test_orchestration_and_control_room_endpoints_coexist(setup_teardown):
    """
    Regression Test:
    Verify that both GET /api/runs/{run_id}/orchestration and
    GET /api/runs/{run_id}/control-room function correctly side-by-side
    without interference.
    """
    temp_dir = setup_teardown
    db = SessionLocal()

    proj = Project(name="CoexistProj", repository_path=temp_dir, status="ACTIVE")
    db.add(proj)
    db.commit()
    db.refresh(proj)

    run = EngineeringRun(
        project_id=proj.id,
        goal="Verify endpoint coexistence",
        status="RUNNING"
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    db.close()

    # 1. Orchestration endpoint works
    orch_resp = client.get(f"/api/runs/{run.id}/orchestration")
    assert orch_resp.status_code == 200
    orch_data = orch_resp.json()
    assert orch_data["engineering_run_id"] == run.id

    # 2. Control Room endpoint still works
    cr_resp = client.get(f"/api/runs/{run.id}/control-room")
    assert cr_resp.status_code == 200
    cr_data = cr_resp.json()
    assert cr_data["run"]["id"] == run.id
    assert cr_data["run"]["status"] == "RUNNING"


def test_active_run_does_not_falsely_complete_on_missing_orchestration(setup_teardown):
    """
    Regression Test:
    Verify that an active run (e.g. status RUNNING) is not falsely marked as COMPLETED
    when querying orchestration state.
    """
    temp_dir = setup_teardown
    db = SessionLocal()

    proj = Project(name="ActiveRunProj", repository_path=temp_dir, status="ACTIVE")
    db.add(proj)
    db.commit()
    db.refresh(proj)

    run = EngineeringRun(
        project_id=proj.id,
        goal="Active run test",
        status="RUNNING"
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    db.close()

    # Query orchestration
    orch_resp = client.get(f"/api/runs/{run.id}/orchestration")
    assert orch_resp.status_code == 200
    orch_data = orch_resp.json()
    # State should reflect active/building execution, NOT COMPLETED
    assert orch_data["state"] != "COMPLETED"
    assert orch_data["state"] in ("BUILDING", "RUNNING")

    # Verify run status in backend remains RUNNING
    run_resp = client.get(f"/api/runs/{run.id}")
    assert run_resp.status_code == 200
    assert run_resp.json()["status"] == "RUNNING"

