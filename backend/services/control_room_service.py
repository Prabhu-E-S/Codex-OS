import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Set
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.models.run import EngineeringRun
from backend.models.orchestration import OrchestrationState
from backend.models.agent_execution import AgentExecution
from backend.models.workspace import Workspace
from backend.models.sandbox import Sandbox
from backend.models.finding import Finding
from backend.models.evaluation import Evaluation
from backend.services.execution_service import ExecutionService
from backend.evaluation.evidence import redact_sensitive_text
from backend.schemas.control_room import (
    ControlRoomSnapshotResponse,
    ControlRoomRun,
    ControlRoomOrchestration,
    ControlRoomAgent,
    ControlRoomIteration,
    ControlRoomIterationAgentSummary,
    ControlRoomWorkspace,
    ControlRoomSandbox,
    ControlRoomFinding,
    ControlRoomFindingsSummary,
    ControlRoomEvaluation,
    ControlRoomDimension,
    ControlRoomEvent,
    ControlRoomLogs,
)


def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class ControlRoomService:
    @staticmethod
    def sanitize_workspace_path(path: Optional[str]) -> str:
        """
        Sanitize an absolute filesystem path to a safe project-relative representation.
        Prevents leaking private host directories, usernames, or absolute mount structures.
        """
        if not path:
            return "workspaces/unassigned"
        normalized = path.replace("\\", "/")
        # Extract relative path from workspaces/ onwards if present
        if "/workspaces/" in normalized:
            idx = normalized.index("/workspaces/")
            return normalized[idx + 1:]
        parts = normalized.strip("/").split("/")
        return f"workspaces/{parts[-1]}" if parts else "workspaces/default"

    @classmethod
    def get_snapshot(cls, run_id: int, db: Session) -> ControlRoomSnapshotResponse:
        """
        Aggregate a comprehensive, read-only snapshot of an engineering run for the Control Room.
        Purely observational: performs zero state mutations and zero Git operations.
        """
        run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Engineering run with ID {run_id} not found"
            )

        project_name = run.project.name if run.project else f"Project #{run.project_id}"
        orch = run.orchestration_state

        # Calculate run duration with timezone-safe UTC normalization
        now = datetime.now(timezone.utc)
        duration_seconds: Optional[float] = None
        started_utc = _to_utc(run.started_at)
        completed_utc = _to_utc(run.completed_at)
        if started_utc:
            end_time = completed_utc or now
            duration_seconds = max(0.0, (end_time - started_utc).total_seconds())

        # Determine execution mode and current iteration
        mode = "AUTONOMOUS" if orch is not None else "MANUAL"
        current_iteration = orch.iteration if orch else 1
        max_iterations = orch.max_iterations if orch else 1

        # 1. Run Metadata
        run_data = ControlRoomRun(
            id=run.id,
            project_id=run.project_id,
            project_name=project_name,
            status=run.status,
            goal=run.goal,
            mode=mode,
            iteration=current_iteration,
            max_iterations=max_iterations,
            started_at=run.started_at,
            completed_at=run.completed_at,
            duration_seconds=duration_seconds,
            exit_code=run.exit_code,
            error_message=run.error_message,
            workspace_id=run.workspace_id,
            workspace_name=run.workspace_name,
            sandbox_id=run.sandbox_id,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

        # 2. Orchestration State
        orch_data: Optional[ControlRoomOrchestration] = None
        events_list: List[ControlRoomEvent] = []
        if orch:
            is_active = orch.state not in ("COMPLETED", "FAILED", "CANCELLED")
            orch_data = ControlRoomOrchestration(
                state=orch.state,
                current_agent=orch.current_agent,
                iteration=orch.iteration,
                max_iterations=orch.max_iterations,
                last_decision=orch.last_decision,
                last_decision_reason=orch.last_decision_reason,
                failure_reason=orch.failure_reason,
                pause_requested=orch.pause_requested,
                cancel_requested=orch.cancel_requested,
                is_active=is_active,
            )

            # Parse orchestration events
            try:
                raw_events = json.loads(orch.events_json or "[]")
                for evt in raw_events:
                    events_list.append(
                        ControlRoomEvent(
                            timestamp=evt.get("timestamp", ""),
                            event_type=evt.get("event_type", "UNKNOWN"),
                            iteration=evt.get("iteration", 1),
                            agent=evt.get("agent"),
                            state=evt.get("state"),
                            decision=evt.get("decision"),
                            reason=evt.get("reason"),
                            details=evt.get("details"),
                        )
                    )
            except Exception:
                events_list = []

        # 3. Agent Executions
        agents_data: List[ControlRoomAgent] = []
        seen_workspace_ids: Set[int] = set()
        seen_sandbox_ids: Set[int] = set()

        if run.workspace_id:
            seen_workspace_ids.add(run.workspace_id)
        if run.sandbox_id:
            seen_sandbox_ids.add(run.sandbox_id)

        for ae in run.agent_executions:
            if ae.workspace_id:
                seen_workspace_ids.add(ae.workspace_id)
            if ae.sandbox_id:
                seen_sandbox_ids.add(ae.sandbox_id)

            agent_duration: Optional[float] = None
            ae_started_utc = _to_utc(ae.started_at)
            ae_completed_utc = _to_utc(ae.completed_at)
            if ae_started_utc:
                agent_end = ae_completed_utc or now
                agent_duration = max(0.0, (agent_end - ae_started_utc).total_seconds())

            # Count findings for this execution
            f_count = len(ae.findings) if ae.findings else 0

            # Redact sensitive output in agent output
            sanitized_output = redact_sensitive_text(ae.output or "")

            agents_data.append(
                ControlRoomAgent(
                    id=ae.id,
                    agent_type=ae.agent_type,
                    agent_name=ae.agent_name,
                    status=ae.status,
                    iteration=ae.iteration,
                    workspace_id=ae.workspace_id,
                    workspace_name=ae.workspace_name,
                    sandbox_id=ae.sandbox_id,
                    sandbox_status=ae.sandbox.status if ae.sandbox else None,
                    started_at=ae.started_at,
                    completed_at=ae.completed_at,
                    duration_seconds=agent_duration,
                    input_summary=ae.input_summary,
                    output=sanitized_output or "",
                    error_message=ae.error_message,
                    exit_code=ae.exit_code,
                    findings_count=f_count,
                )
            )

        # 4. Iteration Groupings
        max_iter_found = 1
        if orch:
            max_iter_found = max(max_iter_found, orch.iteration)
        if agents_data:
            max_iter_found = max(max_iter_found, max(a.iteration for a in agents_data))

        iterations_data: List[ControlRoomIteration] = []
        for i in range(1, max_iter_found + 1):
            iter_agents = [a for a in agents_data if a.iteration == i]
            iter_findings_count = sum(a.findings_count for a in iter_agents)

            # Find iteration decision from events or current orch
            iter_decision: Optional[str] = None
            iter_reason: Optional[str] = None

            # Check events for a decision logged in iteration i
            for evt in reversed(events_list):
                if evt.iteration == i and evt.decision:
                    iter_decision = evt.decision
                    iter_reason = evt.reason
                    break

            if not iter_decision and orch and orch.iteration == i and orch.state in ("DECIDING", "COMPLETED", "FAILED", "CANCELLED"):
                iter_decision = orch.last_decision
                iter_reason = orch.last_decision_reason

            # Determine iteration status
            if (orch and orch.iteration == i and is_active) or any(a.status == "RUNNING" for a in iter_agents):
                iter_status = "RUNNING"
            elif iter_decision == "STOP_SUCCESS":
                iter_status = "COMPLETED"
            elif iter_decision == "STOP_FAILURE":
                iter_status = "FAILED"
            elif iter_decision == "RETRY_BUILDER":
                iter_status = "RETRYING"
            elif any(a.status == "FAILED" for a in iter_agents):
                iter_status = "FAILED"
            elif iter_agents and all(a.status == "COMPLETED" for a in iter_agents):
                iter_status = "COMPLETED"
            else:
                iter_status = "COMPLETED" if run.status == "COMPLETED" else "RUNNING"

            agent_summaries = [
                ControlRoomIterationAgentSummary(
                    agent_type=a.agent_type,
                    agent_name=a.agent_name,
                    status=a.status,
                    duration_seconds=a.duration_seconds,
                    findings_count=a.findings_count,
                )
                for a in iter_agents
            ]

            iterations_data.append(
                ControlRoomIteration(
                    iteration_number=i,
                    status=iter_status,
                    agents=agent_summaries,
                    decision=iter_decision,
                    decision_reason=iter_reason,
                    findings_count=iter_findings_count,
                )
            )

        # 5. Workspaces
        workspaces_data: List[ControlRoomWorkspace] = []
        if seen_workspace_ids:
            workspaces = db.query(Workspace).filter(Workspace.id.in_(seen_workspace_ids)).all()
            for ws in workspaces:
                workspaces_data.append(
                    ControlRoomWorkspace(
                        id=ws.id,
                        name=ws.name,
                        branch_name=ws.branch_name,
                        relative_path=cls.sanitize_workspace_path(ws.path),
                        status=ws.status,
                    )
                )

        # 6. Sandboxes
        sandboxes_data: List[ControlRoomSandbox] = []
        if seen_sandbox_ids:
            sandboxes = db.query(Sandbox).filter(Sandbox.id.in_(seen_sandbox_ids)).all()
            for sb in sandboxes:
                c_id_preview = sb.container_id[:12] if sb.container_id else None
                sandboxes_data.append(
                    ControlRoomSandbox(
                        id=sb.id,
                        workspace_id=sb.workspace_id,
                        image=sb.image,
                        status=sb.status,
                        container_id_preview=c_id_preview,
                        cpu_limit=sb.cpu_limit,
                        memory_limit=sb.memory_limit,
                        timeout_seconds=sb.timeout_seconds,
                        exit_code=sb.exit_code,
                        started_at=sb.started_at,
                        stopped_at=sb.stopped_at,
                    )
                )

        # 7. Findings & Summary
        findings_data: List[ControlRoomFinding] = []
        summary_severities: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        summary_types: Dict[str, int] = {"BREAKER": 0, "SECURITY": 0}
        open_count = 0
        resolved_count = 0

        for f in run.findings:
            summary_severities[f.severity] = summary_severities.get(f.severity, 0) + 1
            summary_types[f.type] = summary_types.get(f.type, 0) + 1
            if f.status == "RESOLVED":
                resolved_count += 1
            else:
                open_count += 1

            sanitized_evidence = redact_sensitive_text(f.evidence or "")
            agent_type = f.agent_execution.agent_type if f.agent_execution else None

            findings_data.append(
                ControlRoomFinding(
                    id=f.id,
                    type=f.type,
                    severity=f.severity,
                    category=f.category,
                    title=f.title,
                    description=f.description,
                    file_path=f.file_path,
                    line_number=f.line_number,
                    evidence=sanitized_evidence,
                    reproduction=f.reproduction,
                    remediation=f.remediation,
                    status=f.status,
                    iteration=f.iteration,
                    resolved_iteration=getattr(f, "resolved_iteration", None),
                    resolved_at=getattr(f, "resolved_at", None),
                    agent_type=agent_type,
                    created_at=f.created_at,
                )
            )

        findings_summary = ControlRoomFindingsSummary(
            total=len(findings_data),
            by_severity=summary_severities,
            by_type=summary_types,
            open=open_count,
            resolved=resolved_count,
        )

        # 8. Evaluation (Latest)
        evaluation_data: Optional[ControlRoomEvaluation] = None
        if run.evaluations:
            latest_eval: Evaluation = run.evaluations[0]
            dims = [
                ControlRoomDimension(
                    dimension=d.dimension,
                    score=d.score,
                    status=d.status,
                    weight=d.weight,
                    weighted_score=d.weighted_score,
                    explanation=d.explanation,
                    limitations=d.limitations,
                )
                for d in latest_eval.dimensions
            ]

            evaluation_data = ControlRoomEvaluation(
                id=latest_eval.id,
                status=latest_eval.status,
                overall_score=latest_eval.overall_score,
                status_label=latest_eval.status_label,
                score_version=latest_eval.score_version,
                formula=latest_eval.formula,
                summary=latest_eval.summary,
                strengths=latest_eval.strengths,
                weaknesses=latest_eval.weaknesses,
                limitations=latest_eval.limitations,
                dimensions=dims,
                evaluated_at=latest_eval.completed_at,
            )

        # 9. Logs (stdout/stderr sanitized)
        raw_logs = ExecutionService.get_run_logs(run_id, db)
        raw_stdout = raw_logs.get("stdout", "") or ""
        raw_stderr = raw_logs.get("stderr", "") or ""

        clean_stdout = redact_sensitive_text(raw_stdout) or ""
        clean_stderr = redact_sensitive_text(raw_stderr) or ""
        total_lines = (clean_stdout.count("\n") + 1 if clean_stdout else 0) + (
            clean_stderr.count("\n") + 1 if clean_stderr else 0
        )

        logs_data = ControlRoomLogs(
            stdout=clean_stdout,
            stderr=clean_stderr,
            exit_code=run.exit_code,
            total_lines=total_lines,
        )

        # Limit recent events to latest 50
        recent_events = events_list[-50:] if len(events_list) > 50 else events_list

        return ControlRoomSnapshotResponse(
            run=run_data,
            orchestration=orch_data,
            agents=agents_data,
            iterations=iterations_data,
            workspaces=workspaces_data,
            sandboxes=sandboxes_data,
            findings=findings_data,
            findings_summary=findings_summary,
            evaluation=evaluation_data,
            recent_events=recent_events,
            logs=logs_data,
        )
