from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class ControlRoomRun(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    project_name: str
    status: str
    goal: str
    mode: str  # "AUTONOMOUS" or "MANUAL"
    iteration: int
    max_iterations: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    workspace_id: Optional[int] = None
    workspace_name: Optional[str] = None
    sandbox_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class ControlRoomOrchestration(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    state: str
    current_agent: Optional[str] = None
    iteration: int
    max_iterations: int
    last_decision: Optional[str] = None
    last_decision_reason: Optional[str] = None
    failure_reason: Optional[str] = None
    pause_requested: bool = False
    cancel_requested: bool = False
    is_active: bool = False


class ControlRoomAgent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_type: str
    agent_name: str
    status: str
    iteration: int
    workspace_id: Optional[int] = None
    workspace_name: Optional[str] = None
    sandbox_id: Optional[int] = None
    sandbox_status: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    input_summary: Optional[str] = None
    output: str = ""
    error_message: Optional[str] = None
    exit_code: Optional[int] = None
    findings_count: int = 0


class ControlRoomIterationAgentSummary(BaseModel):
    agent_type: str
    agent_name: str
    status: str
    duration_seconds: Optional[float] = None
    findings_count: int = 0


class ControlRoomIteration(BaseModel):
    iteration_number: int
    status: str  # "COMPLETED", "FAILED", "RUNNING", "RETRYING"
    agents: List[ControlRoomIterationAgentSummary] = []
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    findings_count: int = 0


class ControlRoomWorkspace(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    branch_name: str
    relative_path: str
    status: str
    agent_name: Optional[str] = None


class ControlRoomSandbox(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    image: str
    status: str
    container_id_preview: Optional[str] = None
    cpu_limit: float
    memory_limit: str
    timeout_seconds: int
    exit_code: Optional[int] = None
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None


class ControlRoomFinding(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str  # "BREAKER" or "SECURITY"
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"
    category: str
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    evidence: Optional[str] = None
    reproduction: Optional[str] = None
    remediation: Optional[str] = None
    status: str
    iteration: int
    agent_type: Optional[str] = None
    created_at: datetime


class ControlRoomFindingsSummary(BaseModel):
    total: int = 0
    by_severity: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    open: int = 0
    resolved: int = 0


class ControlRoomDimension(BaseModel):
    dimension: str
    score: Optional[float] = None
    status: str
    weight: float
    weighted_score: Optional[float] = None
    explanation: Optional[str] = None
    limitations: Optional[str] = None


class ControlRoomEvaluation(BaseModel):
    id: int
    status: str
    overall_score: Optional[float] = None
    status_label: str
    score_version: str
    formula: Optional[str] = None
    summary: Optional[str] = None
    strengths: List[str] = []
    weaknesses: List[str] = []
    limitations: List[str] = []
    dimensions: List[ControlRoomDimension] = []
    evaluated_at: Optional[datetime] = None


class ControlRoomEvent(BaseModel):
    timestamp: str
    event_type: str
    iteration: int
    agent: Optional[str] = None
    state: Optional[str] = None
    decision: Optional[str] = None
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ControlRoomLogs(BaseModel):
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    total_lines: int = 0


class ControlRoomSnapshotResponse(BaseModel):
    run: ControlRoomRun
    orchestration: Optional[ControlRoomOrchestration] = None
    agents: List[ControlRoomAgent] = []
    iterations: List[ControlRoomIteration] = []
    workspaces: List[ControlRoomWorkspace] = []
    sandboxes: List[ControlRoomSandbox] = []
    findings: List[ControlRoomFinding] = []
    findings_summary: ControlRoomFindingsSummary = ControlRoomFindingsSummary()
    evaluation: Optional[ControlRoomEvaluation] = None
    recent_events: List[ControlRoomEvent] = []
    logs: ControlRoomLogs = ControlRoomLogs()
