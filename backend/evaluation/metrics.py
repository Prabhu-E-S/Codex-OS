import re
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.models.run import EngineeringRun
from backend.models.agent_execution import AgentExecution
from backend.models.finding import Finding
from backend.models.orchestration import OrchestrationState
from backend.evaluation.models import MetricItem

logger = logging.getLogger("codex_os.evaluation.metrics")

class MetricCollector:
    """
    Collects measurable metrics and evidence across the entire lifecycle of an EngineeringRun.
    Discovers tool outputs honestly, distinguishes missing evidence from zero, and tracks
    test pass rates, coverage, security severities, maintainability signals, and regression risk.
    """

    @classmethod
    def collect_run_metrics(
        cls,
        run: EngineeringRun,
        agent_executions: List[AgentExecution],
        findings: List[Finding],
        orchestration_state: Optional[OrchestrationState] = None,
    ) -> Dict[str, MetricItem]:
        metrics: Dict[str, MetricItem] = {}

        # 1. Basic Run Lifecycle Metrics
        metrics["run_status"] = MetricItem(
            name="run_status",
            value=run.status,
            source="RUN",
            description="Lifecycle status of the engineering run",
        )
        metrics["run_exit_code"] = MetricItem(
            name="run_exit_code",
            value=run.exit_code,
            source="RUN",
            description="Exit code of the run execution",
        )

        duration_seconds = None
        if run.started_at and run.completed_at:
            duration_seconds = max(0.0, (run.completed_at - run.started_at).total_seconds())
        metrics["run_duration_seconds"] = MetricItem(
            name="run_duration_seconds",
            value=duration_seconds,
            unit="s",
            source="RUN",
            available=duration_seconds is not None,
            description="Total run execution time",
        )

        # 2. Agent Execution Breakdown
        agents_by_type: Dict[str, List[AgentExecution]] = {}
        for ae in agent_executions:
            agents_by_type.setdefault(ae.agent_type, []).append(ae)

        metrics["total_agent_executions"] = MetricItem(
            name="total_agent_executions",
            value=len(agent_executions),
            source="AGENT_EXECUTION",
            description="Total number of agent executions across all iterations",
        )

        # Builder metrics
        builder_execs = agents_by_type.get("BUILDER", [])
        final_builder = builder_execs[-1] if builder_execs else None
        builder_completed = final_builder.status == "COMPLETED" if final_builder else False
        metrics["builder_completed"] = MetricItem(
            name="builder_completed",
            value=builder_completed,
            source="BUILDER",
            description="Whether the Builder agent completed implementation successfully",
        )

        # Tester metrics (Test pass / fail)
        tester_execs = agents_by_type.get("TESTER", [])
        final_tester = tester_execs[-1] if tester_execs else None

        test_data = cls._extract_test_metrics(final_tester)
        metrics["tests_available"] = MetricItem(
            name="tests_available",
            value=test_data["available"],
            source="TESTER",
            description="Whether automated test results were detected",
        )
        metrics["total_tests"] = MetricItem(
            name="total_tests",
            value=test_data["total"],
            source="TESTER",
            available=test_data["available"],
            description="Total number of tests executed",
        )
        metrics["passed_tests"] = MetricItem(
            name="passed_tests",
            value=test_data["passed"],
            source="TESTER",
            available=test_data["available"],
            description="Number of passing tests",
        )
        metrics["failed_tests"] = MetricItem(
            name="failed_tests",
            value=test_data["failed"],
            source="TESTER",
            available=test_data["available"],
            description="Number of failing tests",
        )
        metrics["test_pass_rate"] = MetricItem(
            name="test_pass_rate",
            value=test_data["pass_rate"],
            unit="%",
            source="TESTER",
            available=test_data["available"],
            description="Percentage of automated tests that passed",
        )
        metrics["test_duration_seconds"] = MetricItem(
            name="test_duration_seconds",
            value=test_data["duration"],
            unit="s",
            source="TESTER",
            available=test_data["duration"] is not None,
            description="Test execution duration",
        )

        # 3. Test Coverage Metrics (Honest discovery)
        coverage_data = cls._extract_coverage_metrics(final_tester, run)
        metrics["coverage_available"] = MetricItem(
            name="coverage_available",
            value=coverage_data["available"],
            source="COVERAGE",
            description="Whether test coverage tooling and reports were available",
        )
        metrics["line_coverage"] = MetricItem(
            name="line_coverage",
            value=coverage_data["line_coverage"],
            unit="%",
            source="COVERAGE",
            available=coverage_data["available"],
            description="Code line coverage percentage",
        )
        metrics["branch_coverage"] = MetricItem(
            name="branch_coverage",
            value=coverage_data["branch_coverage"],
            unit="%",
            source="COVERAGE",
            available=coverage_data["branch_coverage"] is not None,
            description="Branch coverage percentage if supported by tool",
        )

        # 4. Security Findings & Scanner Metrics
        finding_stats = cls._aggregate_findings(findings)
        for key, val in finding_stats.items():
            metrics[key] = MetricItem(
                name=key,
                value=val,
                source="SECURITY",
                description=f"Security/Breaker finding metric: {key}",
            )

        # 5. Maintainability & Linter Metrics (Honest discovery)
        linter_data = cls._extract_linter_metrics(final_builder, run)
        metrics["linter_available"] = MetricItem(
            name="linter_available",
            value=linter_data["available"],
            source="LINTER",
            description="Whether static linter / code analysis tooling was available",
        )
        metrics["lint_errors"] = MetricItem(
            name="lint_errors",
            value=linter_data["errors"],
            source="LINTER",
            available=linter_data["available"],
            description="Number of linter / static analysis errors",
        )
        metrics["lint_warnings"] = MetricItem(
            name="lint_warnings",
            value=linter_data["warnings"],
            source="LINTER",
            available=linter_data["available"],
            description="Number of linter / static analysis warnings",
        )

        # 6. Performance & Benchmark Metrics
        perf_data = cls._extract_performance_metrics(final_tester, run)
        metrics["benchmark_available"] = MetricItem(
            name="benchmark_available",
            value=perf_data["available"],
            source="BENCHMARK",
            description="Whether meaningful performance benchmarks or timing tests were available",
        )
        metrics["benchmark_duration_ms"] = MetricItem(
            name="benchmark_duration_ms",
            value=perf_data["duration_ms"],
            unit="ms",
            source="BENCHMARK",
            available=perf_data["available"],
            description="Benchmark or timing measurement in milliseconds",
        )
        metrics["timeout_occurrences"] = MetricItem(
            name="timeout_occurrences",
            value=perf_data["timeout_count"],
            source="BENCHMARK",
            description="Number of command timeouts encountered during execution",
        )

        # 7. Regression Risk & Iteration History
        iterations = orchestration_state.iteration if orchestration_state else 1
        metrics["iteration_count"] = MetricItem(
            name="iteration_count",
            value=iterations,
            source="ORCHESTRATION",
            description="Number of engineering iterations executed",
        )
        metrics["unresolved_breaker_findings"] = MetricItem(
            name="unresolved_breaker_findings",
            value=finding_stats.get("breaker_high_critical_count", 0),
            source="BREAKER",
            description="Number of blocking adversarial edge cases identified",
        )

        return metrics

    @classmethod
    def _extract_test_metrics(cls, tester_execution: Optional[AgentExecution]) -> Dict[str, Any]:
        """Extract test pass/fail counts from TesterAgent output or metadata."""
        default_res = {
            "available": False,
            "total": 0,
            "passed": 0,
            "failed": 0,
            "pass_rate": None,
            "duration": None,
        }
        if not tester_execution or not tester_execution.output:
            return default_res

        output = tester_execution.output

        # Match pytest style: "48 passed, 2 failed in 3.45s" or "50 passed in 1.20s"
        pytest_match = re.search(r"(\d+)\s+passed(?:,\s+(\d+)\s+failed)?(?:[^\n]*in\s+([\d\.]+)s)?", output, re.IGNORECASE)
        if pytest_match:
            passed = int(pytest_match.group(1))
            failed = int(pytest_match.group(2) or 0)
            duration = float(pytest_match.group(3)) if pytest_match.group(3) else None
            total = passed + failed
            pass_rate = round((passed / total) * 100.0, 2) if total > 0 else 0.0
            return {
                "available": True,
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": pass_rate,
                "duration": duration,
            }

        # Match "Tests: 48 passed, 50 total" or "X/Y passed"
        frac_match = re.search(r"(\d+)\s*/\s*(\d+)\s+tests?\s+passed", output, re.IGNORECASE)
        if frac_match:
            passed = int(frac_match.group(1))
            total = int(frac_match.group(2))
            failed = max(0, total - passed)
            pass_rate = round((passed / total) * 100.0, 2) if total > 0 else 0.0
            return {
                "available": True,
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": pass_rate,
                "duration": None,
            }

        # Check if output contains explicit test success/failure indications
        if "all tests passed" in output.lower() or "tests passed successfully" in output.lower():
            return {
                "available": True,
                "total": 1,
                "passed": 1,
                "failed": 0,
                "pass_rate": 100.0,
                "duration": None,
            }

        return default_res

    @classmethod
    def _extract_coverage_metrics(cls, tester_execution: Optional[AgentExecution], run: EngineeringRun) -> Dict[str, Any]:
        """Discover coverage tooling output honestly. Does not fabricate percentages."""
        default_res = {
            "available": False,
            "line_coverage": None,
            "branch_coverage": None,
        }
        candidates = []
        if tester_execution and tester_execution.output:
            candidates.append(tester_execution.output)
        if run.stdout:
            candidates.append(run.stdout)

        combined = "\n".join(candidates)

        # Match coverage regex e.g. "TOTAL ... 82%" or "Coverage: 74.5%"
        cov_match = re.search(r"(?:TOTAL|coverage|line\s+coverage)[^\n%]*?(\d+(?:\.\d+)?)\s*%", combined, re.IGNORECASE)
        if cov_match:
            try:
                line_cov = float(cov_match.group(1))
                line_cov = max(0.0, min(100.0, line_cov))
                return {
                    "available": True,
                    "line_coverage": line_cov,
                    "branch_coverage": None,
                }
            except ValueError:
                pass

        return default_res

    @classmethod
    def _aggregate_findings(cls, findings: List[Finding]) -> Dict[str, Any]:
        """
        Aggregate Breaker and Security findings across severities.
        Resolved findings are retained for historical audit, but only active
        unresolved findings contribute to security/regression penalties.
        """
        resolved_count = sum(1 for f in findings if (f.status or "OPEN").upper() == "RESOLVED")
        active_findings = [f for f in findings if (f.status or "OPEN").upper() != "RESOLVED"]

        stats = {
            "total_findings": len(findings),
            "open_findings": len(active_findings),
            "resolved_findings": resolved_count,
            "critical_findings": 0,
            "high_findings": 0,
            "medium_findings": 0,
            "low_findings": 0,
            "info_findings": 0,
            "breaker_findings_count": 0,
            "security_findings_count": 0,
            "breaker_high_critical_count": 0,
            "security_high_critical_count": 0,
        }
        for f in active_findings:
            sev = (f.severity or "").upper()
            ftype = (f.type or "").upper()

            if sev == "CRITICAL":
                stats["critical_findings"] += 1
            elif sev == "HIGH":
                stats["high_findings"] += 1
            elif sev == "MEDIUM":
                stats["medium_findings"] += 1
            elif sev == "LOW":
                stats["low_findings"] += 1
            elif sev == "INFO":
                stats["info_findings"] += 1

            if ftype == "BREAKER":
                stats["breaker_findings_count"] += 1
                if sev in ("CRITICAL", "HIGH"):
                    stats["breaker_high_critical_count"] += 1
            elif ftype == "SECURITY":
                stats["security_findings_count"] += 1
                if sev in ("CRITICAL", "HIGH"):
                    stats["security_high_critical_count"] += 1

        return stats

    @classmethod
    def _extract_linter_metrics(cls, builder_execution: Optional[AgentExecution], run: EngineeringRun) -> Dict[str, Any]:
        """Discover static linter output (ruff, eslint, flake8) honestly."""
        default_res = {
            "available": False,
            "errors": 0,
            "warnings": 0,
        }
        combined = ""
        if builder_execution and builder_execution.output:
            combined += builder_execution.output + "\n"
        if run.stdout:
            combined += run.stdout + "\n"

        # Match ruff/eslint style: "Found 2 errors, 5 warnings" or "X lint errors"
        lint_match = re.search(r"found\s+(\d+)\s+errors?(?:,\s+(\d+)\s+warnings?)?", combined, re.IGNORECASE)
        if lint_match:
            errors = int(lint_match.group(1))
            warnings = int(lint_match.group(2) or 0)
            return {"available": True, "errors": errors, "warnings": warnings}

        clean_match = re.search(r"(?:all checks passed|0 errors|clean code|no issues found)", combined, re.IGNORECASE)
        if clean_match and ("lint" in combined.lower() or "ruff" in combined.lower() or "flake8" in combined.lower()):
            return {"available": True, "errors": 0, "warnings": 0}

        return default_res

    @classmethod
    def _extract_performance_metrics(cls, tester_execution: Optional[AgentExecution], run: EngineeringRun) -> Dict[str, Any]:
        """Discover performance benchmark or latency measurements honestly."""
        default_res = {
            "available": False,
            "duration_ms": None,
            "timeout_count": 0,
        }
        combined = ""
        if tester_execution and tester_execution.output:
            combined += tester_execution.output + "\n"
        if run.stdout:
            combined += run.stdout + "\n"
        if run.stderr:
            combined += run.stderr + "\n"

        timeout_count = combined.lower().count("timed out") + combined.lower().count("timeout error")
        default_res["timeout_count"] = timeout_count

        # Check for benchmark timing e.g. "Benchmark: 142ms" or "Mean latency: 45.2 ms"
        bench_match = re.search(r"(?:benchmark|latency|response\s+time)[^\n\d]*?(\d+(?:\.\d+)?)\s*(ms|s)", combined, re.IGNORECASE)
        if bench_match:
            val = float(bench_match.group(1))
            unit = bench_match.group(2).lower()
            duration_ms = val if unit == "ms" else val * 1000.0
            return {
                "available": True,
                "duration_ms": duration_ms,
                "timeout_count": timeout_count,
            }

        return default_res
