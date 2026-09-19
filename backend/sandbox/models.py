from enum import Enum
from dataclasses import dataclass
from typing import Optional

class SandboxStatus(str, Enum):
    """Lifecycle states of a Docker sandbox environment."""
    CREATING = "CREATING"
    CREATED = "CREATED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
    REMOVED = "REMOVED"


@dataclass
class CommandResult:
    """Structured result of executing a command inside a sandbox container."""
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    error_message: Optional[str] = None


@dataclass
class SandboxSpec:
    """Resource, security, and runtime specification for a sandbox."""
    image: str
    cpu_limit: float = 1.0
    memory_limit: str = "512m"
    timeout_seconds: int = 60
    network_enabled: bool = False
    pids_limit: int = 128
    user: Optional[str] = None


@dataclass
class ContainerState:
    """Low-level container status information."""
    container_id: str
    status: str
    image: str
    running: bool
    exit_code: Optional[int] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
