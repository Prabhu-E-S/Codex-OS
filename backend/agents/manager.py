import logging
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.database import SessionLocal
from backend.models.run import EngineeringRun
from backend.models.project import Project
from backend.models.workspace import Workspace
from backend.models.sandbox import Sandbox
from backend.models.agent_execution import AgentExecution
from backend.models.finding import Finding
from backend.codex.runner import CodexRunner
from backend.codex.models import RunStatus
from backend.workspace.manager import WorkspaceManager
from backend.workspace.models import WorkspaceStatus
from backend.sandbox.manager import SandboxManager
from backend.sandbox.models import SandboxStatus
from backend.agents.models import AgentType, AgentStatus, AgentResult
from backend.agents.context import AgentContext
from backend.agents.base import BaseAgent
from backend.agents.architect import ArchitectAgent
from backend.agents.builder import BuilderAgent
from backend.agents.tester import TesterAgent
from backend.agents.breaker import BreakerAgent
from backend.agents.security import SecurityAgent
from backend.agents.exceptions import AgentWorkflowError

logger = logging.getLogger("codex_os.agents.manager")

class AgentManager:
    """
    Coordinates the sequential Codex OS Agent Team workflow:
    Architect -> Builder -> Tester.
    Enforces strict agent isolation (distinct workspaces and sandboxes),
    persists step-by-step outputs, and halts immediately on failure (no retries).
    """

    _agents: Dict[AgentType, BaseAgent] = {
        AgentType.ARCHITECT: ArchitectAgent(),
        AgentType.BUILDER: BuilderAgent(),
        AgentType.TESTER: TesterAgent(),
        AgentType.BREAKER: BreakerAgent(),
        AgentType.SECURITY: SecurityAgent(),
    }

    @classmethod
    def get_agent(cls, agent_type: AgentType) -> BaseAgent:
        agent = cls._agents.get(agent_type)
        if not agent:
            raise AgentWorkflowError(f"Agent with type {agent_type} not registered.")
        return agent

    @classmethod
    def initialize_agent_executions(cls, db: Session, run_id: int) -> List[AgentExecution]:
        """
        Ensure AgentExecution records exist for all 5 agents in the workflow.
        If already present, returns the existing list ordered by execution sequence.
        """
        existing = (
            db.query(AgentExecution)
            .filter(AgentExecution.engineering_run_id == run_id)
            .order_by(AgentExecution.id.asc())
            .all()
        )
        if existing:
            return existing

        created = []
        sequence = [
            (AgentType.ARCHITECT, "Architect Agent"),
            (AgentType.BUILDER, "Builder Agent"),
            (AgentType.TESTER, "Tester Agent"),
            (AgentType.BREAKER, "Breaker Agent"),
            (AgentType.SECURITY, "Security Agent"),
        ]

        for a_type, a_name in sequence:
            record = AgentExecution(
                engineering_run_id=run_id,
                agent_type=a_type.value,
                agent_name=a_name,
                status=AgentStatus.PENDING.value,
                output="",
            )
            db.add(record)
            created.append(record)

        db.commit()
        for rec in created:
            db.refresh(rec)

        return created

    @classmethod
    def _allocate_agent_workspace(
        cls, db: Session, project_id: int, run_id: int, agent_type: AgentType
    ) -> Optional[Workspace]:
        """
        Allocate a dedicated, isolated workspace for this agent.
        Guarantees that agents never share a writable worktree.
        """
        clean_type = agent_type.value.lower()
        ws_name = f"run{run_id}-{clean_type}"

        # Check if workspace already exists
        existing = (
            db.query(Workspace)
            .filter(
                Workspace.project_id == project_id,
                Workspace.name == ws_name,
                Workspace.deleted_at.is_(None),
            )
            .first()
        )
        if existing:
            return existing

        try:
            ws = WorkspaceManager.create_workspace(
                db=db,
                project_id=project_id,
                name=ws_name,
            )
            return ws
        except Exception as exc:
            logger.warning(
                f"Failed to provision isolated worktree workspace for {clean_type} (run {run_id}): {exc}"
            )
            return None

    @classmethod
    def _allocate_agent_sandbox(
        cls, db: Session, workspace_id: Optional[int]
    ) -> Optional[Sandbox]:
        """
        Allocate a dedicated Docker sandbox bound to the agent's workspace.
        """
        if not workspace_id:
            return None

        try:
            sb = SandboxManager.create_sandbox(db=db, workspace_id=workspace_id)
            return sb
        except Exception as exc:
            logger.warning(
                f"Could not provision container sandbox for workspace {workspace_id}: {exc}"
            )
            return None

    @classmethod
    def start_workflow(cls, run_id: int, db: Session) -> EngineeringRun:
        """
        Initialize the agent team records and spawn the sequential execution worker in background.
        """
        run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Engineering run with ID {run_id} not found"
            )

        project = db.query(Project).filter(Project.id == run.project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project for run {run_id} not found"
            )

        if run.status in (RunStatus.STARTING.value, RunStatus.RUNNING.value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Run {run_id} is already executing with status {run.status}"
            )

        # Initialize agent execution rows in PENDING state
        cls.initialize_agent_executions(db, run.id)

        # Update run to STARTING
        run.status = RunStatus.STARTING.value
        run.started_at = datetime.now(timezone.utc)
        run.completed_at = None
        run.exit_code = None
        run.error_message = None
        run.stdout = ""
        run.stderr = ""
        db.commit()
        db.refresh(run)

        # Launch worker thread
        thread = threading.Thread(
            target=cls._workflow_worker,
            args=(run.id,),
            daemon=True
        )
        thread.start()

        return run

    @classmethod
    def _workflow_worker(cls, run_id: int, db: Optional[Session] = None) -> None:
        """
        Sequential execution loop: Architect -> Builder -> Tester.
        Halted immediately if any agent fails (NO RETRY).
        """
        owns_db = False
        if db is None:
            db = SessionLocal()
            owns_db = True
        try:
            run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
            if not run:
                logger.error(f"Agent workflow worker could not locate run {run_id}")
                return

            project = db.query(Project).filter(Project.id == run.project_id).first()
            if not project:
                logger.error(f"Agent workflow worker could not locate project for run {run_id}")
                return

            # Ensure all 3 agents are pre-initialized in PENDING state
            cls.initialize_agent_executions(db, run_id)

            run.status = RunStatus.RUNNING.value
            db.commit()

            agent_sequence = [
                AgentType.ARCHITECT,
                AgentType.BUILDER,
                AgentType.TESTER,
                AgentType.BREAKER,
                AgentType.SECURITY,
            ]

            previous_results: Dict[AgentType, AgentResult] = {}
            workflow_failed = False

            for agent_type in agent_sequence:
                # Check if cancelled
                db.refresh(run)
                if run.status == RunStatus.CANCELLED.value:
                    logger.info(f"Workflow for run {run_id} was cancelled before {agent_type.value}")
                    break

                agent_instance = cls.get_agent(agent_type)
                agent_exec = (
                    db.query(AgentExecution)
                    .filter(
                        AgentExecution.engineering_run_id == run_id,
                        AgentExecution.agent_type == agent_type.value,
                    )
                    .first()
                )
                if not agent_exec:
                    agent_exec = AgentExecution(
                        engineering_run_id=run_id,
                        agent_type=agent_type.value,
                        agent_name=agent_instance.name,
                        status=AgentStatus.PENDING.value,
                    )
                    db.add(agent_exec)
                    db.commit()
                    db.refresh(agent_exec)

                # Provision dedicated, isolated workspace for this agent
                ws = cls._allocate_agent_workspace(db, project.id, run_id, agent_type)
                if ws:
                    agent_exec.workspace_id = ws.id
                    ws_path = ws.path
                    ws_name = ws.name
                    # Provision container sandbox bound to this workspace
                    sb = cls._allocate_agent_sandbox(db, ws.id)
                    if sb:
                        agent_exec.sandbox_id = sb.id
                else:
                    ws_path = project.repository_path
                    ws_name = None

                agent_exec.status = AgentStatus.RUNNING.value
                agent_exec.started_at = datetime.now(timezone.utc)
                db.commit()

                context = AgentContext(
                    project_id=project.id,
                    project_name=project.name,
                    repository_path=project.repository_path,
                    engineering_run_id=run.id,
                    engineering_goal=run.goal,
                    workspace_id=agent_exec.workspace_id,
                    workspace_name=ws_name,
                    workspace_path=ws_path,
                    sandbox_id=agent_exec.sandbox_id,
                    previous_results=previous_results,
                )

                # Execute the agent
                result = agent_instance.run(context)
                previous_results[agent_type] = result

                # Update database record
                agent_exec.status = result.status.value
                agent_exec.output = result.output
                agent_exec.error_message = result.error_message
                agent_exec.exit_code = result.exit_code
                agent_exec.input_summary = result.input_summary
                agent_exec.completed_at = datetime.now(timezone.utc)
                db.commit()

                # Persist any findings generated by Breaker or Security agents
                if result.metadata and "findings" in result.metadata:
                    for f_item in result.metadata["findings"]:
                        f_type = f_item.get("type") or ("BREAKER" if agent_type == AgentType.BREAKER else "SECURITY")
                        finding_rec = Finding(
                            engineering_run_id=run_id,
                            agent_execution_id=agent_exec.id,
                            type=f_type,
                            severity=f_item.get("severity", "MEDIUM"),
                            category=f_item.get("category", "OTHER"),
                            title=f_item.get("title", "Finding"),
                            description=f_item.get("description", ""),
                            file_path=f_item.get("file_path"),
                            line_number=f_item.get("line_number"),
                            evidence=f_item.get("evidence"),
                            reproduction=f_item.get("reproduction"),
                            remediation=f_item.get("remediation"),
                            status="OPEN",
                        )
                        db.add(finding_rec)
                    db.commit()

                # If the agent failed, stop the entire workflow immediately
                if result.status != AgentStatus.COMPLETED:
                    workflow_failed = True
                    logger.warning(
                        f"{agent_type.value} Agent failed in run {run_id}. Halting workflow (no retry)."
                    )
                    run.status = RunStatus.FAILED.value
                    run.completed_at = datetime.now(timezone.utc)
                    run.error_message = (
                        f"{agent_instance.name} failed: {result.error_message or 'Execution failed'}"
                    )
                    db.commit()
                    break

            if not workflow_failed and run.status != RunStatus.CANCELLED.value:
                # All agents completed successfully
                run.status = RunStatus.COMPLETED.value
                run.completed_at = datetime.now(timezone.utc)
                run.exit_code = 0

                arch_out = previous_results.get(AgentType.ARCHITECT, AgentResult(AgentType.ARCHITECT, "", AgentStatus.COMPLETED, "")).output
                build_out = previous_results.get(AgentType.BUILDER, AgentResult(AgentType.BUILDER, "", AgentStatus.COMPLETED, "")).output
                test_out = previous_results.get(AgentType.TESTER, AgentResult(AgentType.TESTER, "", AgentStatus.COMPLETED, "")).output
                breaker_out = previous_results.get(AgentType.BREAKER, AgentResult(AgentType.BREAKER, "", AgentStatus.COMPLETED, "")).output
                sec_out = previous_results.get(AgentType.SECURITY, AgentResult(AgentType.SECURITY, "", AgentStatus.COMPLETED, "")).output

                run.stdout = (
                    "=== Codex OS Autonomous Agent Team Workflow Completed ===\n\n"
                    f"## 1. ARCHITECT PLAN\n{arch_out}\n\n"
                    f"## 2. BUILDER IMPLEMENTATION\n{build_out}\n\n"
                    f"## 3. TESTER VERIFICATION\n{test_out}\n\n"
                    f"## 4. BREAKER ADVERSARIAL ANALYSIS\n{breaker_out}\n\n"
                    f"## 5. SECURITY AUDIT REPORT\n{sec_out}\n"
                )
                db.commit()
                logger.info(f"Agent workflow for run {run_id} completed successfully with all 5 agents.")

        except Exception as exc:
            logger.exception(f"Unexpected exception in agent workflow for run {run_id}: {exc}")
            try:
                run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
                if run:
                    run.status = RunStatus.FAILED.value
                    run.completed_at = datetime.now(timezone.utc)
                    run.error_message = f"Agent workflow error: {exc}"
                    db.commit()
            except Exception:
                pass
        finally:
            if owns_db:
                db.close()

    @classmethod
    def cancel_workflow(cls, run_id: int, db: Session) -> EngineeringRun:
        """
        Cancel an active agent workflow, terminating active runner processes
        and marking all active/pending agents as CANCELLED.
        """
        run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Engineering run with ID {run_id} not found"
            )

        # Stop active process
        CodexRunner.cancel_run(run_id)

        # Cancel uncompleted agent executions
        agent_execs = (
            db.query(AgentExecution)
            .filter(AgentExecution.engineering_run_id == run_id)
            .all()
        )
        for ae in agent_execs:
            if ae.status in (AgentStatus.PENDING.value, AgentStatus.RUNNING.value, AgentStatus.STARTING.value):
                ae.status = AgentStatus.CANCELLED.value
                ae.completed_at = datetime.now(timezone.utc)
                if not ae.error_message:
                    ae.error_message = "Cancelled by user."

        run.status = RunStatus.CANCELLED.value
        run.completed_at = datetime.now(timezone.utc)
        run.error_message = "Agent workflow cancelled by user."
        db.commit()
        db.refresh(run)
        return run
