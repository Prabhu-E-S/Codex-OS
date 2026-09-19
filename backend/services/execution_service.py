import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.database import SessionLocal
from backend.models.run import EngineeringRun
from backend.models.project import Project
from backend.models.workspace import Workspace
from backend.models.sandbox import Sandbox
from backend.workspace.models import WorkspaceStatus
from backend.sandbox.models import SandboxStatus
from backend.sandbox.manager import SandboxManager
from backend.codex.runner import CodexRunner
from backend.codex.models import RunStatus
from backend.codex.process import process_manager

logger = logging.getLogger("codex_os.execution")

class ExecutionService:
    @staticmethod
    def start_execution(run_id: int, db: Session) -> EngineeringRun:
        """
        Validate prerequisites, set status to STARTING, and launch execution asynchronously.
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
                detail=f"Run {run_id} is already active with status {run.status}"
            )

        # Transition status to STARTING
        run.status = RunStatus.STARTING.value
        run.started_at = datetime.now(timezone.utc)
        run.completed_at = None
        run.exit_code = None
        run.stdout = ""
        run.stderr = ""
        run.error_message = None
        db.commit()
        db.refresh(run)

        # Spawn execution in a background thread to avoid blocking API response
        thread = threading.Thread(
            target=ExecutionService._execute_worker,
            args=(run.id, project.repository_path, run.goal, project.name),
            daemon=True
        )
        thread.start()

        return run

    @staticmethod
    def _execute_worker(run_id: int, repository_path: str, goal: str, project_name: str) -> None:
        """
        Worker executed in background thread with an isolated database session.
        Directs execution to workspace path if run.workspace_id is set, otherwise repository_path.
        """
        db = SessionLocal()
        workspace_id: Optional[int] = None
        try:
            run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
            if not run:
                logger.error(f"Worker could not find run {run_id}")
                return

            # If run targets a sandbox, execute within the sandbox container
            if run.sandbox_id:
                sb = db.query(Sandbox).filter(Sandbox.id == run.sandbox_id).first()
                if sb and sb.status != SandboxStatus.REMOVED.value:
                    if sb.status != SandboxStatus.RUNNING.value:
                        SandboxManager.start_sandbox(db, sb.id)
                    run.status = RunStatus.RUNNING.value
                    db.commit()

                    cmd_res = SandboxManager.execute_command(
                        db=db,
                        sandbox_id=sb.id,
                        command=f"python -c 'print(\"Sandbox execution for goal: {goal}\")'"
                    )
                    run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
                    if run:
                        run.status = RunStatus.COMPLETED.value if cmd_res.exit_code == 0 else (RunStatus.TIMEOUT.value if cmd_res.timed_out else RunStatus.FAILED.value)
                        run.exit_code = cmd_res.exit_code
                        run.stdout = cmd_res.stdout
                        run.stderr = cmd_res.stderr
                        run.error_message = cmd_res.error_message
                        run.completed_at = datetime.now(timezone.utc)
                        db.commit()
                        logger.info(f"Run {run_id} finished in sandbox {sb.id} with status {run.status}")
                        return

            # Check Codex availability first
            is_avail, cmd_path, avail_err = CodexRunner.is_available()
            if not is_avail:
                logger.warning(f"Codex unavailable for run {run_id}: {avail_err}")
                run.status = RunStatus.FAILED.value
                run.completed_at = datetime.now(timezone.utc)
                run.exit_code = -1
                run.error_message = avail_err
                run.stderr = avail_err or ""
                db.commit()
                return

            # Determine execution directory: workspace.path if workspace_id, else repository_path
            target_path = repository_path
            if run.workspace_id:
                workspace_id = run.workspace_id
                ws = db.query(Workspace).filter(Workspace.id == run.workspace_id).first()
                if ws and ws.deleted_at is None:
                    target_path = ws.path
                    ws.status = WorkspaceStatus.IN_USE.value
                    db.commit()
                    logger.info(f"Run {run_id} routed to isolated workspace {ws.name} at {ws.path}")
                else:
                    logger.warning(f"Run {run_id} specifies workspace {run.workspace_id} which was not found or deleted; falling back to repository path.")

            # Transition status to RUNNING
            run.status = RunStatus.RUNNING.value
            db.commit()

            # Execute via CodexRunner against target_path
            result = CodexRunner.execute(
                run_id=run_id,
                goal=goal,
                repository_path=target_path,
                project_name=project_name
            )

            # Re-query run to avoid stale state
            run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
            if run:
                run.status = result.status.value
                run.exit_code = result.exit_code
                run.stdout = result.stdout
                run.stderr = result.stderr
                run.error_message = result.error_message
                run.started_at = result.started_at
                run.completed_at = result.completed_at
                db.commit()
                logger.info(f"Run {run_id} finished with status {run.status} (exit {run.exit_code})")

        except Exception as exc:
            logger.exception(f"Unexpected error in execution worker for run {run_id}: {exc}")
            try:
                run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
                if run:
                    run.status = RunStatus.FAILED.value
                    run.completed_at = datetime.now(timezone.utc)
                    run.error_message = f"Execution failed: {exc}"
                    run.stderr = run.stderr + f"\nInternal Execution Error: {exc}"
                    db.commit()
            except Exception:
                pass
        finally:
            # Revert workspace status from IN_USE back to READY
            if workspace_id is not None:
                try:
                    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
                    if ws and ws.status == WorkspaceStatus.IN_USE.value and ws.deleted_at is None:
                        ws.status = WorkspaceStatus.READY.value
                        db.commit()
                except Exception as ws_err:
                    logger.warning(f"Failed to reset workspace {workspace_id} status: {ws_err}")
            db.close()

    @staticmethod
    def cancel_execution(run_id: int, db: Session) -> EngineeringRun:
        """
        Terminate active Codex execution and update run status to CANCELLED.
        """
        run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Engineering run with ID {run_id} not found"
            )

        if run.status not in (RunStatus.STARTING.value, RunStatus.RUNNING.value):
            return run

        # Request cancellation of the process
        CodexRunner.cancel_run(run_id)

        # Update database record
        run.status = RunStatus.CANCELLED.value
        run.completed_at = datetime.now(timezone.utc)
        run.error_message = "The engineering run was cancelled."
        if not run.stderr:
            run.stderr = "[Codex OS] The engineering run was cancelled by user."
        else:
            run.stderr += "\n[Codex OS] The engineering run was cancelled by user."

        # Revert workspace status if IN_USE
        if run.workspace_id:
            ws = db.query(Workspace).filter(Workspace.id == run.workspace_id).first()
            if ws and ws.status == WorkspaceStatus.IN_USE.value and ws.deleted_at is None:
                ws.status = WorkspaceStatus.READY.value

        db.commit()
        db.refresh(run)
        return run

    @staticmethod
    def get_run_logs(run_id: int, db: Session) -> dict:
        """
        Return structured stdout/stderr logs.
        For active runs, integrates live streaming buffers from CodexProcessManager.
        """
        run = db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Engineering run with ID {run_id} not found"
            )

        stdout = run.stdout or ""
        stderr = run.stderr or ""

        # If run is currently active, read from the live stream buffer
        if run.status in (RunStatus.STARTING.value, RunStatus.RUNNING.value):
            live_out, live_err = process_manager.get_live_logs(run_id)
            if live_out is not None:
                stdout = live_out
            if live_err is not None:
                stderr = live_err

        return {
            "id": run.id,
            "status": run.status,
            "workspace_id": run.workspace_id,
            "workspace_name": run.workspace_name,
            "sandbox_id": run.sandbox_id,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": run.exit_code,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "error_message": run.error_message
        }
