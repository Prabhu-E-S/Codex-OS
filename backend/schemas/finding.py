from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class FindingResponse(BaseModel):
    id: int
    engineering_run_id: int
    agent_execution_id: Optional[int] = None
    type: str
    severity: str
    category: str
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    evidence: Optional[str] = None
    reproduction: Optional[str] = None
    remediation: Optional[str] = None
    status: str
    iteration: int = 1
    resolved_iteration: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FindingsSummaryResponse(BaseModel):
    total: int
    breaker_count: int
    security_count: int
    open_count: int = 0
    resolved_count: int = 0
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
