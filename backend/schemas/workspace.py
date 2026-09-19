from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class WorkspaceBase(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$",
        description="Safe workspace identifier (alphanumeric, hyphens, underscores)"
    )

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceResponse(WorkspaceBase):
    id: int
    project_id: int
    path: str
    branch_name: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    active_runs_count: int = 0

    model_config = ConfigDict(from_attributes=True)
