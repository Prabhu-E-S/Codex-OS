import logging
from typing import List, Dict, Any, Optional
from backend.agents.models import AgentResult, AgentStatus
from backend.orchestrator.models import OrchestratorDecision, DecisionResult

logger = logging.getLogger("codex_os.orchestrator.policy")

class OrchestratorPolicy:
    """
    Deterministic decision engine for autonomous orchestration.
    Evaluates execution outcomes from Builder, Tester, Breaker, and Security agents.
    Does NOT calculate any numerical scores or weighted evaluation metrics (Phase 8).
    Produces transparent, human-readable explanations for all decisions.
    """

    BLOCKING_SEVERITIES = {"CRITICAL", "HIGH"}

    @classmethod
    def evaluate(
        cls,
        iteration: int,
        max_iterations: int,
        builder_result: Optional[AgentResult] = None,
        tester_result: Optional[AgentResult] = None,
        breaker_findings: Optional[List[Dict[str, Any]]] = None,
        security_findings: Optional[List[Dict[str, Any]]] = None,
        agent_failure: Optional[str] = None,
    ) -> DecisionResult:
        """
        Evaluate factual agent outcomes to decide next orchestration action:
        - STOP_FAILURE: unrecoverable crash, Builder failure, or iteration limit exceeded.
        - RETRY_BUILDER: test failure or HIGH/CRITICAL finding discovered (if iteration < max).
        - STOP_SUCCESS: all tests passed and no blocking findings exist.
        """
        breaker_findings = breaker_findings or []
        security_findings = security_findings or []

        # 1. Check for unhandled agent failure / crash
        if agent_failure:
            return DecisionResult(
                decision=OrchestratorDecision.STOP_FAILURE,
                reason=f"Stopping execution due to agent failure: {agent_failure}",
                details={"agent_failure": agent_failure}
            )

        # 2. Check Builder execution result
        if not builder_result or builder_result.status != AgentStatus.COMPLETED:
            err = builder_result.error_message if builder_result else "Builder did not execute"
            return DecisionResult(
                decision=OrchestratorDecision.STOP_FAILURE,
                reason=f"Stopping execution because Builder failed: {err}",
                details={"builder_error": err}
            )

        # 3. Check Tester verification result
        tester_failed = False
        tester_failure_reason = ""
        if not tester_result or tester_result.status != AgentStatus.COMPLETED:
            tester_failed = True
            tester_failure_reason = (
                tester_result.error_message
                if tester_result and tester_result.error_message
                else "Tester verification reported test failures"
            )

        # 4. Count blocking findings (CRITICAL, HIGH)
        blocking_breaker = [
            f for f in breaker_findings
            if str(f.get("severity", "")).upper() in cls.BLOCKING_SEVERITIES
        ]
        blocking_security = [
            f for f in security_findings
            if str(f.get("severity", "")).upper() in cls.BLOCKING_SEVERITIES
        ]
        total_blocking = len(blocking_breaker) + len(blocking_security)

        # 5. Check if any issues exist
        has_blocking_issues = tester_failed or total_blocking > 0

        # Check iteration limit if blocking issues exist
        if has_blocking_issues:
            if iteration >= max_iterations:
                reasons = []
                if tester_failed:
                    reasons.append(f"Tester reported failure ({tester_failure_reason})")
                if blocking_breaker:
                    reasons.append(f"{len(blocking_breaker)} HIGH/CRITICAL Breaker finding(s)")
                if blocking_security:
                    reasons.append(f"{len(blocking_security)} HIGH/CRITICAL Security vulnerability(ies)")

                reason_str = "; ".join(reasons)
                return DecisionResult(
                    decision=OrchestratorDecision.STOP_FAILURE,
                    reason=f"Stopping because maximum iteration limit ({max_iterations}) was reached with unresolved issues: {reason_str}",
                    blocking_findings_count=total_blocking,
                    test_failed=tester_failed,
                    details={
                        "iteration": iteration,
                        "max_iterations": max_iterations,
                        "unresolved_reasons": reasons,
                    }
                )

            # Retry Builder with specific feedback
            reasons = []
            if tester_failed:
                reasons.append(f"Tester reported failing cases ({tester_failure_reason})")
            if blocking_breaker:
                reasons.append(f"Breaker reported {len(blocking_breaker)} HIGH/CRITICAL issue(s)")
            if blocking_security:
                reasons.append(f"Security reported {len(blocking_security)} HIGH/CRITICAL vulnerability(ies)")

            reason_str = " and ".join(reasons)
            return DecisionResult(
                decision=OrchestratorDecision.RETRY_BUILDER,
                reason=f"Retrying Builder because {reason_str}.",
                blocking_findings_count=total_blocking,
                test_failed=tester_failed,
                details={
                    "iteration": iteration,
                    "next_iteration": iteration + 1,
                    "blocking_breaker_count": len(blocking_breaker),
                    "blocking_security_count": len(blocking_security),
                }
            )

        # 6. No blocking issues -> Success!
        info_count = len(breaker_findings) + len(security_findings)
        if info_count > 0:
            reason = f"Stopping with success: All tests passed and remaining {info_count} non-blocking finding(s) are acceptable."
        else:
            reason = "Stopping with success: All tests passed and no findings were detected."

        return DecisionResult(
            decision=OrchestratorDecision.STOP_SUCCESS,
            reason=reason,
            blocking_findings_count=0,
            test_failed=False,
            details={
                "iteration": iteration,
                "total_findings": info_count,
            }
        )
