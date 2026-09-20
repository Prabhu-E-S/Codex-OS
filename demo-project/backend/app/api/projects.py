from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectDetailResponse
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project."""
    try:
        project = ProjectService.create_project(db, project_in)
        resp = ProjectResponse.model_validate(project)
        resp.task_count = 0
        return resp
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("", response_model=List[ProjectResponse])
def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """List all projects with task counts."""
    results = ProjectService.list_projects(db, skip=skip, limit=limit)
    response_list = []
    for proj, count in results:
        p_resp = ProjectResponse.model_validate(proj)
        p_resp.task_count = count
        response_list.append(p_resp)
    return response_list

@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get project details including owner."""
    project = ProjectService.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project with ID {project_id} not found.")
    
    resp = ProjectDetailResponse.model_validate(project)
    resp.task_count = len(project.tasks)
    return resp

@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, project_in: ProjectUpdate, db: Session = Depends(get_db)):
    """Update project details."""
    project = ProjectService.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project with ID {project_id} not found.")
    try:
        updated = ProjectService.update_project(db, project, project_in)
        resp = ProjectResponse.model_validate(updated)
        resp.task_count = len(updated.tasks)
        return resp
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete project and associated tasks."""
    project = ProjectService.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project with ID {project_id} not found.")
    ProjectService.delete_project(db, project)
    return None
