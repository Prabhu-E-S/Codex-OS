import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.database import Base, engine, SessionLocal
from backend.main import app
from backend.models.project import Project
from backend.models.run import EngineeringRun
from backend.models.agent_execution import AgentExecution
from backend.models.finding import Finding
from backend.models.orchestration import OrchestrationState
from backend.models.evaluation import Evaluation, EvaluationDimension, EvaluationEvidence
from backend.evaluation.models import (
    EvaluationDimensionType,
    DimensionStatus,
    EvaluationStatus,
    DimensionResult,
    MetricItem,
)
from backend.evaluation.policies import ScoringPolicy
from backend.evaluation.evidence import redact_sensitive_text, make_evidence_item
from backend.evaluation.metrics import MetricCollector
from backend.evaluation.judge import JudgeAgent
from backend.evaluation.manager import EvaluationManager
from backend.evaluation.exceptions import InvalidScoreWeightsError

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    Base.metadata.create_all(bind=engine)
    from backend.main import _migrate_schema
    _migrate_schema()
    yield


def test_deterministic_scoring_formula_section_50():
    """
    Test the exact mathematical requirements from Phase 8 prompt Section 50:
    Given:
      Correctness = 80
      Test Coverage = 70
      Security = 90
      Maintainability = 80
      Performance = 60
      Regression Risk = 70
    Weights:
      30%, 15%, 20%, 15%, 10%, 10%
    Expected:
      80 * 0.30 + 70 * 0.15 + 90 * 0.20 + 80 * 0.15 + 60 * 0.10 + 70 * 0.10
      = 24.0 + 10.5 + 18.0 + 12.0 + 6.0 + 7.0 = 77.5
    """
    weights = {
        "CORRECTNESS": 0.30,
        "TEST_COVERAGE": 0.15,
        "SECURITY": 0.20,
        "MAINTAINABILITY": 0.15,
        "PERFORMANCE": 0.10,
        "REGRESSION_RISK": 0.10,
    }

    dim_results = [
        DimensionResult(
            dimension=EvaluationDimensionType.CORRECTNESS,
            score=80.0,
            status=DimensionStatus.STRONG,
            weight=0.30,
            weighted_score=24.0,
            explanation="Correctness test",
        ),
        DimensionResult(
            dimension=EvaluationDimensionType.TEST_COVERAGE,
            score=70.0,
            status=DimensionStatus.ADEQUATE,
            weight=0.15,
            weighted_score=10.5,
            explanation="Coverage test",
        ),
        DimensionResult(
            dimension=EvaluationDimensionType.SECURITY,
            score=90.0,
            status=DimensionStatus.STRONG,
            weight=0.20,
            weighted_score=18.0,
            explanation="Security test",
        ),
        DimensionResult(
            dimension=EvaluationDimensionType.MAINTAINABILITY,
            score=80.0,
            status=DimensionStatus.STRONG,
            weight=0.15,
            weighted_score=12.0,
            explanation="Maintainability test",
        ),
        DimensionResult(
            dimension=EvaluationDimensionType.PERFORMANCE,
            score=60.0,
            status=DimensionStatus.ADEQUATE,
            weight=0.10,
            weighted_score=6.0,
            explanation="Performance test",
        ),
        DimensionResult(
            dimension=EvaluationDimensionType.REGRESSION_RISK,
            score=70.0,
            status=DimensionStatus.ADEQUATE,
            weight=0.10,
            weighted_score=7.0,
            explanation="Regression risk test",
        ),
    ]

    res = ScoringPolicy.calculate_overall_engineering_score(dim_results, weights, "v1")
    assert res.overall_score == 77.5
    assert res.status_label == DimensionStatus.ADEQUATE
    assert "(80.0 × 30%)" in res.formula
    assert "(70.0 × 15%)" in res.formula
    assert "(90.0 × 20%)" in res.formula
    assert "77.5 / 100" in res.formula


def test_weights_validation_and_invalid_sum():
    """Verify weight sum validation rejects weights that do not equal 1.0."""
    from backend.config import settings

    # Default settings weights must sum to 1.0
    w = settings.get_evaluation_weights()
    assert abs(sum(w.values()) - 1.0) < 1e-5

    # Invalid custom weights
    bad_weights = {"CORRECTNESS": 0.50, "TEST_COVERAGE": 0.10}  # sum = 0.60
    with pytest.raises(InvalidScoreWeightsError):
        EvaluationManager.evaluate_run(run_id=999, db=None, custom_weights=bad_weights)


def test_insufficient_evidence_handling_section_51():
    """
    Verify coverage and performance tooling discovery:
    1. If coverage tool is missing: do NOT fabricate percentage or set to 0/100;
       report status = INSUFFICIENT_EVIDENCE, score = None.
    2. If benchmark is missing: report INSUFFICIENT_EVIDENCE, score = None.
    3. Overall score normalizes across remaining evaluated dimensions.
    """
    empty_metrics = {
        "coverage_available": MetricItem(name="coverage_available", value=False),
        "benchmark_available": MetricItem(name="benchmark_available", value=False),
        "timeout_occurrences": MetricItem(name="timeout_occurrences", value=0),
    }

    # Coverage dimension test
    cov_dim = ScoringPolicy.evaluate_test_coverage(empty_metrics, weight=0.15)
    assert cov_dim.score is None
    assert cov_dim.status == DimensionStatus.INSUFFICIENT_EVIDENCE
    assert cov_dim.limitations is not None
    assert "unavailable" in cov_dim.explanation.lower()

    # Performance dimension test
    perf_dim = ScoringPolicy.evaluate_performance(empty_metrics, weight=0.10)
    assert perf_dim.score is None
    assert perf_dim.status == DimensionStatus.INSUFFICIENT_EVIDENCE
    assert perf_dim.limitations is not None
    assert "no performance benchmark" in perf_dim.explanation.lower()

    # Calculate overall score with 2 insufficient evidence dimensions
    evaluated_dims = [
        DimensionResult(
            dimension=EvaluationDimensionType.CORRECTNESS,
            score=90.0,
            status=DimensionStatus.STRONG,
            weight=0.30,
            weighted_score=27.0,
            explanation="Correctness",
        ),
        cov_dim,  # score=None, weight=0.15
        DimensionResult(
            dimension=EvaluationDimensionType.SECURITY,
            score=100.0,
            status=DimensionStatus.STRONG,
            weight=0.20,
            weighted_score=20.0,
            explanation="Security",
        ),
        DimensionResult(
            dimension=EvaluationDimensionType.MAINTAINABILITY,
            score=80.0,
            status=DimensionStatus.STRONG,
            weight=0.15,
            weighted_score=12.0,
            explanation="Maintainability",
        ),
        perf_dim,  # score=None, weight=0.10
        DimensionResult(
            dimension=EvaluationDimensionType.REGRESSION_RISK,
            score=80.0,
            status=DimensionStatus.STRONG,
            weight=0.10,
            weighted_score=8.0,
            explanation="Regression",
        ),
    ]

    weights = {"CORRECTNESS": 0.30, "TEST_COVERAGE": 0.15, "SECURITY": 0.20, "MAINTAINABILITY": 0.15, "PERFORMANCE": 0.10, "REGRESSION_RISK": 0.10}
    res = ScoringPolicy.calculate_overall_engineering_score(evaluated_dims, weights, "v1")

    # Evaluated sum: 90*0.30 + 100*0.20 + 80*0.15 + 80*0.10 = 27 + 20 + 12 + 8 = 67.0
    # Total evaluated weights: 0.30 + 0.20 + 0.15 + 0.10 = 0.75
    # Normalized score: 67.0 / 0.75 = 89.333... -> 89.3
    assert res.overall_score == 89.3
    assert "Normalized across 4 evaluated dimensions" in res.formula
    assert "TEST_COVERAGE" in res.formula
    assert "PERFORMANCE" in res.formula


def test_security_scoring_severity_policy_and_redaction():
    """Verify explicit penalty deductions for vulnerabilities and credential redaction."""
    # 1. Clean security metrics
    clean_metrics = {
        "critical_findings": MetricItem(name="critical_findings", value=0),
        "high_findings": MetricItem(name="high_findings", value=0),
        "medium_findings": MetricItem(name="medium_findings", value=0),
        "low_findings": MetricItem(name="low_findings", value=0),
        "info_findings": MetricItem(name="info_findings", value=0),
    }
    sec_clean = ScoringPolicy.evaluate_security(clean_metrics, weight=0.20)
    assert sec_clean.score == 100.0
    assert sec_clean.status == DimensionStatus.STRONG

    # 2. Metrics with vulnerabilities:
    # 1 CRITICAL (-35), 1 HIGH (-20), 2 MEDIUM (-16), 1 LOW (-3), 2 INFO (-1)
    # Total penalties: 35 + 20 + 16 + 3 + 1 = 75.0 pts
    # Score = 100.0 - 75.0 = 25.0
    vuln_metrics = {
        "critical_findings": MetricItem(name="critical_findings", value=1),
        "high_findings": MetricItem(name="high_findings", value=1),
        "medium_findings": MetricItem(name="medium_findings", value=2),
        "low_findings": MetricItem(name="low_findings", value=1),
        "info_findings": MetricItem(name="info_findings", value=2),
    }
    sec_vuln = ScoringPolicy.evaluate_security(vuln_metrics, weight=0.20)
    assert sec_vuln.score == 25.0
    assert sec_vuln.status == DimensionStatus.WEAK
    assert "1 CRITICAL" in sec_vuln.explanation
    assert "1 HIGH" in sec_vuln.explanation

    # 3. Secret Redaction Test
    raw_secret_evidence = "Found secret: api_key='sk-prod-99238472938472' and AWS key AKIAIOSFODNN7EXAMPLE in config.py"
    redacted = redact_sensitive_text(raw_secret_evidence)
    assert "sk-prod" not in redacted
    assert "<REDACTED>" in redacted
    assert "AKIA<REDACTED>" in redacted


def test_judge_agent_structured_output_no_numerical_authority():
    """Verify Judge Agent generates structured qualitative output without altering scores."""
    judge = JudgeAgent()
    metrics = {
        "total_tests": MetricItem(name="total_tests", value=50),
        "passed_tests": MetricItem(name="passed_tests", value=48),
        "failed_tests": MetricItem(name="failed_tests", value=2),
        "coverage_available": MetricItem(name="coverage_available", value=False),
        "critical_findings": MetricItem(name="critical_findings", value=0),
        "high_findings": MetricItem(name="high_findings", value=0),
        "medium_findings": MetricItem(name="medium_findings", value=1),
        "linter_available": MetricItem(name="linter_available", value=False),
        "benchmark_available": MetricItem(name="benchmark_available", value=False),
        "iteration_count": MetricItem(name="iteration_count", value=2),
        "unresolved_breaker_findings": MetricItem(name="unresolved_breaker_findings", value=0),
    }

    dim_results = [
        DimensionResult(
            dimension=EvaluationDimensionType.CORRECTNESS,
            score=86.0,
            status=DimensionStatus.STRONG,
            weight=0.30,
            weighted_score=25.8,
            explanation="48/50 tests passed.",
        ),
    ]

    findings = [
        Finding(
            id=1,
            engineering_run_id=1,
            type="BREAKER",
            severity="MEDIUM",
            category="INPUT_VALIDATION",
            title="Empty payload edge case",
            description="Empty JSON returns 500 instead of 400",
        )
    ]

    output = judge.synthesize(
        engineering_goal="Implement user authentication API",
        metrics=metrics,
        dimension_results=dim_results,
        findings=findings,
    )

    assert isinstance(output.summary, str)
    assert len(output.strengths) > 0
    assert len(output.weaknesses) > 0
    assert len(output.limitations) > 0
    assert "CORRECTNESS" in output.dimension_notes
    # Ensure Judge cannot set or inject numerical scores directly
    assert not hasattr(output, "overall_score")


def test_full_evaluation_lifecycle_and_historical_preservation():
    """
    Integration test verifying:
    1. Project and completed EngineeringRun creation
    2. AgentExecutions (Builder, Tester), Findings, OrchestrationState setup
    3. Evaluation trigger via REST API POST /api/runs/{id}/evaluate
    4. Deterministic dimension and overall score persistence
    5. Second evaluation trigger verifying historical evaluations are preserved (v1, v2)
    6. REST API retrieval of dimensions and evidence
    """
    db = SessionLocal()
    try:
        # Setup test project & run
        proj = Project(name="Phase 8 Demo", repository_path="d:/test/repo")
        db.add(proj)
        db.commit()
        db.refresh(proj)

        run = EngineeringRun(
            project_id=proj.id,
            goal="Implement JWT token verification",
            status="COMPLETED",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            exit_code=0,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        # Add agent executions
        builder_exec = AgentExecution(
            engineering_run_id=run.id,
            agent_type="BUILDER",
            agent_name="Builder Agent",
            status="COMPLETED",
            output="Successfully created auth/jwt.py and updated routes.",
            iteration=1,
        )
        tester_exec = AgentExecution(
            engineering_run_id=run.id,
            agent_type="TESTER",
            agent_name="Tester Agent",
            status="COMPLETED",
            output="================ 20 passed in 0.85s ================",
            iteration=1,
        )
        db.add_all([builder_exec, tester_exec])

        # Add findings
        finding = Finding(
            engineering_run_id=run.id,
            agent_execution_id=tester_exec.id,
            type="BREAKER",
            severity="LOW",
            category="EDGE_CASE",
            title="Expired token edge case handled",
            description="Expired token correctly raises 401 with informative message.",
            iteration=1,
        )
        db.add(finding)

        # Add orchestration state
        orch = OrchestrationState(
            engineering_run_id=run.id,
            state="COMPLETED",
            iteration=1,
            max_iterations=3,
            last_decision="STOP_SUCCESS",
            last_decision_reason="All 20 tests passed and zero blocking findings remain.",
        )
        db.add(orch)
        db.commit()

        # 1. Trigger First Evaluation via API
        resp1 = client.post(f"/api/runs/{run.id}/evaluate", json={})
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["engineering_run_id"] == run.id
        assert data1["status"] == "COMPLETED"
        assert data1["overall_score"] is not None
        assert data1["overall_score"] > 70.0
        assert len(data1["dimensions"]) == 6
        assert len(data1["evidence_items"]) > 0
        assert data1["summary"] is not None
        eval1_id = data1["id"]

        # 2. Trigger Second Evaluation (Re-evaluate) to verify historical preservation
        resp2 = client.post(f"/api/runs/{run.id}/evaluate", json={})
        assert resp2.status_code == 200
        data2 = resp2.json()
        eval2_id = data2["id"]
        assert eval2_id != eval1_id

        # Verify both evaluations are preserved
        hist_resp = client.get(f"/api/runs/{run.id}/evaluations")
        assert hist_resp.status_code == 200
        eval_list = hist_resp.json()
        assert len(eval_list) >= 2
        eval_ids = [e["id"] for e in eval_list]
        assert eval1_id in eval_ids
        assert eval2_id in eval_ids

        # 3. Verify Evaluation Details & Dimensions API
        detail_resp = client.get(f"/api/evaluations/{eval1_id}")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["id"] == eval1_id
        assert detail_data["formula"] is not None

        dims_resp = client.get(f"/api/evaluations/{eval1_id}/dimensions")
        assert dims_resp.status_code == 200
        dims_data = dims_resp.json()
        assert len(dims_data) == 6
        dim_names = {d["dimension"] for d in dims_data}
        assert "CORRECTNESS" in dim_names
        assert "SECURITY" in dim_names
        assert "TEST_COVERAGE" in dim_names

        evidence_resp = client.get(f"/api/evaluations/{eval1_id}/evidence")
        assert evidence_resp.status_code == 200
        evidence_data = evidence_resp.json()
        assert len(evidence_data) > 0

        # 4. Verify Project Evaluations API
        proj_evals = client.get(f"/api/projects/{proj.id}/evaluations")
        assert proj_evals.status_code == 200
        assert len(proj_evals.json()) >= 2
    finally:
        db.close()
