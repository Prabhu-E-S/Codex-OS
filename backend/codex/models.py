from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class RunStatus(str, Enum):
    PENDING = "PENDING"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"

@dataclass
class ExecutionResult:
    status: RunStatus
    exit_code: Optional[int]
    stdout: str
    stderr: str
    error_message: Optional[str]
    started_at: datetime
    completed_at: datetime
