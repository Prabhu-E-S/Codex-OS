import re
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from backend.agents.base import BaseAgent
from backend.agents.models import AgentType, AgentStatus, AgentResult
from backend.agents.context import AgentContext
from backend.agents.prompts import build_judge_prompt
from backend.codex.runner import CodexRunner
from backend.codex.models import RunStatus
from backend.evaluation.models import JudgeOutput, DimensionResult, MetricItem
from backend.models.finding import Finding

logger = logging.getLogger("codex_os.agents.judge")

class JudgeAgent(BaseAgent):
    """
    Judge / Evaluator Agent.
    Synthesizes qualitative assessments (summary, strengths, weaknesses, limitations,
    dimension notes) strictly from real collected evidence.
    CRITICAL: Has no authority to alter or assign numerical scores.
    """
    agent_type = AgentType.JUDGE
    name = "Judge Agent"
    role = "Qualitative Evidence Synthesis & Interpretation"
    description = (
        "Qualitatively interprets engineering evidence, synthesizing strengths, weaknesses, "
        "and limitations without modifying code and without numerical score authority."
    )

    def run(self, context: AgentContext) -> AgentResult:
        """Standard BaseAgent execution interface."""
        started_at = datetime.now(timezone.utc)
        logger.info(f"Judge Agent starting for run {context.engineering_run_id}")

        output_text = "Judge Agent executed qualitative evaluation."
        return AgentResult(
            agent_type=self.agent_type,
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            output=output_text,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            input_summary=f"Evaluated engineering goal: {context.engineering_goal[:80]}..."
        )

    def synthesize(
        self,
        engineering_goal: str,
        metrics: Dict[str, MetricItem],
        dimension_results: List[DimensionResult],
        findings: List[Finding],
        working_dir: Optional[str] = None,
    ) -> JudgeOutput:
        """
        Synthesize qualitative insights from deterministic metrics and evidence.
        Produces structured summary, verified strengths, verified weaknesses,
        honest limitations, and dimension notes.
        """
        # Format metrics summary
        metric_lines = []
        for name, item in metrics.items():
            val_str = f"{item.value}{item.unit or ''}" if item.value is not None else "unavailable"
            metric_lines.append(f"- {name}: {val_str} ({item.description or ''})")
        metrics_summary = "\n".join(metric_lines)

        # Format dimension results summary
        dim_lines = []
        for d in dimension_results:
            score_str = f"{d.score:.1f}/100" if d.score is not None else "INSUFFICIENT_EVIDENCE"
            dim_lines.append(f"- {d.dimension.value}: {score_str} [{d.status.value}] (weight: {d.weight*100:.0f}%) — {d.explanation}")
        dimension_summary = "\n".join(dim_lines)

        # Format findings summary
        finding_lines = []
        for f in findings:
            finding_lines.append(f"- [{f.type}] [{f.severity}] {f.title}: {f.description[:100]}...")
        findings_summary = "\n".join(finding_lines) if finding_lines else "No adversarial or security findings reported."

        # If Codex runner is available and working_dir is provided, attempt LLM interpretation
        if CodexRunner.is_available() and working_dir:
            try:
                prompt = build_judge_prompt(
                    engineering_goal=engineering_goal,
                    metrics_summary=metrics_summary,
                    dimension_summary=dimension_summary,
                    findings_summary=findings_summary,
                )
                runner = CodexRunner(working_directory=working_dir, timeout_seconds=120)
                exec_res = runner.execute(prompt)
                if exec_res.status == RunStatus.COMPLETED and exec_res.stdout:
                    parsed = self._parse_judge_json(exec_res.stdout)
                    if parsed:
                        return parsed
            except Exception as e:
                logger.warning(f"CodexRunner qualitative synthesis skipped: {e}")

        # Fallback to deterministic qualitative synthesis based directly on real evidence
        return self._generate_evidence_based_synthesis(
            engineering_goal=engineering_goal,
            metrics=metrics,
            dimension_results=dimension_results,
            findings=findings,
        )

    def _parse_judge_json(self, raw_output: str) -> Optional[JudgeOutput]:
        """Extract and validate Judge JSON structure from model output."""
        try:
            # Search for JSON block
            json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw_output)
            json_str = json_match.group(1) if json_match else raw_output.strip()
            data = json.loads(json_str)

            if isinstance(data, dict) and "summary" in data:
                return JudgeOutput(
                    summary=str(data.get("summary", "")),
                    strengths=[str(s) for s in data.get("strengths", [])],
                    weaknesses=[str(w) for w in data.get("weaknesses", [])],
                    limitations=[str(l) for l in data.get("limitations", [])],
                    dimension_notes={str(k): str(v) for k, v in data.get("dimension_notes", {}).items()},
                )
        except Exception as exc:
            logger.warning(f"Could not parse Judge output as JSON: {exc}")
        return None

    def _generate_evidence_based_synthesis(
        self,
        engineering_goal: str,
        metrics: Dict[str, MetricItem],
        dimension_results: List[DimensionResult],
        findings: List[Finding],
    ) -> JudgeOutput:
        """
        Produce transparent, evidence-backed qualitative synthesis without relying on an external model.
        """
        strengths: List[str] = []
        weaknesses: List[str] = []
        limitations: List[str] = []
        dimension_notes: Dict[str, str] = {}

        # 1. Correctness
        total_tests = metrics.get("total_tests", MetricItem(name="", value=0)).value or 0
        passed_tests = metrics.get("passed_tests", MetricItem(name="", value=0)).value or 0
        failed_tests = metrics.get("failed_tests", MetricItem(name="", value=0)).value or 0
        if total_tests > 0:
            if failed_tests == 0:
                strengths.append(f"All {passed_tests} automated tests passed successfully with 100% pass rate.")
                dimension_notes["CORRECTNESS"] = f"Complete automated test suite passed ({passed_tests}/{total_tests})."
            else:
                weaknesses.append(f"{failed_tests} out of {total_tests} tests failed during verification.")
                dimension_notes["CORRECTNESS"] = f"Test suite experienced {failed_tests} failure(s) out of {total_tests}."
        else:
            limitations.append("No automated test suite evidence was detected in the run output.")
            dimension_notes["CORRECTNESS"] = "Correctness could not be verified by automated tests."

        # 2. Coverage
        cov_avail = metrics.get("coverage_available", MetricItem(name="", value=False)).value
        if cov_avail:
            line_cov = metrics.get("line_coverage", MetricItem(name="", value=0.0)).value or 0.0
            if line_cov >= 80.0:
                strengths.append(f"High code test coverage achieved: {line_cov}%.")
            else:
                weaknesses.append(f"Test coverage is moderate or low: {line_cov}%.")
            dimension_notes["TEST_COVERAGE"] = f"Automated line coverage is {line_cov}%."
        else:
            limitations.append("Code coverage tool (e.g. pytest-cov, jest coverage) was not available.")
            dimension_notes["TEST_COVERAGE"] = "Coverage metrics unavailable."

        # 3. Security
        crit = metrics.get("critical_findings", MetricItem(name="", value=0)).value or 0
        high = metrics.get("high_findings", MetricItem(name="", value=0)).value or 0
        med = metrics.get("medium_findings", MetricItem(name="", value=0)).value or 0
        if crit == 0 and high == 0:
            strengths.append("Zero critical or high severity security vulnerabilities detected.")
            dimension_notes["SECURITY"] = "Clean security audit with no blocking vulnerabilities."
        else:
            weaknesses.append(f"Security audit discovered {crit} critical and {high} high severity vulnerabilities.")
            dimension_notes["SECURITY"] = f"Urgent security remediations needed for {crit + high} blocking vulnerabilities."
        if med > 0:
            weaknesses.append(f"Identified {med} medium severity security finding(s).")

        # 4. Maintainability
        linter_avail = metrics.get("linter_available", MetricItem(name="", value=False)).value
        if linter_avail:
            lint_errs = metrics.get("lint_errors", MetricItem(name="", value=0)).value or 0
            if lint_errs == 0:
                strengths.append("Static code analysis passed with 0 linter errors.")
                dimension_notes["MAINTAINABILITY"] = "Clean static analysis."
            else:
                weaknesses.append(f"Detected {lint_errs} static analysis / linter error(s).")
                dimension_notes["MAINTAINABILITY"] = f"Linter detected {lint_errs} error(s)."
        else:
            limitations.append("Dedicated static linter (ruff, eslint) was not executed.")
            dimension_notes["MAINTAINABILITY"] = "Estimated based on architectural modularity."

        # 5. Performance
        bench_avail = metrics.get("benchmark_available", MetricItem(name="", value=False)).value
        timeout_cnt = metrics.get("timeout_occurrences", MetricItem(name="", value=0)).value or 0
        if bench_avail:
            dur = metrics.get("benchmark_duration_ms", MetricItem(name="", value=0.0)).value or 0.0
            strengths.append(f"Verified performance benchmark executed with latency {dur:.1f}ms.")
            dimension_notes["PERFORMANCE"] = f"Measured latency: {dur:.1f}ms."
        elif timeout_cnt > 0:
            weaknesses.append(f"Execution experienced {timeout_cnt} command timeout(s).")
            dimension_notes["PERFORMANCE"] = f"{timeout_cnt} timeout(s) encountered."
        else:
            limitations.append("No benchmark suite or latency tests were executed.")
            dimension_notes["PERFORMANCE"] = "Performance metrics unavailable."

        # 6. Regression Risk
        iters = metrics.get("iteration_count", MetricItem(name="", value=1)).value or 1
        unres_breaker = metrics.get("unresolved_breaker_findings", MetricItem(name="", value=0)).value or 0
        if iters == 1 and unres_breaker == 0 and failed_tests == 0:
            strengths.append("Single-pass implementation with zero regression indicators.")
            dimension_notes["REGRESSION_RISK"] = "Low regression risk."
        else:
            if iters > 1:
                weaknesses.append(f"Required {iters} autonomous iterations to resolve implementation issues.")
            if unres_breaker > 0:
                weaknesses.append(f"{unres_breaker} adversarial edge cases were reported by Breaker Agent.")
            dimension_notes["REGRESSION_RISK"] = f"Regression risk elevated by {iters} iterations and {unres_breaker} edge case(s)."

        # Executive summary
        summary = (
            f"Evaluation for engineering goal: \"{engineering_goal}\". "
            + (f"Implementation validated with {passed_tests}/{total_tests} passing tests. " if total_tests > 0 else "No automated tests executed. ")
            + (f"Identified {len(findings)} total findings across security and breaker audits. " if findings else "Zero security or adversarial findings. ")
            + f"Completed across {iters} iteration(s)."
        )

        return JudgeOutput(
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
            limitations=limitations,
            dimension_notes=dimension_notes,
        )
