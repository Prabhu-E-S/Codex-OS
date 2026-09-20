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

    @classmethod
    def from_run(cls, run, orch_state=None) -> "OrchestrationResponse":
        effective_orch = orch_state or getattr(run, "orchestration_state", None)
        if effective_orch:
            return cls.from_orm_model(effective_orch)

        # Determine iteration from existing agent executions
        iteration = 1
        agent_execs = getattr(run, "agent_executions", []) or []
        if agent_execs:
            iterations = [ae.iteration for ae in agent_execs if getattr(ae, "iteration", None)]
            if iterations:
                iteration = max(iterations)
        max_iterations = max(iteration, 1)

        # Check for active agent execution
        active_ae = None
        for ae in agent_execs:
            if getattr(ae, "status", None) in ("STARTING", "RUNNING"):
                active_ae = ae
                break

        current_agent = active_ae.agent_name if active_ae else None

        # Map run status to orchestration workflow state
        status_upper = (getattr(run, "status", None) or "PENDING").upper()
        if status_upper == "COMPLETED":
            state = "COMPLETED"
        elif status_upper in ("FAILED", "TIMEOUT"):
            state = "FAILED"
        elif status_upper == "CANCELLED":
            state = "CANCELLED"
        elif status_upper == "PAUSED":
            state = "PAUSED"
        elif active_ae:
            type_map = {
                "ARCHITECT": "ARCHITECTING",
                "BUILDER": "BUILDING",
                "TESTER": "TESTING",
                "BREAKER": "BREAKING",
                "SECURITY": "SECURITY_SCANNING",
            }
            state = type_map.get((getattr(active_ae, "agent_type", "") or "").upper(), "BUILDING")
        elif status_upper in ("STARTING", "RUNNING"):
            state = "BUILDING"
        else:
            state = "PENDING"

        failure_reason = getattr(run, "error_message", None) if status_upper in ("FAILED", "TIMEOUT") else None

        from datetime import timezone
        now = datetime.now(timezone.utc)
        created_at = getattr(run, "created_at", None) or now
        updated_at = getattr(run, "updated_at", None) or now

        return cls(
            id=run.id,
            engineering_run_id=run.id,
            state=state,
            current_agent=current_agent,
            iteration=iteration,
            max_iterations=max_iterations,
            last_decision=None,
            last_decision_reason=None,
            pause_requested=False,
            cancel_requested=False,
            failure_reason=failure_reason,
            events=[],
            created_at=created_at,
            updated_at=updated_at,
        )
