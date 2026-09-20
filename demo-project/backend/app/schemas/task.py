from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserResponse
from app.schemas.comment import CommentResponse

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: str = Field(default="todo", pattern="^(todo|in_progress|review|done)$")
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    due_date: Optional[datetime] = None
    project_id: int
    assignee_id: Optional[int] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(todo|in_progress|review|done)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    due_date: Optional[datetime] = None
    project_id: Optional[int] = None
    assignee_id: Optional[int] = None

class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime
    project_name: Optional[str] = None
    assignee: Optional[UserResponse] = None
    is_overdue: bool = False
    comment_count: int = 0

    model_config = ConfigDict(from_attributes=True)

class TaskDetailResponse(TaskResponse):
    comments: List[CommentResponse] = []
