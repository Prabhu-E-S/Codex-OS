from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class AgentExecutionResponse(BaseModel):
    id: int
    engineering_run_id: int
    agent_type: str
    agent_name: str
    workspace_id: Optional[int] = None
    workspace_name: Optional[str] = None
    sandbox_id: Optional[int] = None
    status: str
    input_summary: Optional[str] = None
    output: str
    error_message: Optional[str] = None
    exit_code: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentWorkflowStatusResponse(BaseModel):
    run_id: int
    run_status: str
    active_agent: Optional[str] = None
    agents: List[AgentExecutionResponse]

    model_config = ConfigDict(from_attributes=True)
