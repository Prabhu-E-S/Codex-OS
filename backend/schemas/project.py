from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Project display name")
    repository_path: str = Field(..., min_length=1, max_length=1024, description="Local or workspace repository path")
    description: Optional[str] = Field(None, max_length=2000, description="Optional project overview")

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    repository_path: Optional[str] = Field(None, min_length=1, max_length=1024)
    description: Optional[str] = None
    status: Optional[str] = None

class ProjectResponse(ProjectBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    runs_count: int = 0

    model_config = ConfigDict(from_attributes=True)
