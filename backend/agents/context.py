from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from backend.agents.models import AgentType, AgentResult

@dataclass
class AgentContext:
    """
    Execution context provided to an agent.
    Encapsulates project information, engineering goal, isolated workspace path,
    assigned sandbox, and prior results from upstream agents.
    Agents do not directly manipulate database internals.
    """
    project_id: int
    project_name: str
    repository_path: str
    engineering_run_id: int
    engineering_goal: str
    workspace_id: Optional[int] = None
    workspace_name: Optional[str] = None
    workspace_path: Optional[str] = None
    sandbox_id: Optional[int] = None
    previous_results: Dict[AgentType, AgentResult] = field(default_factory=dict)
    timeout_seconds: int = 900
    config: Dict[str, Any] = field(default_factory=dict)
    # Phase 7 Iteration context
    iteration: int = 1
    is_autonomous: bool = False
    tester_feedback: Optional[str] = None
    breaker_findings: list[Dict[str, Any]] = field(default_factory=list)
    security_findings: list[Dict[str, Any]] = field(default_factory=list)
    previous_failure_reason: Optional[str] = None
    orchestrator_decision: Optional[str] = None

    def get_previous_result(self, agent_type: AgentType) -> Optional[AgentResult]:
        """Retrieve output and status from a previous agent in the workflow."""
        return self.previous_results.get(agent_type)
