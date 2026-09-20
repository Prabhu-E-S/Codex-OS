from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserResponse

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: str = Field(default="active", pattern="^(active|completed|archived)$")

class ProjectCreate(ProjectBase):
    owner_id: int

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|completed|archived)$")
    owner_id: Optional[int] = None

class ProjectResponse(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    task_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)

class ProjectDetailResponse(ProjectResponse):
    owner: Optional[UserResponse] = None
