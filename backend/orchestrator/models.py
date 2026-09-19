from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

class WorkflowState(str, Enum):
    PENDING = "PENDING"
    ARCHITECTING = "ARCHITECTING"
    BUILDING = "BUILDING"
    TESTING = "TESTING"
    BREAKING = "BREAKING"
    SECURITY_SCANNING = "SECURITY_SCANNING"
    DECIDING = "DECIDING"
    ITERATING = "ITERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"


class OrchestratorDecision(str, Enum):
    CONTINUE = "CONTINUE"
    RETRY_BUILDER = "RETRY_BUILDER"
    STOP_SUCCESS = "STOP_SUCCESS"
    STOP_FAILURE = "STOP_FAILURE"
    PAUSE = "PAUSE"
    CANCELLED = "CANCELLED"


@dataclass
class DecisionResult:
    decision: OrchestratorDecision
    reason: str
    blocking_findings_count: int = 0
    test_failed: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestrationEvent:
    event_type: str
    run_id: int
    iteration: int
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent: Optional[str] = None
    state: Optional[str] = None
    decision: Optional[str] = None
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "run_id": self.run_id,
            "iteration": self.iteration,
            "timestamp": self.timestamp,
            "agent": self.agent,
            "state": self.state,
            "decision": self.decision,
            "reason": self.reason,
            "details": self.details,
        }
