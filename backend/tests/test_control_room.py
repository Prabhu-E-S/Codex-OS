import os
import shutil
import tempfile
import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import Base, engine, SessionLocal
from backend.models.project import Project
from backend.models.run import EngineeringRun
from backend.models.agent_execution import AgentExecution
from backend.models.finding import Finding
from backend.models.orchestration import OrchestrationState
from backend.models.evaluation import Evaluation, EvaluationDimension, EvaluationEvidence
from backend.models.workspace import Workspace
from backend.models.sandbox import Sandbox

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_teardown():
    Base.metadata.create_all(bind=engine)
    from backend.main import _migrate_schema
    _migrate_schema()
    temp_dir = tempfile.mkdtemp(prefix="codex_p9_test_")
    yield temp_dir
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_control_room_404_missing_run():
    """Verify Control Room endpoint returns 404 for non-existent run."""
    response = client.get("/api/runs/999999/control-room")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_control_room_minimal_run_no_data():
    """Verify Control Room endpoint handles a fresh run with no agents, findings, or evaluations without errors."""
    db = SessionLocal()
    try:
        project = Project(
            name="Minimal Project",
            repository_path="C:/dummy/repo",
            description="Test Project"
        )
        db.add(project)
        db.commit()

        run = EngineeringRun(
            project_id=project.id,
            goal="Test minimal run",
            status="PENDING",
            stdout="",
            stderr="",
        )
        db.add(run)
        db.commit()
        run_id = run.id
    finally:
        db.close()

    response = client.get(f"/api/runs/{run_id}/control-room")
    assert response.status_code == 200
    data = response.json()

    assert data["run"]["id"] == run_id
    assert data["run"]["project_name"] == "Minimal Project"
    assert data["run"]["status"] == "PENDING"
    assert data["run"]["mode"] == "MANUAL"
    assert data["orchestration"] is None
    assert data["agents"] == []
    assert data["iterations"] == [
        {
            "iteration_number": 1,
            "status": "RUNNING",
            "agents": [],
            "decision": None,
            "decision_reason": None,
            "findings_count": 0,
        }
    ]
    assert data["findings"] == []
    assert data["findings_summary"]["total"] == 0
    assert data["evaluation"] is None
    assert data["logs"]["stdout"] == ""
    assert data["logs"]["stderr"] == ""


def test_control_room_full_snapshot_and_iteration_grouping():
    """Verify complete Control Room snapshot with multi-iteration agents, decisions, workspaces, sandboxes, and findings."""
    db = SessionLocal()
    try:
        project = Project(
            name="Control Room Full Project",
            repository_path="C:/dummy/repo",
            description="Full Test"
        )
        db.add(project)
        db.commit()

        ws1 = Workspace(
            project_id=project.id,
            name="ws-builder-iter1",
            path="C:/Codex/workspaces/ws-builder-iter1",
            branch_name="codex/workspace/ws-builder-iter1",
            status="READY",
        )
        db.add(ws1)
        db.commit()

        sb1 = Sandbox(
            workspace_id=ws1.id,
            image="python:3.12-slim",
            container_id="abcdef1234567890",
            status="RUNNING",
            cpu_limit=1.5,
            memory_limit="512m",
            timeout_seconds=90,
        )
        db.add(sb1)
        db.commit()

        now = datetime.now(timezone.utc)
        run = EngineeringRun(
            project_id=project.id,
            goal="Implement and verify secure auth module",
            status="RUNNING",
            workspace_id=ws1.id,
            sandbox_id=sb1.id,
            started_at=now,
            stdout="Starting test build...\nBuilding components...\nTests running.",
            stderr="",
        )
        db.add(run)
        db.commit()

        # Orchestration state
        events = [
            {"timestamp": "2026-09-19T12:00:01Z", "event_type": "ORCHESTRATION_START", "iteration": 1},
            {"timestamp": "2026-09-19T12:00:10Z", "event_type": "DECISION", "iteration": 1, "decision": "RETRY_BUILDER", "reason": "Tester reported 1 failure"},
            {"timestamp": "2026-09-19T12:00:15Z", "event_type": "AGENT_START", "iteration": 2, "agent": "BUILDER"},
        ]
        orch = OrchestrationState(
            engineering_run_id=run.id,
            state="BUILDING",
            current_agent="BUILDER",
            iteration=2,
            max_iterations=3,
            last_decision="RETRY_BUILDER",
            last_decision_reason="Tester reported 1 failure",
            events_json=json.dumps(events),
        )
        db.add(orch)

        # Agent Executions
        ae1 = AgentExecution(
            engineering_run_id=run.id,
            agent_type="BUILDER",
            agent_name="Builder Agent",
            status="COMPLETED",
            iteration=1,
            workspace_id=ws1.id,
            sandbox_id=sb1.id,
            output="Created initial auth handlers.",
            started_at=now,
            completed_at=now,
        )
        ae2 = AgentExecution(
            engineering_run_id=run.id,
            agent_type="TESTER",
            agent_name="Tester Agent",
            status="FAILED",
            iteration=1,
            workspace_id=ws1.id,
            sandbox_id=sb1.id,
            output="AssertionError: Token validation failed.",
            started_at=now,
            completed_at=now,
        )
        ae3 = AgentExecution(
            engineering_run_id=run.id,
            agent_type="BUILDER",
            agent_name="Builder Agent",
            status="RUNNING",
            iteration=2,
            workspace_id=ws1.id,
            sandbox_id=sb1.id,
            output="Applying fix for token validation.",
            started_at=now,
        )
        db.add_all([ae1, ae2, ae3])
        db.commit()

        # Finding
        finding = Finding(
            engineering_run_id=run.id,
            agent_execution_id=ae2.id,
            type="BREAKER",
            severity="HIGH",
            category="INPUT_VALIDATION",
            title="Token expired boundary test failed",
            description="Expired tokens return 500 instead of 401",
            file_path="src/auth.py",
            line_number=42,
            evidence="KeyError: 'exp' at line 42",
            status="OPEN",
            iteration=1,
        )
        db.add(finding)
        db.commit()

        run_id = run.id
    finally:
        db.close()

    response = client.get(f"/api/runs/{run_id}/control-room")
    assert response.status_code == 200
    data = response.json()

    # Validate run
    assert data["run"]["id"] == run_id
    assert data["run"]["mode"] == "AUTONOMOUS"
    assert data["run"]["iteration"] == 2
    assert data["run"]["max_iterations"] == 3

    # Validate orchestration
    assert data["orchestration"]["state"] == "BUILDING"
    assert data["orchestration"]["current_agent"] == "BUILDER"
    assert data["orchestration"]["last_decision"] == "RETRY_BUILDER"
    assert data["orchestration"]["is_active"] is True

    # Validate agents
    assert len(data["agents"]) == 3
    assert data["agents"][0]["agent_type"] == "BUILDER"
    assert data["agents"][0]["iteration"] == 1
    assert data["agents"][1]["agent_type"] == "TESTER"
    assert data["agents"][2]["agent_type"] == "BUILDER"
    assert data["agents"][2]["status"] == "RUNNING"

    # Validate iterations
    assert len(data["iterations"]) == 2
    assert data["iterations"][0]["iteration_number"] == 1
    assert data["iterations"][0]["decision"] == "RETRY_BUILDER"
    assert len(data["iterations"][0]["agents"]) == 2
    assert data["iterations"][1]["iteration_number"] == 2
    assert data["iterations"][1]["status"] == "RUNNING"

    # Validate sanitized workspace path
    assert len(data["workspaces"]) == 1
    assert "workspaces/ws-builder-iter1" in data["workspaces"][0]["relative_path"]
    assert "C:" not in data["workspaces"][0]["relative_path"]

    # Validate sanitized sandbox
    assert len(data["sandboxes"]) == 1
    assert data["sandboxes"][0]["container_id_preview"] == "abcdef123456"
    assert data["sandboxes"][0]["status"] == "RUNNING"

    # Validate findings and summary
    assert len(data["findings"]) == 1
    assert data["findings"][0]["severity"] == "HIGH"
    assert data["findings_summary"]["total"] == 1
    assert data["findings_summary"]["by_severity"]["HIGH"] == 1
    assert data["findings_summary"]["by_type"]["BREAKER"] == 1

    # Validate events
    assert len(data["recent_events"]) == 3
    assert data["recent_events"][0]["event_type"] == "ORCHESTRATION_START"


def test_control_room_secret_redaction():
    """Verify secrets and credentials in logs and findings are redacted with <REDACTED>."""
    db = SessionLocal()
    try:
        project = Project(
            name="Security Test Project",
            repository_path="C:/dummy/repo",
            description="Security Test"
        )
        db.add(project)
        db.commit()

        run = EngineeringRun(
            project_id=project.id,
            goal="Test secret masking",
            status="COMPLETED",
            stdout="Deploying with api_key='sk-prod-secret-99887766' and token: ghp_abcdef1234567890",
            stderr="AWS Auth failed for AKIAIOSFODNN7EXAMPLE: -----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0\n-----END RSA PRIVATE KEY-----",
        )
        db.add(run)
        db.commit()

        finding = Finding(
            engineering_run_id=run.id,
            type="SECURITY",
            severity="CRITICAL",
            category="SECRET",
            title="Hardcoded API Key Discovered",
            description="Found OpenAI key in config",
            evidence="Config file has OPENAI_KEY=sk-testsecrettoken123456789",
            status="OPEN",
            iteration=1,
        )
        db.add(finding)
        db.commit()
        run_id = run.id
    finally:
        db.close()

    response = client.get(f"/api/runs/{run_id}/control-room")
    assert response.status_code == 200
    data = response.json()

    stdout = data["logs"]["stdout"]
    stderr = data["logs"]["stderr"]
    evidence = data["findings"][0]["evidence"]

    # Assert no secrets are exposed
    assert "sk-prod-secret-99887766" not in stdout
    assert "ghp_abcdef1234567890" not in stdout
    assert "<REDACTED>" in stdout

    assert "AKIAIOSFODNN7EXAMPLE" not in stderr
    assert "MIIEowIBAAKCAQEA0" not in stderr
    assert "<REDACTED>" in stderr

    assert "sk-testsecrettoken123456789" not in evidence
    assert "<REDACTED>" in evidence


def test_control_room_evaluation_present():
    """Verify Control Room correctly includes Phase 8 evaluation data and scores."""
    db = SessionLocal()
    try:
        project = Project(
            name="Eval Test Project",
            repository_path="C:/dummy/repo",
            description="Eval Test"
        )
        db.add(project)
        db.commit()

        run = EngineeringRun(
            project_id=project.id,
            goal="Evaluation integration test",
            status="COMPLETED",
            stdout="Tests passed.",
        )
        db.add(run)
        db.commit()

        evaluation = Evaluation(
            engineering_run_id=run.id,
            status="COMPLETED",
            overall_score=84.5,
            status_label="STRONG",
            score_version="v1",
            formula="Overall: 84.5 / 100",
            summary="All tests passed with robust security posture.",
            strengths_json=json.dumps(["High test coverage", "Zero critical findings"]),
            weaknesses_json=json.dumps(["Minor linter warnings"]),
            limitations_json=json.dumps([]),
        )
        db.add(evaluation)
        db.commit()

        dim1 = EvaluationDimension(
            evaluation_id=evaluation.id,
            dimension="CORRECTNESS",
            score=95.0,
            status="STRONG",
            weight=0.30,
            weighted_score=28.5,
            explanation="100% pass rate",
        )
        dim2 = EvaluationDimension(
            evaluation_id=evaluation.id,
            dimension="SECURITY",
            score=90.0,
            status="STRONG",
            weight=0.20,
            weighted_score=18.0,
            explanation="No vulnerabilities found",
        )
        db.add_all([dim1, dim2])
        db.commit()

        run_id = run.id
    finally:
        db.close()

    response = client.get(f"/api/runs/{run_id}/control-room")
    assert response.status_code == 200
    data = response.json()

    assert data["evaluation"] is not None
    assert data["evaluation"]["overall_score"] == 84.5
    assert data["evaluation"]["status_label"] == "STRONG"
    assert len(data["evaluation"]["strengths"]) == 2
    assert len(data["evaluation"]["dimensions"]) == 2
    assert data["evaluation"]["dimensions"][0]["dimension"] == "CORRECTNESS"
    assert data["evaluation"]["dimensions"][0]["score"] == 95.0


def test_control_room_read_only_guarantee():
    """Verify Control Room endpoint never modifies existing run, agent, or database state."""
    db = SessionLocal()
    try:
        project = Project(name="RO Project", repository_path="C:/dummy/repo")
        db.add(project)
        db.commit()

        run = EngineeringRun(
            project_id=project.id,
            goal="RO Test",
            status="RUNNING",
            stdout="initial log",
        )
        db.add(run)
        db.commit()
        run_id = run.id
        initial_updated_at = run.updated_at
    finally:
        db.close()

    # Call endpoint multiple times
    for _ in range(3):
        res = client.get(f"/api/runs/{run_id}/control-room")
        assert res.status_code == 200

    # Verify run record in DB is completely untouched
    db = SessionLocal()
    try:
        r = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
        assert r.status == "RUNNING"
        assert r.stdout == "initial log"
        assert r.updated_at == initial_updated_at
    finally:
        db.close()
