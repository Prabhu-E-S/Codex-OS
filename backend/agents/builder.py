import logging
from datetime import datetime, timezone
from backend.agents.base import BaseAgent
from backend.agents.models import AgentType, AgentStatus, AgentResult
from backend.agents.context import AgentContext
from backend.agents.prompts import build_builder_prompt, build_builder_retry_prompt
from backend.codex.runner import CodexRunner
from backend.codex.models import RunStatus

logger = logging.getLogger("codex_os.agents.builder")

class BuilderAgent(BaseAgent):
    """
    Builder Agent is responsible for executing code modifications inside its
    assigned isolated workspace based on the Architect Agent's plan.
    It does NOT modify the primary project repository and does NOT run Git commands.
    """
    agent_type = AgentType.BUILDER
    name = "Builder Agent"
    role = "Code Implementation"
    description = (
        "Implements code modifications inside an isolated workspace following the "
        "Architect's plan without touching the primary repository."
    )

    def run(self, context: AgentContext) -> AgentResult:
        started_at = datetime.now(timezone.utc)
        logger.info(f"Builder Agent starting for run {context.engineering_run_id} (iteration {context.iteration})")

        # Ingest upstream Architect result
        architect_result = context.get_previous_result(AgentType.ARCHITECT)
        if not architect_result or architect_result.status != AgentStatus.COMPLETED:
            err_msg = "Cannot start Builder Agent: Architect plan is missing or was not completed successfully."
            logger.error(err_msg)
            return AgentResult(
                agent_type=self.agent_type,
                agent_name=self.name,
                status=AgentStatus.FAILED,
                output="",
                error_message=err_msg,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                input_summary="Architect plan unavailable."
            )

        architect_plan = architect_result.output
        if context.iteration > 1 or context.tester_feedback or context.breaker_findings or context.security_findings:
            prompt = build_builder_retry_prompt(context, architect_plan)
        else:
            prompt = build_builder_prompt(context, architect_plan)
        target_path = context.workspace_path or context.repository_path

        # Execute code implementation via Phase 2 CodexRunner inside assigned workspace
        execution_result = CodexRunner.execute(
            run_id=context.engineering_run_id,
            goal=prompt,
            repository_path=target_path,
            project_name=context.project_name,
            timeout_seconds=context.timeout_seconds
        )

        completed_at = datetime.now(timezone.utc)

        if execution_result.status == RunStatus.COMPLETED:
            output = execution_result.stdout.strip() if execution_result.stdout else "Implementation changes completed."
            logger.info(f"Builder Agent completed successfully for run {context.engineering_run_id}")
            return AgentResult(
                agent_type=self.agent_type,
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                output=output,
                exit_code=execution_result.exit_code,
                started_at=started_at,
                completed_at=completed_at,
                input_summary=f"Plan from Architect ({len(architect_plan)} chars)",
                metadata={"working_directory": target_path}
            )
        else:
            error_msg = execution_result.error_message or execution_result.stderr or "Builder execution failed"
            logger.error(f"Builder Agent failed for run {context.engineering_run_id}: {error_msg}")
            return AgentResult(
                agent_type=self.agent_type,
                agent_name=self.name,
                status=AgentStatus.FAILED,
                output=execution_result.stdout or "",
                error_message=error_msg,
                exit_code=execution_result.exit_code,
                started_at=started_at,
                completed_at=completed_at,
                input_summary=f"Plan from Architect ({len(architect_plan)} chars)",
                metadata={"working_directory": target_path}
            )
