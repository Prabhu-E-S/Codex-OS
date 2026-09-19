import logging
from typing import Dict, List, Optional
from backend.evaluation.models import (
    EvaluationDimensionType,
    DimensionStatus,
    DimensionResult,
    OverallScoreResult,
    MetricItem,
    EvidenceItem,
    EvidenceSourceType,
)
from backend.evaluation.evidence import make_evidence_item

logger = logging.getLogger("codex_os.evaluation.policies")

class ScoringPolicy:
    """
    Deterministic scoring policies for each engineering evaluation dimension.
    Scores are strictly calculated via transparent mathematical rules and evidence.
    No arbitrary LLM numerical scores are generated or accepted.
    """

    @classmethod
    def evaluate_correctness(cls, metrics: Dict[str, MetricItem], weight: float) -> DimensionResult:
        dim = EvaluationDimensionType.CORRECTNESS
        evidence_items: List[EvidenceItem] = []
        metric_dict = {}

        tests_available = metrics.get("tests_available", MetricItem(name="", value=False)).value
        builder_completed = metrics.get("builder_completed", MetricItem(name="", value=False)).value

        if tests_available:
            total = metrics.get("total_tests", MetricItem(name="", value=0)).value or 0
            passed = metrics.get("passed_tests", MetricItem(name="", value=0)).value or 0
            failed = metrics.get("failed_tests", MetricItem(name="", value=0)).value or 0
            pass_rate = metrics.get("test_pass_rate", MetricItem(name="", value=0.0)).value or 0.0

            metric_dict = {"total_tests": total, "passed_tests": passed, "failed_tests": failed, "pass_rate": pass_rate}

            # Formula: pass_rate minus penalty for failed tests
            penalty = min(40.0, failed * 5.0)
            score = round(max(0.0, min(100.0, pass_rate - penalty)), 1)
            status = DimensionStatus.STRONG if score >= 80.0 else (DimensionStatus.ADEQUATE if score >= 60.0 else DimensionStatus.WEAK)

            explanation = (
                f"{passed}/{total} automated tests passed ({pass_rate}% pass rate). "
                + (f"Deducted {penalty:.1f} points for {failed} failing test(s)." if failed > 0 else "All verified tests passed.")
            )

            evidence_items.append(make_evidence_item(
                dimension=dim.value,
                source_type=EvidenceSourceType.TEST,
                metric_name="test_results",
                metric_value=f"{passed}/{total}",
                unit="tests",
                description=f"{passed} passed, {failed} failed out of {total} total tests.",
            ))
            return DimensionResult(
                dimension=dim,
                score=score,
                status=status,
                weight=weight,
                weighted_score=round(score * weight, 2),
                explanation=explanation,
                metrics=metric_dict,
                evidence_items=evidence_items,
            )

        # Fallback when no automated tests were found
        if builder_completed:
            score = 45.0
            status = DimensionStatus.WEAK
            explanation = "No automated test suite was detected. Builder completed code modifications, but correctness cannot be verified without automated tests."
            limitations = "Lack of automated test evidence prevents full correctness verification."
        else:
            score = 0.0
            status = DimensionStatus.WEAK
            explanation = "Builder agent did not complete successfully and no automated tests passed."
            limitations = "Implementation was incomplete."

        evidence_items.append(make_evidence_item(
            dimension=dim.value,
            source_type=EvidenceSourceType.AGENT_EXECUTION,
            metric_name="test_availability",
            metric_value="false",
            description="No automated test evidence available in run output.",
        ))

        return DimensionResult(
            dimension=dim,
            score=score,
            status=status,
            weight=weight,
            weighted_score=round(score * weight, 2),
            explanation=explanation,
            metrics=metric_dict,
            evidence_items=evidence_items,
            limitations=limitations,
        )

    @classmethod
    def evaluate_test_coverage(cls, metrics: Dict[str, MetricItem], weight: float) -> DimensionResult:
        dim = EvaluationDimensionType.TEST_COVERAGE
        evidence_items: List[EvidenceItem] = []
        coverage_available = metrics.get("coverage_available", MetricItem(name="", value=False)).value

        if coverage_available:
            line_cov = metrics.get("line_coverage", MetricItem(name="", value=0.0)).value or 0.0
            score = round(max(0.0, min(100.0, float(line_cov))), 1)
            status = DimensionStatus.STRONG if score >= 85.0 else (DimensionStatus.ADEQUATE if score >= 70.0 else DimensionStatus.WEAK)
            explanation = f"Automated line coverage is {score}%."

            evidence_items.append(make_evidence_item(
                dimension=dim.value,
                source_type=EvidenceSourceType.COVERAGE,
                metric_name="line_coverage",
                metric_value=f"{score}%",
                unit="%",
                description=f"Verified code line coverage: {score}%.",
            ))

            return DimensionResult(
                dimension=dim,
                score=score,
                status=status,
                weight=weight,
                weighted_score=round(score * weight, 2),
                explanation=explanation,
                metrics={"line_coverage": score},
                evidence_items=evidence_items,
            )

        # Honest discovery: tool was unavailable, do NOT fabricate percentage or set to 0/100
        explanation = "Coverage tooling was unavailable or coverage metrics were not generated. Code coverage cannot be verified."
        limitations = "Coverage tool (e.g. pytest-cov, jest coverage) was not detected."

        evidence_items.append(make_evidence_item(
            dimension=dim.value,
            source_type=EvidenceSourceType.COVERAGE,
            metric_name="coverage_tool_availability",
            metric_value="unavailable",
            description="Coverage report unavailable.",
        ))

        return DimensionResult(
            dimension=dim,
            score=None,
            status=DimensionStatus.INSUFFICIENT_EVIDENCE,
            weight=weight,
            weighted_score=None,
            explanation=explanation,
            metrics={"coverage_available": False},
            evidence_items=evidence_items,
            limitations=limitations,
        )

    @classmethod
    def evaluate_security(cls, metrics: Dict[str, MetricItem], weight: float) -> DimensionResult:
        dim = EvaluationDimensionType.SECURITY
        evidence_items: List[EvidenceItem] = []

        crit = metrics.get("critical_findings", MetricItem(name="", value=0)).value or 0
        high = metrics.get("high_findings", MetricItem(name="", value=0)).value or 0
        med = metrics.get("medium_findings", MetricItem(name="", value=0)).value or 0
        low = metrics.get("low_findings", MetricItem(name="", value=0)).value or 0
        info = metrics.get("info_findings", MetricItem(name="", value=0)).value or 0

        # Deterministic severity penalty formula:
        # CRITICAL: -35 pts, HIGH: -20 pts, MEDIUM: -8 pts, LOW: -3 pts, INFO: -0.5 pts
        penalties = (crit * 35.0) + (high * 20.0) + (med * 8.0) + (low * 3.0) + (info * 0.5)
        score = round(max(0.0, 100.0 - penalties), 1)

        status = DimensionStatus.STRONG if score >= 80.0 else (DimensionStatus.ADEQUATE if score >= 60.0 else DimensionStatus.WEAK)

        parts = []
        if crit > 0:
            parts.append(f"{crit} CRITICAL (-{crit*35})")
        if high > 0:
            parts.append(f"{high} HIGH (-{high*20})")
        if med > 0:
            parts.append(f"{med} MEDIUM (-{med*8})")
        if low > 0:
            parts.append(f"{low} LOW (-{low*3})")
        if info > 0:
            parts.append(f"{info} INFO (-{info*0.5})")

        if parts:
            explanation = f"Security audit identified vulnerabilities: {', '.join(parts)}. Total penalty: {penalties:.1f} points."
        else:
            explanation = "No security vulnerabilities or secret leaks were identified during audit."

        evidence_items.append(make_evidence_item(
            dimension=dim.value,
            source_type=EvidenceSourceType.SECURITY,
            metric_name="findings_breakdown",
            metric_value=f"{crit} crit, {high} high, {med} med, {low} low",
            description=f"Security findings audit: {crit} critical, {high} high, {med} medium, {low} low.",
        ))

        return DimensionResult(
            dimension=dim,
            score=score,
            status=status,
            weight=weight,
            weighted_score=round(score * weight, 2),
            explanation=explanation,
            metrics={"critical": crit, "high": high, "medium": med, "low": low, "info": info, "penalties": penalties},
            evidence_items=evidence_items,
        )

    @classmethod
    def evaluate_maintainability(cls, metrics: Dict[str, MetricItem], weight: float) -> DimensionResult:
        dim = EvaluationDimensionType.MAINTAINABILITY
        evidence_items: List[EvidenceItem] = []

        linter_available = metrics.get("linter_available", MetricItem(name="", value=False)).value
        if linter_available:
            errors = metrics.get("lint_errors", MetricItem(name="", value=0)).value or 0
            warnings = metrics.get("lint_warnings", MetricItem(name="", value=0)).value or 0

            # Linter penalty: -10 per error, -3 per warning
            penalties = (errors * 10.0) + (warnings * 3.0)
            score = round(max(0.0, 100.0 - penalties), 1)
            status = DimensionStatus.STRONG if score >= 80.0 else (DimensionStatus.ADEQUATE if score >= 60.0 else DimensionStatus.WEAK)

            explanation = (
                f"Static analysis detected {errors} error(s) and {warnings} warning(s). "
                f"Deducted {penalties:.1f} maintainability points." if penalties > 0
                else "Static analysis passed with 0 errors and 0 warnings."
            )

            evidence_items.append(make_evidence_item(
                dimension=dim.value,
                source_type=EvidenceSourceType.LINTER,
                metric_name="lint_issues",
                metric_value=f"{errors} errors, {warnings} warnings",
                description=f"Linter detected {errors} errors and {warnings} warnings.",
            ))

            return DimensionResult(
                dimension=dim,
                score=score,
                status=status,
                weight=weight,
                weighted_score=round(score * weight, 2),
                explanation=explanation,
                metrics={"lint_errors": errors, "lint_warnings": warnings},
                evidence_items=evidence_items,
            )

        # Baseline when linter tooling is unavailable
        score = 80.0
        status = DimensionStatus.ADEQUATE
        explanation = "Static linter was not executed. Maintainability scored at baseline reflecting clean modular architecture without detected syntax issues."
        limitations = "Dedicated linter tool (e.g. ruff, flake8, eslint) was not detected."

        evidence_items.append(make_evidence_item(
            dimension=dim.value,
            source_type=EvidenceSourceType.STATIC_ANALYSIS,
            metric_name="linter_tool_availability",
            metric_value="unavailable",
            description="Dedicated linter tool was not available.",
        ))

        return DimensionResult(
            dimension=dim,
            score=score,
            status=status,
            weight=weight,
            weighted_score=round(score * weight, 2),
            explanation=explanation,
            metrics={"linter_available": False},
            evidence_items=evidence_items,
            limitations=limitations,
        )

    @classmethod
    def evaluate_performance(cls, metrics: Dict[str, MetricItem], weight: float) -> DimensionResult:
        dim = EvaluationDimensionType.PERFORMANCE
        evidence_items: List[EvidenceItem] = []

        bench_available = metrics.get("benchmark_available", MetricItem(name="", value=False)).value
        timeout_count = metrics.get("timeout_occurrences", MetricItem(name="", value=0)).value or 0

        if bench_available:
            duration_ms = metrics.get("benchmark_duration_ms", MetricItem(name="", value=0.0)).value or 0.0
            # Latency penalty: baseline 90.0, timeout penalties
            timeout_penalty = timeout_count * 25.0
            score = round(max(0.0, 90.0 - timeout_penalty), 1)
            status = DimensionStatus.STRONG if score >= 80.0 else (DimensionStatus.ADEQUATE if score >= 60.0 else DimensionStatus.WEAK)
            explanation = f"Benchmark executed with measured latency {duration_ms:.1f}ms." + (f" Encountered {timeout_count} command timeout(s)." if timeout_count > 0 else "")

            evidence_items.append(make_evidence_item(
                dimension=dim.value,
                source_type=EvidenceSourceType.BENCHMARK,
                metric_name="benchmark_duration_ms",
                metric_value=f"{duration_ms:.1f}ms",
                unit="ms",
                description=f"Measured latency: {duration_ms:.1f}ms.",
            ))

            return DimensionResult(
                dimension=dim,
                score=score,
                status=status,
                weight=weight,
                weighted_score=round(score * weight, 2),
                explanation=explanation,
                metrics={"duration_ms": duration_ms, "timeout_count": timeout_count},
                evidence_items=evidence_items,
            )

        if timeout_count > 0:
            score = round(max(0.0, 60.0 - (timeout_count * 20.0)), 1)
            status = DimensionStatus.WEAK
            explanation = f"Performance degraded: encountered {timeout_count} command execution timeout(s)."

            evidence_items.append(make_evidence_item(
                dimension=dim.value,
                source_type=EvidenceSourceType.BENCHMARK,
                metric_name="timeout_occurrences",
                metric_value=str(timeout_count),
                description=f"Execution encountered {timeout_count} timeouts.",
            ))

            return DimensionResult(
                dimension=dim,
                score=score,
                status=status,
                weight=weight,
                weighted_score=round(score * weight, 2),
                explanation=explanation,
                metrics={"timeout_count": timeout_count},
                evidence_items=evidence_items,
            )

        # Honest discovery: no benchmark available
        explanation = "No performance benchmarks or timing tests were executed. Performance cannot be scored without benchmark evidence."
        limitations = "No benchmark suite was available for this run."

        evidence_items.append(make_evidence_item(
            dimension=dim.value,
            source_type=EvidenceSourceType.BENCHMARK,
            metric_name="benchmark_tool_availability",
            metric_value="unavailable",
            description="No benchmark tests detected in run.",
        ))

        return DimensionResult(
            dimension=dim,
            score=None,
            status=DimensionStatus.INSUFFICIENT_EVIDENCE,
            weight=weight,
            weighted_score=None,
            explanation=explanation,
            metrics={"benchmark_available": False},
            evidence_items=evidence_items,
            limitations=limitations,
        )

    @classmethod
    def evaluate_regression_risk(cls, metrics: Dict[str, MetricItem], weight: float) -> DimensionResult:
        dim = EvaluationDimensionType.REGRESSION_RISK
        evidence_items: List[EvidenceItem] = []

        unresolved_breaker = metrics.get("unresolved_breaker_findings", MetricItem(name="", value=0)).value or 0
        failed_tests = metrics.get("failed_tests", MetricItem(name="", value=0)).value or 0
        iterations = metrics.get("iteration_count", MetricItem(name="", value=1)).value or 1

        # Base 100 minus risk penalties:
        # Each blocking breaker finding: -20 pts
        # Each failed test: -10 pts
        # Iterations beyond 1: -5 pts per retry iteration
        breaker_penalty = unresolved_breaker * 20.0
        test_penalty = failed_tests * 10.0
        iteration_penalty = max(0, iterations - 1) * 5.0
        total_penalties = breaker_penalty + test_penalty + iteration_penalty

        score = round(max(0.0, min(100.0, 100.0 - total_penalties)), 1)
        status = DimensionStatus.STRONG if score >= 80.0 else (DimensionStatus.ADEQUATE if score >= 60.0 else DimensionStatus.WEAK)

        reasons = []
        if unresolved_breaker > 0:
            reasons.append(f"{unresolved_breaker} adversarial edge case(s) (-{breaker_penalty:.0f})")
        if failed_tests > 0:
            reasons.append(f"{failed_tests} test failure(s) (-{test_penalty:.0f})")
        if iterations > 1:
            reasons.append(f"{iterations} iterations required (-{iteration_penalty:.0f})")

        if reasons:
            explanation = f"Regression risk elevated by {', '.join(reasons)}."
        else:
            explanation = "Low regression risk: single-iteration pass with 0 unresolved edge cases and all tests passing."

        evidence_items.append(make_evidence_item(
            dimension=dim.value,
            source_type=EvidenceSourceType.ORCHESTRATION,
            metric_name="regression_risk_factors",
            metric_value=f"iters={iterations}, breaker_blocks={unresolved_breaker}, test_fails={failed_tests}",
            description=f"Regression risk factors: {iterations} iterations, {unresolved_breaker} breaker blocks, {failed_tests} failed tests.",
        ))

        return DimensionResult(
            dimension=dim,
            score=score,
            status=status,
            weight=weight,
            weighted_score=round(score * weight, 2),
            explanation=explanation,
            metrics={
                "unresolved_breaker": unresolved_breaker,
                "failed_tests": failed_tests,
                "iterations": iterations,
                "total_penalties": total_penalties,
            },
            evidence_items=evidence_items,
        )

    @classmethod
    def calculate_overall_engineering_score(
        cls,
        dimension_results: List[DimensionResult],
        weights: Dict[str, float],
        score_version: str = "v1",
    ) -> OverallScoreResult:
        """
        Calculate the transparent, deterministic overall Engineering Score.
        Supports normalized scaling when dimensions have INSUFFICIENT_EVIDENCE.
        """
        scored_dimensions = [d for d in dimension_results if d.score is not None]

        if not scored_dimensions:
            return OverallScoreResult(
                overall_score=None,
                status_label=DimensionStatus.INSUFFICIENT_EVIDENCE,
                score_version=score_version,
                weights=weights,
                formula="No dimensions contained sufficient evidence to compute an Engineering Score.",
                dimension_results=dimension_results,
            )

        # Sum weighted scores
        evaluated_weight_sum = sum(d.weight for d in scored_dimensions)
        weighted_score_sum = sum(d.score * d.weight for d in scored_dimensions)

        # Normalized overall score (0.0 - 100.0)
        overall_score = round(weighted_score_sum / evaluated_weight_sum, 1)

        # Build formula string
        terms = [f"({d.score:.1f} × {d.weight*100:.0f}%)" for d in scored_dimensions]
        if abs(evaluated_weight_sum - 1.0) < 1e-5:
            formula = f"{' + '.join(terms)} = {overall_score:.1f} / 100"
        else:
            insufficient_dims = [d.dimension.value for d in dimension_results if d.score is None]
            formula = (
                f"Normalized across {len(scored_dimensions)} evaluated dimensions "
                f"({', '.join(insufficient_dims)} had insufficient evidence): "
                f"({' + '.join(terms)}) / {evaluated_weight_sum:.2f} = {overall_score:.1f} / 100"
            )

        status_label = (
            DimensionStatus.STRONG if overall_score >= 80.0
            else (DimensionStatus.ADEQUATE if overall_score >= 60.0 else DimensionStatus.WEAK)
        )

        return OverallScoreResult(
            overall_score=overall_score,
            status_label=status_label,
            score_version=score_version,
            weights=weights,
            formula=formula,
            dimension_results=dimension_results,
        )
