import re
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from backend.agents.base import BaseAgent
from backend.agents.models import AgentType, AgentStatus, AgentResult
from backend.agents.context import AgentContext
from backend.agents.prompts import build_breaker_prompt
from backend.codex.runner import CodexRunner
from backend.codex.models import RunStatus

logger = logging.getLogger("codex_os.agents.breaker")

class BreakerAgent(BaseAgent):
    """
    Breaker Agent is responsible for adversarial testing and discovering weaknesses
    in the Builder's implementation.
    It identifies edge cases, boundary conditions, malformed inputs, and invalid states,
    executes targeted tests inside the sandbox, and produces structured evidence-backed findings.
    It does NOT modify production code and does NOT execute any Git commands.
    """
    agent_type = AgentType.BREAKER
    name = "Breaker Agent"
    role = "Adversarial Testing & Weakness Discovery"
    description = (
        "Attacks the implementation through safe, controlled adversarial tests inside the "
        "sandbox to discover edge cases and weaknesses without modifying production code."
    )

    def run(self, context: AgentContext) -> AgentResult:
        started_at = datetime.now(timezone.utc)
        logger.info(f"Breaker Agent starting for run {context.engineering_run_id}")

        # Ingest upstream results
        architect_res = context.get_previous_result(AgentType.ARCHITECT)
        builder_res = context.get_previous_result(AgentType.BUILDER)
        tester_res = context.get_previous_result(AgentType.TESTER)

        if not builder_res or builder_res.status != AgentStatus.COMPLETED:
            err_msg = "Cannot start Breaker Agent: Builder implementation is missing or was not completed successfully."
            logger.error(err_msg)
            return AgentResult(
                agent_type=self.agent_type,
                agent_name=self.name,
                status=AgentStatus.FAILED,
                output="",
                error_message=err_msg,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                input_summary="Builder output unavailable."
            )

        architect_plan = architect_res.output if architect_res else "No plan provided."
        builder_summary = builder_res.output
        tester_output = tester_res.output if tester_res else "Tester output unavailable."

        prompt = build_breaker_prompt(context, architect_plan, builder_summary, tester_output)
        target_path = context.workspace_path or context.repository_path

        # Execute adversarial analysis via Phase 2 CodexRunner
        execution_result = CodexRunner.execute(
            run_id=context.engineering_run_id,
            goal=prompt,
            repository_path=target_path,
            project_name=context.project_name,
            timeout_seconds=context.timeout_seconds
        )

        completed_at = datetime.now(timezone.utc)

        if execution_result.status == RunStatus.COMPLETED:
            output = execution_result.stdout.strip() if execution_result.stdout else "Adversarial testing completed."

            # Parse structured findings from output
            findings = self._extract_findings(output)
            test_counts = self._extract_test_counts(output)

            logger.info(
                f"Breaker Agent finished successfully for run {context.engineering_run_id} "
                f"with {len(findings)} findings discovered."
            )

            metadata: Dict[str, Any] = {
                "working_directory": target_path,
                "findings": findings,
                "test_counts": test_counts,
                "findings_count": len(findings),
            }

            return AgentResult(
                agent_type=self.agent_type,
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                output=output,
                exit_code=execution_result.exit_code,
                error_message=None,
                started_at=started_at,
                completed_at=completed_at,
                input_summary=f"Analyzed Builder implementation ({len(builder_summary)} chars) and Tester output",
                metadata=metadata
            )
        else:
            error_msg = execution_result.error_message or execution_result.stderr or "Breaker execution failed"
            logger.error(f"Breaker Agent failed for run {context.engineering_run_id}: {error_msg}")
            return AgentResult(
                agent_type=self.agent_type,
                agent_name=self.name,
                status=AgentStatus.FAILED,
                output=execution_result.stdout or "",
                error_message=error_msg,
                exit_code=execution_result.exit_code,
                started_at=started_at,
                completed_at=completed_at,
                input_summary=f"Analyzed Builder implementation ({len(builder_summary)} chars)",
                metadata={"working_directory": target_path, "findings": []}
            )

    def _extract_findings(self, text: str) -> List[Dict[str, Any]]:
        """Extract structured finding objects from text or JSON blocks."""
        findings: List[Dict[str, Any]] = []

        # 1. Search for JSON block
        json_matches = re.findall(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text)
        for block in json_matches:
            try:
                data = json.loads(block)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "title" in item:
                            sev = str(item.get("severity", "MEDIUM")).upper()
                            if sev not in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]:
                                sev = "MEDIUM"
                            cat = str(item.get("category", "EDGE_CASE")).upper()
                            findings.append({
                                "type": "BREAKER",
                                "severity": sev,
                                "category": cat,
                                "title": item.get("title", "Adversarial finding"),
                                "description": item.get("description", "Discovered potential failure condition."),
                                "file_path": item.get("file_path"),
                                "line_number": item.get("line_number"),
                                "evidence": item.get("evidence"),
                                "reproduction": item.get("reproduction"),
                                "remediation": item.get("remediation"),
                            })
            except json.JSONDecodeError:
                pass

        return findings

    def _extract_test_counts(self, text: str) -> Dict[str, int]:
        counts = {"generated": 0, "executed": 0, "passed": 0, "failed": 0}
        gen = re.search(r"tests?\s+generated:\s*(\d+)", text, re.IGNORECASE)
        if gen:
            counts["generated"] = int(gen.group(1))
        exe = re.search(r"tests?\s+executed:\s*(\d+)", text, re.IGNORECASE)
        if exe:
            counts["executed"] = int(exe.group(1))
        pas = re.search(r"tests?\s+passed:\s*(\d+)", text, re.IGNORECASE)
        if pas:
            counts["passed"] = int(pas.group(1))
        fai = re.search(r"tests?\s+failed:\s*(\d+)", text, re.IGNORECASE)
        if fai:
            counts["failed"] = int(fai.group(1))
        return counts
