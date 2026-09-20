import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database import SessionLocal
from backend.models.project import Project
from backend.models.run import EngineeringRun
from backend.models.agent_execution import AgentExecution
from backend.models.finding import Finding
from backend.agents.models import AgentType, AgentStatus, AgentResult
from backend.services.finding_service import FindingService
from backend.services.control_room_service import ControlRoomService
from backend.orchestrator.policy import OrchestratorPolicy
from backend.orchestrator.models import OrchestratorDecision
from backend.orchestrator.feedback import IterationFeedbackCollector
from backend.evaluation.metrics import MetricCollector
from backend.evaluation.policies import ScoringPolicy


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_project(db_session: Session):
    proj = Project(
        name="Lifecycle Test Project",
        repository_path="C:/dummy/repo",
        description="Test project for finding lifecycle",
    )
    db_session.add(proj)
    db_session.commit()
    return proj


@pytest.fixture
def test_run(db_session: Session, test_project: Project):
    run = EngineeringRun(
        project_id=test_project.id,
        goal="Fix security vulnerability",
        status="RUNNING",
    )
    db_session.add(run)
    db_session.commit()
    return run


def test_1_breaker_creates_open_finding(db_session: Session, test_run: EngineeringRun):
    """1. Breaker creates an OPEN finding in Iteration 1."""
    exec_record = AgentExecution(
        engineering_run_id=test_run.id,
        agent_type="BREAKER",
        agent_name="Breaker Agent",
        status="COMPLETED",
        iteration=1,
    )
    db_session.add(exec_record)
    db_session.commit()

    reported = [
        {
            "type": "BREAKER",
            "severity": "HIGH",
            "category": "INPUT_VALIDATION",
            "title": "Uncaught NoneType in user payload parser",
            "description": "Sending null payload crashes the worker.",
            "file_path": "app/services/parser.py",
            "line_number": 42,
            "evidence": "TypeError: 'NoneType' object is not subscriptable",
        }
    ]

    reconciled = FindingService.reconcile_findings(
        db=db_session,
        run_id=test_run.id,
        agent_execution_id=exec_record.id,
        agent_type=AgentType.BREAKER,
        iteration=1,
        reported_findings=reported,
    )

    assert len(reconciled) == 1
    f = reconciled[0]
    assert f.status == "OPEN"
    assert f.iteration == 1
    assert f.resolved_iteration is None
    assert f.resolved_at is None
    assert f.severity == "HIGH"
    assert f.type == "BREAKER"


def test_2_builder_receives_open_finding(db_session: Session, test_run: EngineeringRun):
    """2. Builder receives the open finding in feedback for Iteration 2."""
    finding = Finding(
        engineering_run_id=test_run.id,
        type="BREAKER",
        severity="HIGH",
        category="INPUT_VALIDATION",
        title="Uncaught NoneType in user payload parser",
        description="Sending null payload crashes worker.",
        file_path="app/services/parser.py",
        line_number=42,
        status="OPEN",
        iteration=1,
    )
    db_session.add(finding)
    db_session.commit()

    # Query active open findings as orchestrator does
    open_breaker = (
        db_session.query(Finding)
        .filter(
            Finding.engineering_run_id == test_run.id,
            Finding.status == "OPEN",
            Finding.type == "BREAKER",
        )
        .all()
    )

    breaker_dicts = [
        {"severity": f.severity, "title": f.title, "description": f.description}
        for f in open_breaker
    ]

    feedback = IterationFeedbackCollector.extract_feedback(
        iteration=1,
        decision_reason="HIGH severity Breaker finding discovered",
        breaker_findings=breaker_dicts,
    )

    assert feedback["iteration"] == 2
    assert len(feedback["breaker_findings"]) == 1
    assert feedback["breaker_findings"][0]["title"] == "Uncaught NoneType in user payload parser"


def test_3_breaker_validation_resolves_finding(db_session: Session, test_run: EngineeringRun):
    """3 & 4. Subsequent Breaker validation no longer reports the issue -> transitions to RESOLVED."""
    # Iteration 1: Finding detected
    exec_1 = AgentExecution(
        engineering_run_id=test_run.id,
        agent_type="BREAKER",
        agent_name="Breaker Agent",
        status="COMPLETED",
        iteration=1,
    )
    db_session.add(exec_1)
    db_session.commit()

    FindingService.reconcile_findings(
        db=db_session,
        run_id=test_run.id,
        agent_execution_id=exec_1.id,
        agent_type=AgentType.BREAKER,
        iteration=1,
        reported_findings=[
            {
                "type": "BREAKER",
                "severity": "HIGH",
                "category": "INPUT_VALIDATION",
                "title": "Uncaught NoneType in user payload parser",
                "file_path": "app/services/parser.py",
                "line_number": 42,
            }
        ],
    )

    initial_finding = (
        db_session.query(Finding)
        .filter(Finding.engineering_run_id == test_run.id)
        .first()
    )
    assert initial_finding.status == "OPEN"
    initial_id = initial_finding.id

    # Iteration 2: Builder fixed the issue -> Breaker runs clean (0 findings reported)
    exec_2 = AgentExecution(
        engineering_run_id=test_run.id,
        agent_type="BREAKER",
        agent_name="Breaker Agent",
        status="COMPLETED",
        iteration=2,
    )
    db_session.add(exec_2)
    db_session.commit()

    FindingService.reconcile_findings(
        db=db_session,
        run_id=test_run.id,
        agent_execution_id=exec_2.id,
        agent_type=AgentType.BREAKER,
        iteration=2,
        reported_findings=[],  # Clean scan!
    )

    # Re-fetch from DB
    db_session.refresh(initial_finding)
    assert initial_finding.id == initial_id
    assert initial_finding.status == "RESOLVED"
    assert initial_finding.iteration == 1  # First detected in iteration 1
    assert initial_finding.resolved_iteration == 2  # Resolved in iteration 2
    assert initial_finding.resolved_at is not None


def test_5_finding_remains_open_when_issue_still_detected(db_session: Session, test_run: EngineeringRun):
    """5. Finding remains OPEN when the issue is still detected; no duplicates created."""
    exec_1 = AgentExecution(
        engineering_run_id=test_run.id,
        agent_type="BREAKER",
        agent_name="Breaker Agent",
        status="COMPLETED",
        iteration=1,
    )
    db_session.add(exec_1)
    db_session.commit()

    finding_data = {
        "type": "BREAKER",
        "severity": "HIGH",
        "category": "ERROR_HANDLING",
        "title": "Division by zero in metrics calculator",
        "file_path": "app/metrics.py",
        "line_number": 88,
        "evidence": "ZeroDivisionError: division by zero",
    }

    # Iteration 1
    FindingService.reconcile_findings(
        db=db_session,
        run_id=test_run.id,
        agent_execution_id=exec_1.id,
        agent_type=AgentType.BREAKER,
        iteration=1,
        reported_findings=[finding_data],
    )

    count_iter_1 = db_session.query(Finding).filter(Finding.engineering_run_id == test_run.id).count()
    assert count_iter_1 == 1

    # Iteration 2: Builder failed to fix -> Breaker detects the exact same issue again
    exec_2 = AgentExecution(
        engineering_run_id=test_run.id,
        agent_type="BREAKER",
        agent_name="Breaker Agent",
        status="COMPLETED",
        iteration=2,
    )
    db_session.add(exec_2)
    db_session.commit()

    # Slightly shifted line number due to edits
    finding_data_iter2 = dict(finding_data)
    finding_data_iter2["line_number"] = 92

    FindingService.reconcile_findings(
        db=db_session,
        run_id=test_run.id,
        agent_execution_id=exec_2.id,
        agent_type=AgentType.BREAKER,
        iteration=2,
        reported_findings=[finding_data_iter2],
    )

    all_findings = db_session.query(Finding).filter(Finding.engineering_run_id == test_run.id).all()
    assert len(all_findings) == 1  # NO duplicate row
    f = all_findings[0]
    assert f.status == "OPEN"
    assert f.iteration == 1
    assert f.resolved_iteration is None
    assert f.line_number == 92  # Updated to newest observation


def test_6_security_finding_resolved_after_clean_scan(db_session: Session, test_run: EngineeringRun):
    """6. Security finding is resolved after a subsequent clean security scan."""
    exec_sec_1 = AgentExecution(
        engineering_run_id=test_run.id,
        agent_type="SECURITY",
        agent_name="Security Agent",
        status="COMPLETED",
        iteration=1,
    )
    db_session.add(exec_sec_1)
    db_session.commit()

    sec_finding = {
        "type": "SECURITY",
        "severity": "CRITICAL",
        "category": "SECRET",
        "title": "Hardcoded Stripe API secret key",
        "file_path": "config/secrets.py",
        "line_number": 12,
        "evidence": "sk_live_51Abc...",
    }

    FindingService.reconcile_findings(
        db=db_session,
        run_id=test_run.id,
        agent_execution_id=exec_sec_1.id,
        agent_type=AgentType.SECURITY,
        iteration=1,
        reported_findings=[sec_finding],
    )

    f_record = db_session.query(Finding).filter(Finding.engineering_run_id == test_run.id).first()
    assert f_record.status == "OPEN"
    assert f_record.severity == "CRITICAL"

    # Iteration 2: Builder replaced hardcoded secret with os.getenv -> clean security scan
    exec_sec_2 = AgentExecution(
        engineering_run_id=test_run.id,
        agent_type="SECURITY",
        agent_name="Security Agent",
        status="COMPLETED",
        iteration=2,
    )
    db_session.add(exec_sec_2)
    db_session.commit()

    FindingService.reconcile_findings(
        db=db_session,
        run_id=test_run.id,
        agent_execution_id=exec_sec_2.id,
        agent_type=AgentType.SECURITY,
        iteration=2,
        reported_findings=[],
    )

    db_session.refresh(f_record)
    assert f_record.status == "RESOLVED"
    assert f_record.resolved_iteration == 2
    assert f_record.resolved_at is not None


def test_7_no_duplicate_unresolved_state_across_3_iterations(db_session: Session, test_run: EngineeringRun):
    """7. Same finding detected across multiple iterations does not create duplicate records."""
    finding_data = {
        "type": "BREAKER",
        "severity": "HIGH",
        "category": "EDGE_CASE",
        "title": "Memory leak on continuous stream ingestion",
        "file_path": "app/stream.py",
        "line_number": 105,
    }

    for iter_num in (1, 2, 3):
        exec_record = AgentExecution(
            engineering_run_id=test_run.id,
            agent_type="BREAKER",
            agent_name="Breaker Agent",
            status="COMPLETED",
            iteration=iter_num,
        )
        db_session.add(exec_record)
        db_session.commit()

        FindingService.reconcile_findings(
            db=db_session,
            run_id=test_run.id,
            agent_execution_id=exec_record.id,
            agent_type=AgentType.BREAKER,
            iteration=iter_num,
            reported_findings=[finding_data],
        )

    findings = db_session.query(Finding).filter(Finding.engineering_run_id == test_run.id).all()
    assert len(findings) == 1
    assert findings[0].status == "OPEN"
    assert findings[0].iteration == 1


def test_8_resolved_findings_not_treated_as_active_in_evaluation(test_run: EngineeringRun):
    """8. Resolved findings are not treated as active findings by evaluation."""
    findings = []
    # 2 active OPEN findings
    for i in range(2):
        findings.append(
            Finding(
                engineering_run_id=test_run.id,
                type="SECURITY",
                severity="MEDIUM",
                category="CONFIGURATION",
                title=f"Open Config Issue {i}",
                status="OPEN",
                iteration=1,
            )
        )
    # 8 RESOLVED findings
    for i in range(8):
        findings.append(
            Finding(
                engineering_run_id=test_run.id,
                type="SECURITY",
                severity="HIGH",
                category="SECRET",
                title=f"Resolved Secret {i}",
                status="RESOLVED",
                iteration=1,
                resolved_iteration=2,
                resolved_at=datetime.now(timezone.utc),
            )
        )

    stats = MetricCollector._aggregate_findings(findings)
    assert stats["total_findings"] == 10
    assert stats["open_findings"] == 2
    assert stats["resolved_findings"] == 8
    # Only the 2 OPEN medium findings should count toward severity metrics
    assert stats["medium_findings"] == 2
    assert stats["high_findings"] == 0
    assert stats["critical_findings"] == 0

    # Test scoring: 2 medium (-16 pts) -> score = 84.0, ADEQUATE/STRONG
    # (If the 8 resolved HIGH findings had been counted, penalty would have been 8*20 = 160 -> score 0.0)
    from backend.evaluation.models import MetricItem
    metrics_map = {
        "critical_findings": MetricItem(name="critical_findings", value=stats["critical_findings"]),
        "high_findings": MetricItem(name="high_findings", value=stats["high_findings"]),
        "medium_findings": MetricItem(name="medium_findings", value=stats["medium_findings"]),
        "low_findings": MetricItem(name="low_findings", value=stats["low_findings"]),
        "info_findings": MetricItem(name="info_findings", value=stats["info_findings"]),
    }
    sec_result = ScoringPolicy.evaluate_security(metrics_map, weight=0.25)
    assert sec_result.score == 84.0
    assert sec_result.score > 80.0


def test_9_orchestrator_decision_policy_and_max_iterations():
    """9. The orchestrator continues on open blocking findings, stops on success when resolved, and respects max_iterations."""
    builder_ok = AgentResult(
        agent_type=AgentType.BUILDER,
        agent_name="Builder Agent",
        status=AgentStatus.COMPLETED,
        output="Code changes applied.",
    )
    tester_ok = AgentResult(
        agent_type=AgentType.TESTER,
        agent_name="Tester Agent",
        status=AgentStatus.COMPLETED,
        output="15 passed in 0.4s",
    )

    # Case A: High finding present in Iteration 1 of 3 -> RETRY_BUILDER
    decision_iter1 = OrchestratorPolicy.evaluate(
        iteration=1,
        max_iterations=3,
        builder_result=builder_ok,
        tester_result=tester_ok,
        breaker_findings=[{"severity": "HIGH", "title": "Crash on empty input"}],
        security_findings=[],
    )
    assert decision_iter1.decision == OrchestratorDecision.RETRY_BUILDER

    # Case B: In Iteration 2, finding is resolved (0 blocking findings) -> STOP_SUCCESS
    decision_iter2 = OrchestratorPolicy.evaluate(
        iteration=2,
        max_iterations=3,
        builder_result=builder_ok,
        tester_result=tester_ok,
        breaker_findings=[],  # Resolved!
        security_findings=[],
    )
    assert decision_iter2.decision == OrchestratorDecision.STOP_SUCCESS

    # Case C: Still unresolved at max_iterations (Iteration 3 of 3) -> STOP_FAILURE
    decision_iter3 = OrchestratorPolicy.evaluate(
        iteration=3,
        max_iterations=3,
        builder_result=builder_ok,
        tester_result=tester_ok,
        breaker_findings=[{"severity": "HIGH", "title": "Crash on empty input"}],
        security_findings=[],
    )
    assert decision_iter3.decision == OrchestratorDecision.STOP_FAILURE
    assert "maximum iteration limit (3) was reached with unresolved issues" in decision_iter3.reason


def test_10_control_room_snapshot_shows_open_vs_resolved(db_session: Session, test_run: EngineeringRun):
    """10. Control Room findings display and summary accurately reflect OPEN vs RESOLVED."""
    f_open = Finding(
        engineering_run_id=test_run.id,
        type="BREAKER",
        severity="MEDIUM",
        category="API_BEHAVIOR",
        title="Uncaught 500 error",
        description="Missing error handler",
        status="OPEN",
        iteration=1,
    )
    f_resolved = Finding(
        engineering_run_id=test_run.id,
        type="SECURITY",
        severity="HIGH",
        category="SECRET",
        title="AWS Access Key",
        description="Hardcoded key in credentials.py",
        status="RESOLVED",
        iteration=1,
        resolved_iteration=2,
        resolved_at=datetime.now(timezone.utc),
    )
    db_session.add_all([f_open, f_resolved])
    db_session.commit()

    snapshot = ControlRoomService.get_snapshot(test_run.id, db_session)
    assert snapshot is not None
    assert snapshot.findings_summary.total == 2
    assert snapshot.findings_summary.open == 1
    assert snapshot.findings_summary.resolved == 1

    findings = snapshot.findings
    assert len(findings) == 2

    resolved_items = [f for f in findings if f.status == "RESOLVED"]
    assert len(resolved_items) == 1
    assert resolved_items[0].resolved_iteration == 2
    assert resolved_items[0].resolved_at is not None

    open_items = [f for f in findings if f.status == "OPEN"]
    assert len(open_items) == 1
    assert open_items[0].resolved_iteration is None


def test_11_finding_fingerprint_matching_logic():
    """Verify robust matching between candidate findings and existing records."""
    f = Finding(
        engineering_run_id=1,
        type="BREAKER",
        severity="HIGH",
        category="INPUT_VALIDATION",
        title="Uncaught NoneType in user payload parser",
        file_path="app/services/parser.py",
        line_number=45,
    )

    # 1. Exact match
    assert FindingService.matches(f, {
        "type": "BREAKER",
        "title": "Uncaught NoneType in user payload parser",
        "file_path": "app/services/parser.py",
        "line_number": 45,
    })

    # 2. Windows vs Unix path normalization and case insensitivity
    assert FindingService.matches(f, {
        "type": "BREAKER",
        "title": "uncaught nonetype in user payload parser",
        "file_path": "app\\services\\parser.py",
        "line_number": 48,  # Shifted line number
    })

    # 3. Agent title prefix difference
    assert FindingService.matches(f, {
        "type": "BREAKER",
        "title": "Adversarial finding: Uncaught NoneType in user payload parser",
        "file_path": "./app/services/parser.py",
    })

    # 4. Different agent type should NEVER match
    assert not FindingService.matches(f, {
        "type": "SECURITY",
        "title": "Uncaught NoneType in user payload parser",
        "file_path": "app/services/parser.py",
    })

    # 5. Different file should NOT match
    assert not FindingService.matches(f, {
        "type": "BREAKER",
        "title": "Uncaught NoneType in user payload parser",
        "file_path": "app/other.py",
    })
