import os
import shutil
import tempfile
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import Base, engine, SessionLocal
from backend.models.project import Project
from backend.models.run import EngineeringRun
from backend.models.workspace import Workspace
from backend.models.sandbox import Sandbox
from backend.models.agent_execution import AgentExecution
from backend.models.finding import Finding
from backend.agents.models import AgentType, AgentStatus, AgentResult
from backend.agents.context import AgentContext
from backend.agents.breaker import BreakerAgent
from backend.agents.security import SecurityAgent
from backend.agents.manager import AgentManager
from backend.codex.models import RunStatus, ExecutionResult
from backend.workspace.git import MockGitWorkspaceProvider
from backend.sandbox.docker import MockDockerProvider
from backend.security.scanner import SecurityScannerManager
from backend.security.providers import (
    PatternSecretScannerProvider,
    BanditScannerProvider,
    PipAuditScannerProvider,
    NpmAuditScannerProvider,
)
from backend.security.models import ScannerFinding, ScannerReport, AggregatedScanReport

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
    temp_dir = tempfile.mkdtemp(prefix="codex_p6_test_")
    yield temp_dir
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)


# ==========================================
# 1. BREAKER AGENT TESTS
# ==========================================

def test_breaker_agent_execution_and_finding_extraction(setup_teardown):
    """Verify BreakerAgent designs adversarial tests, executes via Codex, and extracts findings."""
    temp_dir = setup_teardown
    agent = BreakerAgent()

    arch_res = AgentResult(AgentType.ARCHITECT, "Architect", AgentStatus.COMPLETED, "Plan...")
    build_res = AgentResult(AgentType.BUILDER, "Builder", AgentStatus.COMPLETED, "Implemented POST /parse endpoint in parser.py")
    test_res = AgentResult(AgentType.TESTER, "Tester", AgentStatus.COMPLETED, "Tests Run: 5\nPassed: 5\nFailed: 0\nStatus: PASSED")

    context = AgentContext(
        project_id=1,
        project_name="DataParserApp",
        repository_path=temp_dir,
        engineering_run_id=101,
        engineering_goal="Implement robust data parser",
        previous_results={
            AgentType.ARCHITECT: arch_res,
            AgentType.BUILDER: build_res,
            AgentType.TESTER: test_res
        }
    )

    breaker_stdout = (
        "### Adversarial Test Summary\n"
        "Tests Generated: 4\n"
        "Tests Executed: 4\n"
        "Tests Passed: 2\n"
        "Tests Failed: 2\n\n"
        "### Weakness Analysis\n"
        "Application unhandled IndexError when empty array passed to parse().\n\n"
        "```json\n"
        "[\n"
        "  {\n"
        "    \"title\": \"Application crashes with IndexError on empty input array\",\n"
        "    \"severity\": \"HIGH\",\n"
        "    \"category\": \"INPUT_VALIDATION\",\n"
        "    \"file_path\": \"src/parser.py\",\n"
        "    \"line_number\": 42,\n"
        "    \"description\": \"Passing empty array [] causes index out of range during element access.\",\n"
        "    \"evidence\": \"IndexError: list index out of range at parser.py:42\",\n"
        "    \"reproduction\": \"parser.parse([])\",\n"
        "    \"remediation\": \"Add length validation before accessing first element.\"\n"
        "  },\n"
        "  {\n"
        "    \"title\": \"Null pointer exception on NoneType payload\",\n"
        "    \"severity\": \"MEDIUM\",\n"
        "    \"category\": \"EDGE_CASE\",\n"
        "    \"file_path\": \"src/parser.py\",\n"
        "    \"line_number\": 15,\n"
        "    \"description\": \"Passing None as argument raises AttributeError.\",\n"
        "    \"evidence\": \"AttributeError: 'NoneType' object has no attribute 'strip'\",\n"
        "    \"reproduction\": \"parser.parse(None)\",\n"
        "    \"remediation\": \"Check if input is None and raise ValueError or return default.\"\n"
        "  }\n"
        "]\n"
        "```\n"
    )

    mock_exec = make_exec_result(RunStatus.COMPLETED, 0, breaker_stdout, "")

    with patch("backend.codex.runner.CodexRunner.execute", return_value=mock_exec):
        res = agent.run(context)
        assert res.status == AgentStatus.COMPLETED
        assert res.metadata is not None
        findings = res.metadata.get("findings", [])
        assert len(findings) == 2
        assert findings[0]["severity"] == "HIGH"
        assert findings[0]["category"] == "INPUT_VALIDATION"
        assert "IndexError" in findings[0]["title"]
        assert findings[0]["file_path"] == "src/parser.py"
        assert findings[0]["line_number"] == 42
        assert findings[1]["severity"] == "MEDIUM"

        test_counts = res.metadata.get("test_counts", {})
        assert test_counts["generated"] == 4
        assert test_counts["failed"] == 2


def test_breaker_agent_fails_when_builder_missing(setup_teardown):
    """Verify BreakerAgent halts cleanly if Builder did not complete."""
    temp_dir = setup_teardown
    agent = BreakerAgent()
    context = AgentContext(
        project_id=1,
        project_name="DataParserApp",
        repository_path=temp_dir,
        engineering_run_id=102,
        engineering_goal="Goal...",
        previous_results={}  # No Builder result
    )

    res = agent.run(context)
    assert res.status == AgentStatus.FAILED
    assert "Builder implementation is missing" in res.error_message


# ==========================================
# 2. SECURITY AGENT & SCANNER TESTS
# ==========================================

def test_pattern_secret_scanner_detection(setup_teardown):
    """
    Test the built-in PatternSecretScannerProvider against fixture files containing
    fake test secrets and unsafe patterns (SQL injection, subprocess shell=True, path traversal).
    """
    temp_dir = setup_teardown

    # Create test fixture files
    fixture_code = (
        "# Fake credentials for testing only\n"
        "FAKE_AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'\n"
        "api_key = 'fake_test_api_key_for_testing_12345'\n"
        "password = 'super_secret_test_password_123'\n"
        "\n"
        "# Unsafe patterns\n"
        "def unsafe_exec(cmd):\n"
        "    import subprocess\n"
        "    subprocess.call(cmd, shell=True)\n"
        "\n"
        "def query_user(user_id):\n"
        "    cursor.execute(f\"SELECT * FROM users WHERE id = {user_id}\")\n"
        "\n"
        "def read_file(name):\n"
        "    open(f'/tmp/{name}', 'r')\n"
    )

    fixture_file = os.path.join(temp_dir, "test_vulnerable.py")
    with open(fixture_file, "w", encoding="utf-8") as f:
        f.write(fixture_code)

    scanner = PatternSecretScannerProvider()
    avail, _ = scanner.is_available()
    assert avail is True

    report = scanner.scan(temp_dir)
    assert report.ran is True
    assert len(report.findings) >= 5

    categories = [f.category for f in report.findings]
    assert "SECRET" in categories
    assert "INJECTION" in categories
    assert "FILESYSTEM" in categories

    severities = [f.severity for f in report.findings]
    assert "CRITICAL" in severities
    assert "HIGH" in severities


def test_security_scanner_manager_handles_unavailable_tools_honestly(setup_teardown):
    """
    Verify that SecurityScannerManager discovers available tools and records
    unavailable tools honestly without crashing, pretending they ran, or fabricating vulnerabilities.
    """
    temp_dir = setup_teardown

    # Run scans on empty directory
    report = SecurityScannerManager.run_scans(target_path=temp_dir, network_enabled=False)

    assert "pattern_scanner" in report.scanners_available
    # For tools not installed in this environment, they must be reported as unavailable
    assert isinstance(report.scanners_unavailable, list)
    assert report.duration_seconds >= 0

    # If bandit is not installed, it should be in scanners_unavailable
    if not shutil.which("bandit"):
        assert "bandit" in report.scanners_unavailable
        assert report.reports["bandit"].available is False
        assert report.reports["bandit"].ran is False


def test_security_agent_merges_scanner_and_static_analysis(setup_teardown):
    """Verify SecurityAgent combines scanner findings and Codex static security findings."""
    temp_dir = setup_teardown
    agent = SecurityAgent()

    # Create dummy fixture file
    with open(os.path.join(temp_dir, "config.py"), "w") as f:
        f.write("api_key = 'fake_secret_token_1234567890'\n")

    arch_res = AgentResult(AgentType.ARCHITECT, "Architect", AgentStatus.COMPLETED, "Plan...")
    build_res = AgentResult(AgentType.BUILDER, "Builder", AgentStatus.COMPLETED, "Summary...")
    test_res = AgentResult(AgentType.TESTER, "Tester", AgentStatus.COMPLETED, "Tests passed.")

    context = AgentContext(
        project_id=1,
        project_name="SecApp",
        repository_path=temp_dir,
        engineering_run_id=103,
        engineering_goal="Security review",
        previous_results={
            AgentType.ARCHITECT: arch_res,
            AgentType.BUILDER: build_res,
            AgentType.TESTER: test_res
        }
    )

    codex_sec_stdout = (
        "### Security Posture Summary\n"
        "Static inspection confirmed a hard-coded API key and missing rate limiting.\n\n"
        "```json\n"
        "[\n"
        "  {\n"
        "    \"title\": \"Missing authentication on admin route\",\n"
        "    \"severity\": \"HIGH\",\n"
        "    \"category\": \"AUTHENTICATION\",\n"
        "    \"file_path\": \"src/admin.py\",\n"
        "    \"line_number\": 10,\n"
        "    \"description\": \"Route /admin/reset lacks authentication dependency.\",\n"
        "    \"evidence\": \"def reset_db(): pass without auth dependency\",\n"
        "    \"reproduction\": \"curl http://localhost/admin/reset\",\n"
        "    \"remediation\": \"Add Depends(get_current_admin) guard.\"\n"
        "  }\n"
        "]\n"
        "```\n"
    )

    mock_exec = make_exec_result(RunStatus.COMPLETED, 0, codex_sec_stdout, "")

    with patch("backend.codex.runner.CodexRunner.execute", return_value=mock_exec):
        res = agent.run(context)
        assert res.status == AgentStatus.COMPLETED
        findings = res.metadata.get("findings", [])
        # Should include both the pattern scanner finding (api_key) and the codex finding (missing auth)
        assert len(findings) >= 2
        titles = [f["title"] for f in findings]
        assert any("API key" in t for t in titles)
        assert any("Missing authentication" in t for t in titles)


# ==========================================
# 3. FINDING DATABASE MODEL & REST API TESTS
# ==========================================

def test_finding_model_persistence_and_filtering(setup_teardown):
    """Test Finding database model creation, filtering, and summary APIs."""
    temp_dir = setup_teardown
    db = SessionLocal()
    project = Project(name="FindingsProject", repository_path=temp_dir)
    db.add(project)
    db.commit()

    run = EngineeringRun(project_id=project.id, goal="Finding persistence test")
    db.add(run)
    db.commit()

    exec_breaker = AgentExecution(
        engineering_run_id=run.id,
        agent_type=AgentType.BREAKER.value,
        agent_name="Breaker Agent",
        status=AgentStatus.COMPLETED.value
    )
    exec_sec = AgentExecution(
        engineering_run_id=run.id,
        agent_type=AgentType.SECURITY.value,
        agent_name="Security Agent",
        status=AgentStatus.COMPLETED.value
    )
    db.add_all([exec_breaker, exec_sec])
    db.commit()

    f1 = Finding(
        engineering_run_id=run.id,
        agent_execution_id=exec_breaker.id,
        type="BREAKER",
        severity="HIGH",
        category="INPUT_VALIDATION",
        title="Empty payload crash",
        description="Application crashes when payload is empty",
        file_path="src/app.py",
        line_number=20,
        evidence="Exit code 1",
        reproduction="POST / with {}",
        remediation="Validate payload not empty",
        status="OPEN"
    )
    f2 = Finding(
        engineering_run_id=run.id,
        agent_execution_id=exec_sec.id,
        type="SECURITY",
        severity="CRITICAL",
        category="SECRET",
        title="AWS Key leaked",
        description="Key found in config",
        file_path="config.py",
        line_number=5,
        evidence="AKIA...",
        reproduction="View config.py",
        remediation="Remove secret",
        status="OPEN"
    )
    f3 = Finding(
        engineering_run_id=run.id,
        agent_execution_id=exec_sec.id,
        type="SECURITY",
        severity="LOW",
        category="CONFIGURATION",
        title="Debug mode enabled",
        description="DEBUG=True in production settings",
        file_path="settings.py",
        status="OPEN"
    )
    db.add_all([f1, f2, f3])
    db.commit()

    run_id = run.id
    f1_id = f1.id
    db.close()

    # 1. Test GET /api/runs/{run_id}/findings
    resp = client.get(f"/api/runs/{run_id}/findings")
    assert resp.status_code == 200
    all_findings = resp.json()
    assert len(all_findings) == 3

    # 2. Filter by type=BREAKER
    resp = client.get(f"/api/runs/{run_id}/findings?type=BREAKER")
    assert resp.status_code == 200
    breaker_findings = resp.json()
    assert len(breaker_findings) == 1
    assert breaker_findings[0]["type"] == "BREAKER"

    # 3. Filter by severity=CRITICAL
    resp = client.get(f"/api/runs/{run_id}/findings?severity=CRITICAL")
    assert resp.status_code == 200
    crit_findings = resp.json()
    assert len(crit_findings) == 1
    assert crit_findings[0]["title"] == "AWS Key leaked"

    # 4. Filter by category=SECRET
    resp = client.get(f"/api/runs/{run_id}/findings?category=SECRET")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 5. Summary endpoint
    resp = client.get(f"/api/runs/{run_id}/findings/summary")
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["total"] == 3
    assert summary["breaker_count"] == 1
    assert summary["security_count"] == 2
    assert summary["by_severity"]["CRITICAL"] == 1
    assert summary["by_severity"]["HIGH"] == 1
    assert summary["by_severity"]["LOW"] == 1

    # 6. Single finding endpoint
    resp = client.get(f"/api/runs/{run_id}/findings/{f1_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Empty payload crash"

    # 7. Non-existent finding returns 404
    resp = client.get(f"/api/runs/{run_id}/findings/999999")
    assert resp.status_code == 404


# ==========================================
# 4. 5-AGENT WORKFLOW & FAIL-FAST TESTS
# ==========================================

def test_full_5_agent_sequential_workflow(setup_teardown):
    """
    Test complete sequential execution across all 5 agents:
    Architect -> Builder -> Tester -> Breaker -> Security.
    Verifies that all 5 workspaces are allocated and findings are persisted.
    """
    temp_dir = setup_teardown
    db = SessionLocal()
    project = Project(name="Full5AgentProject", repository_path=temp_dir)
    db.add(project)
    db.commit()

    run = EngineeringRun(project_id=project.id, goal="Full 5-agent pipeline test")
    db.add(run)
    db.commit()

    arch_res = make_exec_result(RunStatus.COMPLETED, 0, "Architect: Plan created", "")
    build_res = make_exec_result(RunStatus.COMPLETED, 0, "Builder: Implementation complete", "")
    test_res = make_exec_result(RunStatus.COMPLETED, 0, "Tests Run: 2\nPassed: 2\nFailed: 0\nStatus: PASSED", "")
    breaker_res = make_exec_result(
        RunStatus.COMPLETED, 0,
        "Tests Generated: 2\nTests Executed: 2\nTests Passed: 1\nTests Failed: 1\n"
        "```json\n"
        "[{\"title\": \"Breaker Finding 1\", \"severity\": \"MEDIUM\", \"category\": \"EDGE_CASE\", \"file_path\": \"app.py\", \"line_number\": 12, \"evidence\": \"AssertionError\"}]\n"
        "```", ""
    )
    sec_res = make_exec_result(
        RunStatus.COMPLETED, 0,
        "Security Posture Summary: Verified safe.\n"
        "```json\n"
        "[{\"title\": \"Security Finding 1\", \"severity\": \"LOW\", \"category\": \"CONFIGURATION\", \"file_path\": \"app.py\", \"line_number\": 2, \"evidence\": \"Debug flag\"}]\n"
        "```", ""
    )

    with patch("backend.codex.runner.CodexRunner.execute", side_effect=[arch_res, build_res, test_res, breaker_res, sec_res]):
        with patch("backend.workspace.manager.get_git_provider", return_value=MockGitWorkspaceProvider()):
            with patch("backend.sandbox.manager.get_docker_provider", return_value=MockDockerProvider()):
                AgentManager._workflow_worker(run.id, db=db)

    db.refresh(run)
    assert run.status == RunStatus.COMPLETED.value
    assert "BREAKER ADVERSARIAL ANALYSIS" in run.stdout
    assert "SECURITY AUDIT REPORT" in run.stdout

    # Verify all 5 agent executions
    execs = db.query(AgentExecution).filter(AgentExecution.engineering_run_id == run.id).order_by(AgentExecution.id.asc()).all()
    assert len(execs) == 5
    assert [e.agent_type for e in execs] == ["ARCHITECT", "BUILDER", "TESTER", "BREAKER", "SECURITY"]
    assert all(e.status == AgentStatus.COMPLETED.value for e in execs)

    # Verify findings were automatically persisted to the findings table
    persisted_findings = db.query(Finding).filter(Finding.engineering_run_id == run.id).all()
    assert len(persisted_findings) >= 2
    types = [f.type for f in persisted_findings]
    assert "BREAKER" in types
    assert "SECURITY" in types
    db.close()


def test_workflow_halts_on_tester_failure_before_breaker_and_security(setup_teardown):
    """
    Verify that if the Tester agent detects test failures, the workflow HALTS immediately.
    Breaker and Security agents must NOT be executed.
    """
    temp_dir = setup_teardown
    db = SessionLocal()
    project = Project(name="TesterFailProject", repository_path=temp_dir)
    db.add(project)
    db.commit()

    run = EngineeringRun(project_id=project.id, goal="Run with failing tests")
    db.add(run)
    db.commit()

    arch_res = make_exec_result(RunStatus.COMPLETED, 0, "Plan", "")
    build_res = make_exec_result(RunStatus.COMPLETED, 0, "Implemented", "")
    test_fail_res = make_exec_result(RunStatus.COMPLETED, 1, "Tests Run: 5\nPassed: 3\nFailed: 2\nStatus: FAILED\nAssertionError in test_login", "")

    # Only 3 calls should happen: Architect -> Builder -> Tester (fail)
    with patch("backend.codex.runner.CodexRunner.execute", side_effect=[arch_res, build_res, test_fail_res]):
        with patch("backend.workspace.manager.get_git_provider", return_value=MockGitWorkspaceProvider()):
            with patch("backend.sandbox.manager.get_docker_provider", return_value=MockDockerProvider()):
                AgentManager._workflow_worker(run.id, db=db)

    db.refresh(run)
    assert run.status == RunStatus.FAILED.value
    assert "Tester Agent failed" in run.error_message

    execs = db.query(AgentExecution).filter(AgentExecution.engineering_run_id == run.id).order_by(AgentExecution.id.asc()).all()
    assert len(execs) == 5
    assert execs[0].status == AgentStatus.COMPLETED.value  # Architect
    assert execs[1].status == AgentStatus.COMPLETED.value  # Builder
    assert execs[2].status == AgentStatus.FAILED.value     # Tester
    assert execs[3].status == AgentStatus.PENDING.value    # Breaker: NOT EXECUTED
    assert execs[4].status == AgentStatus.PENDING.value    # Security: NOT EXECUTED
    db.close()


def test_workflow_halts_on_breaker_failure_before_security(setup_teardown):
    """
    Verify that if the Breaker agent itself fails to execute, Security does NOT execute.
    """
    temp_dir = setup_teardown
    db = SessionLocal()
    project = Project(name="BreakerFailProject", repository_path=temp_dir)
    db.add(project)
    db.commit()

    run = EngineeringRun(project_id=project.id, goal="Run with breaker crash")
    db.add(run)
    db.commit()

    arch_res = make_exec_result(RunStatus.COMPLETED, 0, "Plan", "")
    build_res = make_exec_result(RunStatus.COMPLETED, 0, "Implemented", "")
    test_res = make_exec_result(RunStatus.COMPLETED, 0, "Tests Run: 2\nPassed: 2\nFailed: 0\nStatus: PASSED", "")
    breaker_crash = make_exec_result(RunStatus.FAILED, 1, "", "Sandbox container memory limit exceeded", error_message="Container OOMKilled")

    with patch("backend.codex.runner.CodexRunner.execute", side_effect=[arch_res, build_res, test_res, breaker_crash]):
        with patch("backend.workspace.manager.get_git_provider", return_value=MockGitWorkspaceProvider()):
            with patch("backend.sandbox.manager.get_docker_provider", return_value=MockDockerProvider()):
                AgentManager._workflow_worker(run.id, db=db)

    db.refresh(run)
    assert run.status == RunStatus.FAILED.value
    assert "Breaker Agent failed" in run.error_message

    execs = db.query(AgentExecution).filter(AgentExecution.engineering_run_id == run.id).order_by(AgentExecution.id.asc()).all()
    assert len(execs) == 5
    assert execs[0].status == AgentStatus.COMPLETED.value  # Architect
    assert execs[1].status == AgentStatus.COMPLETED.value  # Builder
    assert execs[2].status == AgentStatus.COMPLETED.value  # Tester
    assert execs[3].status == AgentStatus.FAILED.value     # Breaker
    assert execs[4].status == AgentStatus.PENDING.value    # Security: NOT EXECUTED
    db.close()
