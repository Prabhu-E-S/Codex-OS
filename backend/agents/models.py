from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

class AgentType(str, Enum):
    ARCHITECT = "ARCHITECT"
    BUILDER = "BUILDER"
    TESTER = "TESTER"
    BREAKER = "BREAKER"
    SECURITY = "SECURITY"
    JUDGE = "JUDGE"

class AgentStatus(str, Enum):
    PENDING = "PENDING"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

@dataclass
class AgentResult:
    agent_type: AgentType
    agent_name: str
    status: AgentStatus
    output: str
    error_message: Optional[str] = None
    exit_code: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input_summary: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
