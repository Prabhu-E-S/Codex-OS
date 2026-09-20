from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskDetailResponse
from app.schemas.comment import CommentCreate, CommentResponse
from app.services.task_service import TaskService
from app.services.comment_service import CommentService

router = APIRouter(prefix="/tasks", tags=["Tasks"])

def _format_task_response(task, comment_count: int = 0) -> TaskResponse:
    resp = TaskResponse.model_validate(task)
    resp.project_name = task.project.name if task.project else None
    resp.is_overdue = TaskService.is_task_overdue(task)
    resp.comment_count = comment_count
    return resp

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task_in: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task."""
    try:
        task = TaskService.create_task(db, task_in)
        return _format_task_response(task, comment_count=0)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("", response_model=List[TaskResponse])
def list_tasks(
    status: Optional[str] = Query(None, pattern="^(todo|in_progress|review|done)$"),
    priority: Optional[str] = Query(None, pattern="^(low|medium|high|urgent)$"),
    project_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """List tasks with optional search and filters."""
    results = TaskService.list_tasks(
        db=db,
        status=status,
        priority=priority,
        project_id=project_id,
        assignee_id=assignee_id,
        search=search,
        skip=skip,
        limit=limit
    )
    return [_format_task_response(t, count) for t, count in results]

@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Retrieve detailed information about a task including comments."""
    task = TaskService.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with ID {task_id} not found.")

    resp = TaskDetailResponse.model_validate(task)
    resp.project_name = task.project.name if task.project else None
    resp.is_overdue = TaskService.is_task_overdue(task)
    resp.comment_count = len(task.comments)
    return resp

@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task_in: TaskUpdate, db: Session = Depends(get_db)):
    """Update task fields."""
    task = TaskService.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with ID {task_id} not found.")
    try:
        updated = TaskService.update_task(db, task, task_in)
        return _format_task_response(updated, comment_count=len(updated.comments))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task."""
    task = TaskService.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with ID {task_id} not found.")
    TaskService.delete_task(db, task)
    return None

# Comments Sub-endpoints
@router.post("/{task_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(task_id: int, comment_in: CommentCreate, db: Session = Depends(get_db)):
    """Add a comment to a task."""
    try:
        return CommentService.create_comment(db, task_id, comment_in)
    except ValueError as e:
        # If task does not exist vs author does not exist
        if "Task with id" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{task_id}/comments", response_model=List[CommentResponse])
def list_comments(task_id: int, db: Session = Depends(get_db)):
    """List comments for a specific task."""
    try:
        return CommentService.list_comments_for_task(db, task_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
