from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.workspace import WorkspaceCreate, WorkspaceResponse
from backend.workspace.manager import WorkspaceManager
from backend.workspace.exceptions import (
    WorkspaceError,
    GitError,
    InvalidWorkspaceNameError,
    WorkspacePathEscapeError,
    WorkspaceAlreadyExistsError,
    WorkspaceNotFoundError,
    ProjectRepositoryNotFoundError,
)

router = APIRouter(tags=["Workspaces"])

@router.get("/projects/{project_id}/workspaces", response_model=List[WorkspaceResponse])
def list_project_workspaces(project_id: int, db: Session = Depends(get_db)):
    """Retrieve all active isolated worktree workspaces for a project."""
    return WorkspaceManager.list_workspaces(db, project_id)

@router.post(
    "/projects/{project_id}/workspaces",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED
)
def create_project_workspace(
    project_id: int,
    workspace_in: WorkspaceCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new isolated Git worktree workspace for a project.
    Validates safe workspace name and provisions directory under CODEX_WORKSPACE_ROOT.
    """
    try:
        workspace = WorkspaceManager.create_workspace(
            db=db,
            project_id=project_id,
            name=workspace_in.name
        )
        return WorkspaceManager.get_workspace_by_id(db, workspace.id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ProjectRepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except (InvalidWorkspaceNameError, WorkspacePathEscapeError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except WorkspaceAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except GitError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Git worktree failed: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: int, db: Session = Depends(get_db)):
    """Retrieve details and status for a single workspace."""
    workspace = WorkspaceManager.get_workspace_by_id(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with ID {workspace_id} not found"
        )
    return workspace

@router.delete("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
def remove_workspace(workspace_id: int, db: Session = Depends(get_db)):
    """
    Safely remove an isolated Git worktree workspace and its underlying files.
    """
    try:
        workspace = WorkspaceManager.remove_workspace(db, workspace_id)
        return WorkspaceManager.get_workspace_by_id(db, workspace.id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except WorkspaceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Git removal failed: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
