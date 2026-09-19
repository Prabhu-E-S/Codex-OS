import logging
from typing import Dict, Any, List, Optional
from backend.agents.models import AgentResult, AgentStatus
from backend.models.finding import Finding

logger = logging.getLogger("codex_os.orchestrator.feedback")

class IterationFeedbackCollector:
    """
    Extracts and compiles structured feedback from Tester, Breaker, and Security
    agents from a completed iteration to inject into the Builder Agent's context.
    """

    @classmethod
    def extract_feedback(
        cls,
        iteration: int,
        decision_reason: str,
        tester_result: Optional[AgentResult] = None,
        breaker_findings: Optional[List[Dict[str, Any]]] = None,
        security_findings: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Compile dictionary of feedback for next Builder Agent iteration.
        """
        tester_feedback_str: Optional[str] = None
        if tester_result and tester_result.status != AgentStatus.COMPLETED:
            parts = []
            if tester_result.error_message:
                parts.append(f"Error: {tester_result.error_message}")
            if tester_result.output:
                # Truncate very long test outputs to most informative tail
                out = tester_result.output.strip()
                if len(out) > 2000:
                    out = "... [truncated] ...\n" + out[-2000:]
                parts.append(f"Output:\n{out}")
            tester_feedback_str = "\n".join(parts) if parts else "Test execution failed."

        return {
            "iteration": iteration + 1,
            "previous_failure_reason": decision_reason,
            "tester_feedback": tester_feedback_str,
            "breaker_findings": breaker_findings or [],
            "security_findings": security_findings or [],
            "orchestrator_decision": "RETRY_BUILDER",
        }
