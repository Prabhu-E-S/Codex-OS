import json
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.database import SessionLocal
from backend.config import settings
from backend.models.run import EngineeringRun
from backend.models.project import Project
from backend.models.workspace import Workspace
from backend.models.sandbox import Sandbox
from backend.models.agent_execution import AgentExecution
from backend.models.finding import Finding
from backend.models.orchestration import OrchestrationState
from backend.codex.runner import CodexRunner
from backend.codex.models import RunStatus
from backend.agents.models import AgentType, AgentStatus, AgentResult
from backend.agents.context import AgentContext
from backend.agents.manager import AgentManager
from backend.orchestrator.models import (
    WorkflowState,
    OrchestratorDecision,
    OrchestrationEvent,
    DecisionResult,
)
from backend.orchestrator.state_machine import WorkflowStateMachine
from backend.orchestrator.policy import OrchestratorPolicy
from backend.orchestrator.feedback import IterationFeedbackCollector
from backend.orchestrator.exceptions import InvalidStateTransitionError

logger = logging.getLogger("codex_os.orchestrator.manager")

class OrchestratorManager:
    """
    Coordinates multi-iteration autonomous agent workflow loops.
    Orchestrates: Architect (once) -> Builder -> Tester -> Breaker -> Security -> Decision.
    Handles boundary-safe pause, resume, cancel, structured feedback propagation,
    and state persistence.
    """

    @classmethod
    def _append_event(
        cls,
        db: Session,
        orch_state: OrchestrationState,
        event_type: str,
        agent: Optional[str] = None,
        state: Optional[str] = None,
        decision: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append a structured orchestration event to the state's event log."""
        try:
            current_events = json.loads(orch_state.events_json or "[]")
        except Exception:
            current_events = []

        evt = OrchestrationEvent(
            event_type=event_type,
            run_id=orch_state.engineering_run_id,
            iteration=orch_state.iteration,
            agent=agent,
            state=state,
            decision=decision,
            reason=reason,
            details=details,
        )
        current_events.append(evt.to_dict())
        orch_state.events_json = json.dumps(current_events)
        db.commit()

    @classmethod
    def get_orchestration_state(cls, run_id: int, db: Session) -> Optional[OrchestrationState]:
        """Retrieve the persistent orchestration state for an engineering run."""
        return (
            db.query(OrchestrationState)
            .filter(OrchestrationState.engineering_run_id == run_id)
            .first()
        )

    @classmethod
    def start_autonomous_run(
        cls,
        run_id: int,
        max_iterations: int = 3,
        db: Optional[Session] = None,
        spawn_worker: bool = True
    ) -> OrchestrationState:
        """
        Initialize and launch an autonomous multi-iteration run.
        """
        owns_db = False
        if db is None:
            db = SessionLocal()
            owns_db = True

        try:
            run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
            if not run:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Engineering run with ID {run_id} not found"
                )

            # Clamp max_iterations
            limit = settings.ORCHESTRATOR_MAX_ITERATIONS_LIMIT
            max_iter = max(1, min(max_iterations, limit))

            orch_state = (
                db.query(OrchestrationState)
                .filter(OrchestrationState.engineering_run_id == run_id)
                .first()
            )

            if orch_state:
                if orch_state.state in (
                    WorkflowState.ARCHITECTING.value,
                    WorkflowState.BUILDING.value,
                    WorkflowState.TESTING.value,
                    WorkflowState.BREAKING.value,
                    WorkflowState.SECURITY_SCANNING.value,
                    WorkflowState.DECIDING.value,
                    WorkflowState.ITERATING.value,
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Run {run_id} is already actively orchestrating in state {orch_state.state}"
                    )
                # Reset existing state
                orch_state.state = WorkflowState.PENDING.value
                orch_state.iteration = 1
                orch_state.max_iterations = max_iter
                orch_state.current_agent = None
                orch_state.last_decision = None
                orch_state.last_decision_reason = None
                orch_state.pause_requested = False
                orch_state.cancel_requested = False
                orch_state.failure_reason = None
            else:
                orch_state = OrchestrationState(
                    engineering_run_id=run_id,
                    state=WorkflowState.PENDING.value,
                    iteration=1,
                    max_iterations=max_iter,
                    events_json="[]",
                )
                db.add(orch_state)

            run.status = RunStatus.STARTING.value
            run.started_at = datetime.now(timezone.utc)
            run.completed_at = None
            run.exit_code = None
            run.error_message = None
            db.commit()
            db.refresh(orch_state)

            cls._append_event(
                db=db,
                orch_state=orch_state,
                event_type="run.started",
                state=WorkflowState.PENDING.value,
                details={"max_iterations": max_iter},
            )

            if spawn_worker:
                # Launch autonomous execution in worker thread
                thread = threading.Thread(
                    target=cls._orchestration_worker,
                    args=(run_id,),
                    daemon=True
                )
                thread.start()

            return orch_state
        finally:
            if owns_db:
                db.close()

    @classmethod
    def pause_run(cls, run_id: int, db: Session) -> OrchestrationState:
        """
        Request execution pause at the nearest safe agent boundary.
        """
        orch_state = cls.get_orchestration_state(run_id, db)
        if not orch_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No orchestration state for run {run_id}"
            )

        if WorkflowStateMachine.is_terminal(orch_state.state):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pause run in terminal state {orch_state.state}"
            )

        if orch_state.state == WorkflowState.PAUSED.value:
            return orch_state

        orch_state.pause_requested = True
        db.commit()
        db.refresh(orch_state)

        cls._append_event(
            db=db,
            orch_state=orch_state,
            event_type="run.pause_requested",
            reason="Pause requested by user; will pause at nearest agent boundary."
        )
        return orch_state

    @classmethod
    def resume_run(cls, run_id: int, db: Session, spawn_worker: bool = True) -> OrchestrationState:
        """
        Resume an autonomous run from the PAUSED state.
        """
        orch_state = cls.get_orchestration_state(run_id, db)
        if not orch_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No orchestration state for run {run_id}"
            )

        if orch_state.state != WorkflowState.PAUSED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot resume run in non-paused state {orch_state.state}"
            )

        orch_state.pause_requested = False
        db.commit()
        db.refresh(orch_state)

        cls._append_event(
            db=db,
            orch_state=orch_state,
            event_type="run.resumed",
            reason="Execution resumed by user."
        )

        run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
        if run:
            run.status = RunStatus.RUNNING.value
            db.commit()

        if spawn_worker:
            # Launch worker thread to resume
            thread = threading.Thread(
                target=cls._orchestration_worker,
                args=(run_id,),
                daemon=True
            )
            thread.start()

        return orch_state

    @classmethod
    def cancel_run(cls, run_id: int, db: Session) -> OrchestrationState:
        """
        Cancel an active autonomous run.
        """
        orch_state = cls.get_orchestration_state(run_id, db)
        if not orch_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No orchestration state for run {run_id}"
            )

        # Signal cancellation
        orch_state.cancel_requested = True
        orch_state.state = WorkflowState.CANCELLED.value
        orch_state.current_agent = None

        # Terminate active codex runner process if executing
        CodexRunner.cancel_run(run_id)

        # Cancel any active or starting agent executions for this run
        active_aes = (
            db.query(AgentExecution)
            .filter(
                AgentExecution.engineering_run_id == run_id,
                AgentExecution.status.in_([AgentStatus.STARTING.value, AgentStatus.RUNNING.value, AgentStatus.PENDING.value])
            )
            .all()
        )
        for ae in active_aes:
            ae.status = AgentStatus.CANCELLED.value
            ae.completed_at = datetime.now(timezone.utc)
            ae.error_message = "Cancelled by user."

        run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
        if run:
            run.status = RunStatus.CANCELLED.value
            run.completed_at = datetime.now(timezone.utc)
            run.error_message = "Autonomous run cancelled by user."

        db.commit()
        db.refresh(orch_state)

        cls._append_event(
            db=db,
            orch_state=orch_state,
            event_type="run.cancelled",
            reason="Autonomous run cancelled by user."
        )

        return orch_state

    @classmethod
    def _execute_agent_step(
        cls,
        db: Session,
        run: EngineeringRun,
        project: Project,
        agent_type: AgentType,
        iteration: int,
        previous_results: Dict[AgentType, AgentResult],
        feedback_dict: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """
        Execute a single agent step within the current iteration and record AgentExecution.
        """
        agent_instance = AgentManager.get_agent(agent_type)

        # Look for existing record or create new
        agent_exec = AgentExecution(
            engineering_run_id=run.id,
            agent_type=agent_type.value,
            agent_name=agent_instance.name,
            iteration=iteration,
            status=AgentStatus.RUNNING.value,
            started_at=datetime.now(timezone.utc),
        )
        db.add(agent_exec)
        db.commit()
        db.refresh(agent_exec)

        # Allocate workspace / sandbox
        ws = AgentManager._allocate_agent_workspace(db, project.id, run.id, agent_type)
        if ws:
            agent_exec.workspace_id = ws.id
            ws_path = ws.path
            ws_name = ws.name
            sb = AgentManager._allocate_agent_sandbox(db, ws.id)
            if sb:
                agent_exec.sandbox_id = sb.id
        else:
            ws_path = project.repository_path
            ws_name = None

        db.commit()

        # Build context
        context = AgentContext(
            project_id=project.id,
            project_name=project.name,
            repository_path=project.repository_path,
            engineering_run_id=run.id,
            engineering_goal=run.goal,
            workspace_id=agent_exec.workspace_id,
            workspace_name=ws_name,
            workspace_path=ws_path,
            target_subpath=run.target_subpath,
            sandbox_id=agent_exec.sandbox_id,
            previous_results=previous_results,
            iteration=iteration,
            is_autonomous=True,
        )

        # Inject retry feedback if available for Builder
        if feedback_dict and agent_type == AgentType.BUILDER:
            context.tester_feedback = feedback_dict.get("tester_feedback")
            context.breaker_findings = feedback_dict.get("breaker_findings", [])
            context.security_findings = feedback_dict.get("security_findings", [])
            context.previous_failure_reason = feedback_dict.get("previous_failure_reason")
            context.orchestrator_decision = feedback_dict.get("orchestrator_decision")

        if agent_type in (AgentType.TESTER, AgentType.BREAKER, AgentType.SECURITY):
            builder_result = previous_results.get(AgentType.BUILDER)
            builder_target_path = (
                builder_result.metadata.get("working_directory")
                if builder_result and builder_result.metadata
                else None
            )
            AgentManager._sync_builder_target_to_agent_workspace(
                source_target_path=builder_target_path,
                destination_target_path=context.get_target_path(),
            )

        # Run agent
        result = agent_instance.run(context)

        # Update DB record
        agent_exec.status = result.status.value
        agent_exec.output = result.output
        agent_exec.error_message = result.error_message
        agent_exec.exit_code = result.exit_code
        agent_exec.input_summary = result.input_summary
        agent_exec.completed_at = datetime.now(timezone.utc)
        db.commit()

        # Persist findings if produced
        if result.metadata and "findings" in result.metadata:
            for f_item in result.metadata["findings"]:
                f_type = f_item.get("type") or ("BREAKER" if agent_type == AgentType.BREAKER else "SECURITY")
                finding_rec = Finding(
                    engineering_run_id=run.id,
                    agent_execution_id=agent_exec.id,
                    iteration=iteration,
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

        return result

    @classmethod
    def _orchestration_worker(cls, run_id: int, db: Optional[Session] = None) -> None:
        """
        Main autonomous execution loop running in a background thread.
        Architect (once) -> Loop: Builder -> Tester -> Breaker -> Security -> Decision.
        """
        owns_db = False
        if db is None:
            db = SessionLocal()
            owns_db = True

        try:
            run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
            if not run:
                logger.error(f"Orchestrator could not find run {run_id}")
                return

            project = db.query(Project).filter(Project.id == run.project_id).first()
            if not project:
                logger.error(f"Orchestrator could not find project for run {run_id}")
                return

            orch_state = (
                db.query(OrchestrationState)
                .filter(OrchestrationState.engineering_run_id == run_id)
                .first()
            )
            if not orch_state:
                logger.error(f"No orchestration state for run {run_id}")
                return

            run.status = RunStatus.RUNNING.value
            db.commit()

            previous_results: Dict[AgentType, AgentResult] = {}
            feedback_dict: Optional[Dict[str, Any]] = None

            # --- STEP 1: ARCHITECT (Runs once in Iteration 1) ---
            # Check if Architect has already completed in a prior session
            arch_exec = (
                db.query(AgentExecution)
                .filter(
                    AgentExecution.engineering_run_id == run_id,
                    AgentExecution.agent_type == AgentType.ARCHITECT.value,
                    AgentExecution.status == AgentStatus.COMPLETED.value
                )
                .first()
            )

            if arch_exec:
                # Architect already completed; rehydrate result
                previous_results[AgentType.ARCHITECT] = AgentResult(
                    agent_type=AgentType.ARCHITECT,
                    agent_name=arch_exec.agent_name,
                    status=AgentStatus.COMPLETED,
                    output=arch_exec.output,
                )
            else:
                # Check boundary before Architect
                db.refresh(orch_state)
                if orch_state.cancel_requested:
                    orch_state.state = WorkflowState.CANCELLED.value
                    run.status = RunStatus.CANCELLED.value
                    db.commit()
                    return

                if orch_state.pause_requested:
                    orch_state.state = WorkflowState.PAUSED.value
                    run.status = RunStatus.PAUSED.value if hasattr(RunStatus, "PAUSED") else "PAUSED"
                    db.commit()
                    return

                # Transition to ARCHITECTING
                orch_state.state = WorkflowStateMachine.transition(orch_state.state, WorkflowState.ARCHITECTING)
                orch_state.current_agent = "Architect Agent"
                db.commit()

                cls._append_event(
                    db=db,
                    orch_state=orch_state,
                    event_type="agent.started",
                    agent="Architect Agent",
                    state=WorkflowState.ARCHITECTING.value,
                )

                arch_result = cls._execute_agent_step(
                    db=db,
                    run=run,
                    project=project,
                    agent_type=AgentType.ARCHITECT,
                    iteration=1,
                    previous_results=previous_results,
                )
                previous_results[AgentType.ARCHITECT] = arch_result

                if arch_result.status != AgentStatus.COMPLETED:
                    orch_state.state = WorkflowStateMachine.transition(orch_state.state, WorkflowState.FAILED)
                    orch_state.failure_reason = f"Architect Agent failed: {arch_result.error_message}"
                    orch_state.current_agent = None
                    run.status = RunStatus.FAILED.value
                    run.error_message = orch_state.failure_reason
                    run.completed_at = datetime.now(timezone.utc)
                    db.commit()

                    cls._append_event(
                        db=db,
                        orch_state=orch_state,
                        event_type="agent.failed",
                        agent="Architect Agent",
                        reason=arch_result.error_message,
                    )
                    return

                cls._append_event(
                    db=db,
                    orch_state=orch_state,
                    event_type="agent.completed",
                    agent="Architect Agent",
                )

            # --- STEP 2: AUTONOMOUS ITERATION LOOP ---
            while orch_state.iteration <= orch_state.max_iterations:
                curr_iter = orch_state.iteration
                logger.info(f"Orchestrator starting Iteration {curr_iter}/{orch_state.max_iterations} for run {run_id}")

                cls._append_event(
                    db=db,
                    orch_state=orch_state,
                    event_type="iteration.started",
                    details={"iteration": curr_iter, "max_iterations": orch_state.max_iterations},
                )

                # --- 2A. BUILDER AGENT ---
                db.refresh(orch_state)
                if orch_state.cancel_requested:
                    orch_state.state = WorkflowState.CANCELLED.value
                    run.status = RunStatus.CANCELLED.value
                    db.commit()
                    return

                if orch_state.pause_requested:
                    orch_state.state = WorkflowState.PAUSED.value
                    run.status = "PAUSED"
                    db.commit()
                    return

                target_build_state = WorkflowState.BUILDING
                orch_state.state = WorkflowStateMachine.transition(orch_state.state, target_build_state)
                orch_state.current_agent = "Builder Agent"
                db.commit()

                cls._append_event(
                    db=db,
                    orch_state=orch_state,
                    event_type="agent.started",
                    agent="Builder Agent",
                    state=WorkflowState.BUILDING.value,
                )

                builder_res = cls._execute_agent_step(
                    db=db,
                    run=run,
                    project=project,
                    agent_type=AgentType.BUILDER,
                    iteration=curr_iter,
                    previous_results=previous_results,
                    feedback_dict=feedback_dict,
                )
                previous_results[AgentType.BUILDER] = builder_res

                if builder_res.status != AgentStatus.COMPLETED:
                    orch_state.state = WorkflowStateMachine.transition(orch_state.state, WorkflowState.FAILED)
                    orch_state.failure_reason = f"Builder Agent failed in iteration {curr_iter}: {builder_res.error_message}"
                    orch_state.current_agent = None
                    orch_state.last_decision = OrchestratorDecision.STOP_FAILURE.value
                    orch_state.last_decision_reason = orch_state.failure_reason
                    run.status = RunStatus.FAILED.value
                    run.error_message = orch_state.failure_reason
                    run.completed_at = datetime.now(timezone.utc)
                    db.commit()

                    cls._append_event(
                        db=db,
                        orch_state=orch_state,
                        event_type="agent.failed",
                        agent="Builder Agent",
                        reason=builder_res.error_message,
                    )
                    return

                cls._append_event(
                    db=db,
                    orch_state=orch_state,
                    event_type="agent.completed",
                    agent="Builder Agent",
                )

                # --- 2B. TESTER AGENT ---
                db.refresh(orch_state)
                if orch_state.cancel_requested:
                    orch_state.state = WorkflowState.CANCELLED.value
                    run.status = RunStatus.CANCELLED.value
                    db.commit()
                    return

                if orch_state.pause_requested:
                    orch_state.state = WorkflowState.PAUSED.value
                    run.status = "PAUSED"
                    db.commit()
                    return

                orch_state.state = WorkflowStateMachine.transition(orch_state.state, WorkflowState.TESTING)
                orch_state.current_agent = "Tester Agent"
                db.commit()

                cls._append_event(
                    db=db,
                    orch_state=orch_state,
                    event_type="agent.started",
                    agent="Tester Agent",
                    state=WorkflowState.TESTING.value,
                )

                tester_res = cls._execute_agent_step(
                    db=db,
                    run=run,
                    project=project,
                    agent_type=AgentType.TESTER,
                    iteration=curr_iter,
                    previous_results=previous_results,
                )
                previous_results[AgentType.TESTER] = tester_res

                cls._append_event(
                    db=db,
                    orch_state=orch_state,
                    event_type="agent.completed" if tester_res.status == AgentStatus.COMPLETED else "agent.failed",
                    agent="Tester Agent",
                    reason=tester_res.error_message,
                )

                # --- 2C. BREAKER AGENT ---
                db.refresh(orch_state)
                if orch_state.cancel_requested:
                    orch_state.state = WorkflowState.CANCELLED.value
                    run.status = RunStatus.CANCELLED.value
                    db.commit()
                    return

                if orch_state.pause_requested:
                    orch_state.state = WorkflowState.PAUSED.value
                    run.status = "PAUSED"
                    db.commit()
                    return

                orch_state.state = WorkflowStateMachine.transition(orch_state.state, WorkflowState.BREAKING)
                orch_state.current_agent = "Breaker Agent"
                db.commit()

                cls._append_event(
                    db=db,
                    orch_state=orch_state,
                    event_type="agent.started",
                    agent="Breaker Agent",
                    state=WorkflowState.BREAKING.value,
                )

                breaker_res = cls._execute_agent_step(
                    db=db,
                    run=run,
                    project=project,
                    agent_type=AgentType.BREAKER,
                    iteration=curr_iter,
                    previous_results=previous_results,
                )
                previous_results[AgentType.BREAKER] = breaker_res

                cls._append_event(
                    db=db,
                    orch_state=orch_state,
                    event_type="agent.completed",
                    agent="Breaker Agent",
                )

                # --- 2D. SECURITY AGENT ---
                db.refresh(orch_state)
                if orch_state.cancel_requested:
                    orch_state.state = WorkflowState.CANCELLED.value
                    run.status = RunStatus.CANCELLED.value
                    db.commit()
                    return

                if orch_state.pause_requested:
                    orch_state.state = WorkflowState.PAUSED.value
                    run.status = "PAUSED"
                    db.commit()
                    return

                orch_state.state = WorkflowStateMachine.transition(orch_state.state, WorkflowState.SECURITY_SCANNING)
                orch_state.current_agent = "Security Agent"
                db.commit()

                cls._append_event(
                    db=db,
                    orch_state=orch_state,
                    event_type="agent.started",
                    agent="Security Agent",
                    state=WorkflowState.SECURITY_SCANNING.value,
                )

                sec_res = cls._execute_agent_step(
                    db=db,
                    run=run,
                    project=project,
                    agent_type=AgentType.SECURITY,
                    iteration=curr_iter,
                    previous_results=previous_results,
                )
                previous_results[AgentType.SECURITY] = sec_res

                cls._append_event(
                    db=db,
                    orch_state=orch_state,
                    event_type="agent.completed",
                    agent="Security Agent",
                )

                # --- 2E. ORCHESTRATOR DECISION ---
                orch_state.state = WorkflowStateMachine.transition(orch_state.state, WorkflowState.DECIDING)
                orch_state.current_agent = None
                db.commit()

                # Collect findings from current iteration
                curr_breaker_findings = (
                    db.query(Finding)
                    .filter(
                        Finding.engineering_run_id == run_id,
                        Finding.iteration == curr_iter,
                        Finding.type == "BREAKER",
                    )
                    .all()
                )
                curr_security_findings = (
                    db.query(Finding)
                    .filter(
                        Finding.engineering_run_id == run_id,
                        Finding.iteration == curr_iter,
                        Finding.type == "SECURITY",
                    )
                    .all()
                )

                breaker_dicts = [
                    {
                        "severity": f.severity,
                        "title": f.title,
                        "description": f.description,
                        "evidence": f.evidence,
                        "reproduction": f.reproduction,
                    }
                    for f in curr_breaker_findings
                ]
                sec_dicts = [
                    {
                        "severity": f.severity,
                        "title": f.title,
                        "description": f.description,
                        "file_path": f.file_path,
                        "line_number": f.line_number,
                        "remediation": f.remediation,
                    }
                    for f in curr_security_findings
                ]

                decision = OrchestratorPolicy.evaluate(
                    iteration=curr_iter,
                    max_iterations=orch_state.max_iterations,
                    builder_result=builder_res,
                    tester_result=tester_res,
                    breaker_findings=breaker_dicts,
                    security_findings=sec_dicts,
                )

                orch_state.last_decision = decision.decision.value
                orch_state.last_decision_reason = decision.reason
                db.commit()

                cls._append_event(
                    db=db,
                    orch_state=orch_state,
                    event_type="decision.made",
                    decision=decision.decision.value,
                    reason=decision.reason,
                    details=decision.details,
                )

                # --- 2F. PROCESS DECISION ---
                if decision.decision == OrchestratorDecision.STOP_SUCCESS:
                    orch_state.state = WorkflowStateMachine.transition(orch_state.state, WorkflowState.COMPLETED)
                    run.status = RunStatus.COMPLETED.value
                    run.completed_at = datetime.now(timezone.utc)
                    run.exit_code = 0

                    arch_out = previous_results.get(AgentType.ARCHITECT, AgentResult(AgentType.ARCHITECT, "", AgentStatus.COMPLETED, "")).output
                    build_out = builder_res.output
                    test_out = tester_res.output
                    break_out = breaker_res.output
                    sec_out = sec_res.output

                    run.stdout = (
                        f"=== Codex OS Autonomous Orchestration Completed ({curr_iter} Iteration{'s' if curr_iter > 1 else ''}) ===\n\n"
                        f"## 1. ARCHITECT PLAN\n{arch_out}\n\n"
                        f"## 2. FINAL BUILDER IMPLEMENTATION (Iteration {curr_iter})\n{build_out}\n\n"
                        f"## 3. TESTER VERIFICATION\n{test_out}\n\n"
                        f"## 4. BREAKER ANALYSIS\n{break_out}\n\n"
                        f"## 5. SECURITY AUDIT REPORT\n{sec_out}\n\n"
                        f"### Decision Summary\n{decision.reason}\n"
                    )
                    db.commit()

                    cls._append_event(
                        db=db,
                        orch_state=orch_state,
                        event_type="run.completed",
                        reason=decision.reason,
                    )
                    logger.info(f"Orchestrator completed run {run_id} successfully at iteration {curr_iter}")
                    return

                elif decision.decision == OrchestratorDecision.STOP_FAILURE:
                    orch_state.state = WorkflowStateMachine.transition(orch_state.state, WorkflowState.FAILED)
                    orch_state.failure_reason = decision.reason
                    run.status = RunStatus.FAILED.value
                    run.error_message = decision.reason
                    run.completed_at = datetime.now(timezone.utc)
                    db.commit()

                    cls._append_event(
                        db=db,
                        orch_state=orch_state,
                        event_type="run.failed",
                        reason=decision.reason,
                    )
                    logger.warning(f"Orchestrator stopped run {run_id} with failure: {decision.reason}")
                    return

                elif decision.decision == OrchestratorDecision.RETRY_BUILDER:
                    # Prepare feedback for next Builder iteration
                    feedback_dict = IterationFeedbackCollector.extract_feedback(
                        iteration=curr_iter,
                        decision_reason=decision.reason,
                        tester_result=tester_res,
                        breaker_findings=breaker_dicts,
                        security_findings=sec_dicts,
                    )

                    cls._append_event(
                        db=db,
                        orch_state=orch_state,
                        event_type="iteration.completed",
                        reason=decision.reason,
                        details={"completed_iteration": curr_iter, "next_iteration": curr_iter + 1},
                    )

                    orch_state.state = WorkflowStateMachine.transition(orch_state.state, WorkflowState.ITERATING)
                    orch_state.iteration = curr_iter + 1
                    db.commit()
                    continue

        except Exception as exc:
            logger.exception(f"Unexpected error in orchestrator worker for run {run_id}: {exc}")
            try:
                orch_state = (
                    db.query(OrchestrationState)
                    .filter(OrchestrationState.engineering_run_id == run_id)
                    .first()
                )
                if orch_state and not WorkflowStateMachine.is_terminal(orch_state.state):
                    orch_state.state = WorkflowState.FAILED.value
                    orch_state.failure_reason = f"Internal orchestrator error: {exc}"

                run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
                if run and run.status not in (RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.CANCELLED.value):
                    run.status = RunStatus.FAILED.value
                    run.error_message = f"Orchestrator error: {exc}"
                    run.completed_at = datetime.now(timezone.utc)
                db.commit()
            except Exception:
                pass
        finally:
            if owns_db:
                db.close()
