import logging
from datetime import datetime, timezone
from backend.agents.base import BaseAgent
from backend.agents.models import AgentType, AgentStatus, AgentResult
from backend.agents.context import AgentContext
from backend.agents.prompts import build_architect_prompt
from backend.codex.runner import CodexRunner
from backend.codex.models import RunStatus

logger = logging.getLogger("codex_os.agents.architect")

class ArchitectAgent(BaseAgent):
    """
    Architect Agent is responsible for analyzing the repository context and the
    engineering goal to produce a structured, actionable implementation plan.
    It does NOT modify any source files and does NOT execute any Git commands.
    """
    agent_type = AgentType.ARCHITECT
    name = "Architect Agent"
    role = "Architecture & Planning"
    description = (
        "Analyzes codebase architecture, identifies relevant files, and produces a "
        "structured implementation plan without modifying any code."
    )

    def run(self, context: AgentContext) -> AgentResult:
        started_at = datetime.now(timezone.utc)
        logger.info(f"Architect Agent starting for run {context.engineering_run_id}")

        prompt = build_architect_prompt(context)
        target_path = context.workspace_path or context.repository_path

        # Execute inspection & plan generation via Phase 2 CodexRunner
        execution_result = CodexRunner.execute(
            run_id=context.engineering_run_id,
            goal=prompt,
            repository_path=target_path,
            project_name=context.project_name,
            timeout_seconds=context.timeout_seconds
        )

        completed_at = datetime.now(timezone.utc)

        if execution_result.status == RunStatus.COMPLETED:
            output = execution_result.stdout.strip() if execution_result.stdout else "Architect plan generated."
            logger.info(f"Architect Agent completed successfully for run {context.engineering_run_id}")
            return AgentResult(
                agent_type=self.agent_type,
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                output=output,
                exit_code=execution_result.exit_code,
                started_at=started_at,
                completed_at=completed_at,
                input_summary=f"Goal: {context.engineering_goal[:120]}...",
                metadata={"working_directory": target_path}
            )
        else:
            error_msg = execution_result.error_message or execution_result.stderr or "Architect execution failed"
            logger.error(f"Architect Agent failed for run {context.engineering_run_id}: {error_msg}")
            return AgentResult(
                agent_type=self.agent_type,
                agent_name=self.name,
                status=AgentStatus.FAILED,
                output=execution_result.stdout or "",
                error_message=error_msg,
                exit_code=execution_result.exit_code,
                started_at=started_at,
                completed_at=completed_at,
                input_summary=f"Goal: {context.engineering_goal[:120]}...",
                metadata={"working_directory": target_path}
            )
