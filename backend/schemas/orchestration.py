import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class StartAutonomousRunRequest(BaseModel):
    max_iterations: int = Field(default=3, ge=1, le=10, description="Maximum iterations (1-10)")

class OrchestrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    engineering_run_id: int
    state: str
    current_agent: Optional[str] = None
    iteration: int
    max_iterations: int
    last_decision: Optional[str] = None
    last_decision_reason: Optional[str] = None
    pause_requested: bool
    cancel_requested: bool
    failure_reason: Optional[str] = None
    events: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_model(cls, orch_state) -> "OrchestrationResponse":
        try:
            evts = json.loads(orch_state.events_json or "[]")
        except Exception:
            evts = []

        return cls(
            id=orch_state.id,
            engineering_run_id=orch_state.engineering_run_id,
            state=orch_state.state,
            current_agent=orch_state.current_agent,
            iteration=orch_state.iteration,
            max_iterations=orch_state.max_iterations,
            last_decision=orch_state.last_decision,
            last_decision_reason=orch_state.last_decision_reason,
            pause_requested=orch_state.pause_requested,
            cancel_requested=orch_state.cancel_requested,
            failure_reason=orch_state.failure_reason,
            events=evts,
            created_at=orch_state.created_at,
            updated_at=orch_state.updated_at,
        )
