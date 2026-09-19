import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.config import settings
from backend.schemas.sandbox import (
    SandboxCreate,
    SandboxResponse,
    SandboxExecuteRequest,
    CommandResultResponse,
    DockerStatusResponse,
)
from backend.sandbox.manager import SandboxManager
from backend.sandbox.models import SandboxSpec
from backend.sandbox.docker import get_docker_provider
from backend.sandbox.exceptions import (
    SandboxError,
    SandboxNotFoundError,
    DockerUnavailableError,
    MountSecurityError,
    CommandExecutionError,
    CommandTimeoutError,
)

logger = logging.getLogger("codex_os.api.sandboxes")

router = APIRouter(tags=["Docker Sandboxes"])


@router.get("/sandboxes/status", response_model=DockerStatusResponse)
def get_docker_status():
    """
    Check availability of the Docker engine and daemon.
    Returns whether Docker is available and operational.
    """
    provider = get_docker_provider()
    is_avail, msg = provider.is_available()
    provider_name = getattr(settings, "DOCKER_SANDBOX_PROVIDER", "real")
    return {
        "available": is_avail,
        "message": msg or ("Docker daemon is available" if is_avail else "Docker daemon is unavailable"),
        "provider": provider_name
    }


@router.post(
    "/workspaces/{workspace_id}/sandbox",
    response_model=SandboxResponse,
    status_code=status.HTTP_201_CREATED
)
def create_workspace_sandbox(
    workspace_id: int,
    payload: Optional[SandboxCreate] = None,
    db: Session = Depends(get_db)
):
    """
    Provision a new isolated Docker sandbox container for the given workspace.
    """
    spec = None
    if payload:
        spec = SandboxSpec(
            image=payload.image or settings.DOCKER_SANDBOX_IMAGE,
            cpu_limit=max(0.1, min(4.0, payload.cpu_limit or settings.DOCKER_SANDBOX_CPU_LIMIT)),
            memory_limit=payload.memory_limit or settings.DOCKER_SANDBOX_MEMORY_LIMIT,
            timeout_seconds=max(1, min(3600, payload.timeout_seconds or settings.DOCKER_SANDBOX_TIMEOUT)),
            network_enabled=payload.network_enabled if payload.network_enabled is not None else (settings.DOCKER_SANDBOX_NETWORK != "none"),
            pids_limit=max(16, min(1024, payload.pids_limit or settings.DOCKER_SANDBOX_PIDS_LIMIT)),
            user=settings.DOCKER_SANDBOX_USER,
        )

    try:
        sandbox = SandboxManager.create_sandbox(db=db, workspace_id=workspace_id, spec=spec)
        return sandbox
    except DockerUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Docker engine is unavailable: {e}"
        )
    except SandboxNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except MountSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security violation: {e}"
        )
    except Exception as e:
        logger.error(f"Sandbox creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the sandbox."
        )


@router.get("/workspaces/{workspace_id}/sandbox", response_model=Optional[SandboxResponse])
def get_workspace_sandbox(workspace_id: int, db: Session = Depends(get_db)):
    """
    Retrieve the active (non-removed) sandbox for a workspace.
    """
    sandbox = SandboxManager.get_active_sandbox(db, workspace_id)
    return sandbox


@router.get("/sandboxes/{sandbox_id}", response_model=SandboxResponse)
def get_sandbox(sandbox_id: int, db: Session = Depends(get_db)):
    """
    Retrieve detailed status of a specific sandbox by ID.
    """
    sandbox = SandboxManager.get_sandbox_by_id(db, sandbox_id)
    if not sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox with ID {sandbox_id} not found"
        )
    return sandbox


@router.post("/sandboxes/{sandbox_id}/start", response_model=SandboxResponse)
def start_sandbox(sandbox_id: int, db: Session = Depends(get_db)):
    """
    Start an existing stopped/created sandbox container.
    """
    try:
        return SandboxManager.start_sandbox(db, sandbox_id)
    except SandboxNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Sandbox start error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while starting the sandbox.")


@router.post("/sandboxes/{sandbox_id}/stop", response_model=SandboxResponse)
def stop_sandbox(sandbox_id: int, db: Session = Depends(get_db)):
    """
    Stop a running sandbox container.
    """
    try:
        return SandboxManager.stop_sandbox(db, sandbox_id)
    except SandboxNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Sandbox stop error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while stopping the sandbox.")


@router.delete("/sandboxes/{sandbox_id}", response_model=SandboxResponse)
def remove_sandbox(sandbox_id: int, db: Session = Depends(get_db)):
    """
    Stop, tear down, and delete the sandbox container while preserving workspace files.
    """
    try:
        return SandboxManager.remove_sandbox(db, sandbox_id)
    except SandboxNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Sandbox remove error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while removing the sandbox.")


@router.post("/sandboxes/{sandbox_id}/execute", response_model=CommandResultResponse)
def execute_sandbox_command(
    sandbox_id: int,
    request: SandboxExecuteRequest,
    db: Session = Depends(get_db)
):
    """
    Execute an arbitrary command safely inside the sandbox's /workspace directory.
    Enforces process timeouts and output capture.
    """
    try:
        result = SandboxManager.execute_command(
            db=db,
            sandbox_id=sandbox_id,
            command=request.command,
            timeout=request.timeout
        )
        return {
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_ms": result.duration_ms,
            "timed_out": result.timed_out,
            "error_message": result.error_message
        }
    except SandboxNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SandboxError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Sandbox execution error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while executing the command.")
