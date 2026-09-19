from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class SandboxCreate(BaseModel):
    """Payload for provisioning a new Docker sandbox."""
    image: Optional[str] = Field(None, description="Docker image tag (defaults to configured image)")
    cpu_limit: Optional[float] = Field(None, ge=0.1, le=16.0, description="CPU core limit")
    memory_limit: Optional[str] = Field(None, description="Memory limit (e.g. 512m, 1g)")
    timeout_seconds: Optional[int] = Field(None, ge=5, le=3600, description="Command execution timeout in seconds")
    network_enabled: Optional[bool] = Field(None, description="Enable container network access (defaults to false/none)")
    pids_limit: Optional[int] = Field(None, ge=16, le=1024, description="PID process limit")


class SandboxResponse(BaseModel):
    """Detailed sandbox status and telemetry response."""
    id: int
    workspace_id: int
    container_id: Optional[str] = None
    image: str
    status: str
    cpu_limit: float
    memory_limit: str
    timeout_seconds: int
    network_enabled: bool
    pids_limit: int
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SandboxExecuteRequest(BaseModel):
    """Payload for executing a command inside a sandbox."""
    command: str = Field(..., min_length=1, description="Command string to execute inside /workspace")
    timeout: Optional[int] = Field(None, ge=1, le=600, description="Optional command timeout in seconds")


class CommandResultResponse(BaseModel):
    """Structured output of a sandbox command execution."""
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    error_message: Optional[str] = None


class DockerStatusResponse(BaseModel):
    """Docker daemon and SDK availability check response."""
    available: bool
    message: str
    provider: str
