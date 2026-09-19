import re
import logging
from datetime import datetime, timezone
from backend.agents.base import BaseAgent
from backend.agents.models import AgentType, AgentStatus, AgentResult
from backend.agents.context import AgentContext
from backend.agents.prompts import build_tester_prompt
from backend.codex.runner import CodexRunner
from backend.codex.models import RunStatus

logger = logging.getLogger("codex_os.agents.tester")

class TesterAgent(BaseAgent):
    """
    Tester Agent is responsible for verifying the Builder's implementation
    against the Architect's plan by identifying and executing relevant test suites.
    It does NOT modify production code and does NOT execute any Git commands.
    """
    __test__ = False
    agent_type = AgentType.TESTER
    name = "Tester Agent"
    role = "Verification & Test Execution"
    description = (
        "Verifies implementation by identifying, running, and reporting test results "
        "without modifying production files."
    )

    def run(self, context: AgentContext) -> AgentResult:
        started_at = datetime.now(timezone.utc)
        logger.info(f"Tester Agent starting for run {context.engineering_run_id}")

        # Ingest upstream Architect and Builder results
        architect_res = context.get_previous_result(AgentType.ARCHITECT)
        builder_res = context.get_previous_result(AgentType.BUILDER)

        if not builder_res or builder_res.status != AgentStatus.COMPLETED:
            err_msg = "Cannot start Tester Agent: Builder implementation is missing or was not completed successfully."
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

        prompt = build_tester_prompt(context, architect_plan, builder_summary)
        target_path = context.workspace_path or context.repository_path

        # Execute test verification via Phase 2 CodexRunner
        execution_result = CodexRunner.execute(
            run_id=context.engineering_run_id,
            goal=prompt,
            repository_path=target_path,
            project_name=context.project_name,
            timeout_seconds=context.timeout_seconds
        )

        completed_at = datetime.now(timezone.utc)

        if execution_result.status == RunStatus.COMPLETED:
            output = execution_result.stdout.strip() if execution_result.stdout else "Tests executed successfully."

            # Inspect output for explicit test failure indicators
            is_failed = False
            if re.search(r"status:\s*failed", output, re.IGNORECASE):
                is_failed = True
            elif re.search(r"failed:\s*[1-9]\d*", output, re.IGNORECASE):
                is_failed = True

            agent_status = AgentStatus.FAILED if is_failed else AgentStatus.COMPLETED
            logger.info(f"Tester Agent finished with status {agent_status} for run {context.engineering_run_id}")

            return AgentResult(
                agent_type=self.agent_type,
                agent_name=self.name,
                status=agent_status,
                output=output,
                exit_code=1 if is_failed else execution_result.exit_code,
                error_message="One or more tests failed during verification." if is_failed else None,
                started_at=started_at,
                completed_at=completed_at,
                input_summary=f"Verified Builder output ({len(builder_summary)} chars)",
                metadata={"working_directory": target_path}
            )
        else:
            error_msg = execution_result.error_message or execution_result.stderr or "Tester execution failed"
            logger.error(f"Tester Agent failed for run {context.engineering_run_id}: {error_msg}")
            return AgentResult(
                agent_type=self.agent_type,
                agent_name=self.name,
                status=AgentStatus.FAILED,
                output=execution_result.stdout or "",
                error_message=error_msg,
                exit_code=execution_result.exit_code,
                started_at=started_at,
                completed_at=completed_at,
                input_summary=f"Verified Builder output ({len(builder_summary)} chars)",
                metadata={"working_directory": target_path}
            )
