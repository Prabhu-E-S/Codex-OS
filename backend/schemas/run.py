from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class RunBase(BaseModel):
    goal: str = Field(..., min_length=1, description="Engineering run goal or objective")
    status: Optional[str] = Field("PENDING", max_length=50, description="Run status")
    workspace_id: Optional[int] = Field(None, description="Optional isolated workspace ID")
    sandbox_id: Optional[int] = Field(None, description="Optional Docker sandbox ID")

class RunCreate(RunBase):
    pass

class RunResponse(BaseModel):
    id: int
    project_id: int
    workspace_id: Optional[int] = None
    workspace_name: Optional[str] = None
    sandbox_id: Optional[int] = None
    status: str
    goal: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    stdout: Optional[str] = ""
    stderr: Optional[str] = ""
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RunLogsResponse(BaseModel):
    id: int
    status: str
    workspace_id: Optional[int] = None
    workspace_name: Optional[str] = None
    sandbox_id: Optional[int] = None
    stdout: str
    stderr: str
    exit_code: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


