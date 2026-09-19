from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.run import RunCreate, RunResponse, RunLogsResponse
from backend.services.project_service import ProjectService
from backend.services.execution_service import ExecutionService

router = APIRouter(tags=["Engineering Runs"])

@router.get("/projects/{project_id}/runs", response_model=List[RunResponse])
def list_project_runs(project_id: int, db: Session = Depends(get_db)):
    """Retrieve all engineering runs for a specific project."""
    project = ProjectService.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    return ProjectService.get_project_runs(db, project_id)

@router.post(
    "/projects/{project_id}/runs",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED
)
def create_project_run(project_id: int, run_in: RunCreate, db: Session = Depends(get_db)):
    """Create a new engineering run record for a project."""
    project = ProjectService.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    if not run_in.goal or not run_in.goal.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Run goal is required"
        )
    if run_in.workspace_id:
        from backend.models.workspace import Workspace
        ws = db.query(Workspace).filter(
            Workspace.id == run_in.workspace_id,
            Workspace.project_id == project_id,
            Workspace.deleted_at.is_(None)
        ).first()
        if not ws:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workspace with ID {run_in.workspace_id} not found for this project"
            )
    if run_in.sandbox_id:
        from backend.models.sandbox import Sandbox
        from backend.sandbox.models import SandboxStatus
        sb = db.query(Sandbox).filter(
            Sandbox.id == run_in.sandbox_id,
            Sandbox.status != SandboxStatus.REMOVED.value
        ).first()
        if not sb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active sandbox with ID {run_in.sandbox_id} not found"
            )
    return ProjectService.create_run(db, project_id, run_in)

@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: int, db: Session = Depends(get_db)):
    """Retrieve a single engineering run by ID."""
    run = ProjectService.get_run_by_id(db, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Engineering run with ID {run_id} not found"
        )
    return run

@router.post("/runs/{run_id}/execute", response_model=RunResponse)
def execute_run(run_id: int, db: Session = Depends(get_db)):
    """
    Start Codex execution for an engineering run against the project's repository path.
    Transitions status to STARTING and launches background process execution.
    """
    return ExecutionService.start_execution(run_id, db)

@router.get("/runs/{run_id}/logs", response_model=RunLogsResponse)
def get_run_logs(run_id: int, db: Session = Depends(get_db)):
    """
    Retrieve stdout and stderr logs for an engineering run.
    For active runs, streams live process output buffers.
    """
    return ExecutionService.get_run_logs(run_id, db)

@router.post("/runs/{run_id}/cancel", response_model=RunResponse)
def cancel_run(run_id: int, db: Session = Depends(get_db)):
    """
    Cancel an active engineering run, terminating the underlying Codex process tree.
    """
    return ExecutionService.cancel_execution(run_id, db)

