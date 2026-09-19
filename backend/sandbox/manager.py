import os
import time
import logging
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.workspace import Workspace
from backend.models.sandbox import Sandbox
from backend.sandbox.models import SandboxStatus, SandboxSpec, CommandResult
from backend.sandbox.docker import DockerProvider, get_docker_provider
from backend.sandbox.executor import SandboxExecutor
from backend.sandbox.exceptions import (
    SandboxError,
    SandboxNotFoundError,
    DockerUnavailableError,
    MountSecurityError,
    ContainerCreationError,
    ContainerStartError,
    ContainerStopError,
    ContainerRemovalError,
)

logger = logging.getLogger("codex_os.sandbox.manager")


class SandboxManager:
    """
    High-level lifecycle management for Docker sandboxes tied to Phase 3 workspaces.
    Coordinates creation, startup, execution, stopping, teardown, and recreation.
    """

    @staticmethod
    def get_default_spec() -> SandboxSpec:
        """Create a SandboxSpec from environment settings."""
        return SandboxSpec(
            image=getattr(settings, "DOCKER_SANDBOX_IMAGE", "python:3.12-slim"),
            cpu_limit=getattr(settings, "DOCKER_SANDBOX_CPU_LIMIT", 1.0),
            memory_limit=getattr(settings, "DOCKER_SANDBOX_MEMORY_LIMIT", "512m"),
            timeout_seconds=getattr(settings, "DOCKER_SANDBOX_TIMEOUT", 60),
            network_enabled=(getattr(settings, "DOCKER_SANDBOX_NETWORK", "none") != "none"),
            pids_limit=getattr(settings, "DOCKER_SANDBOX_PIDS_LIMIT", 128),
            user=getattr(settings, "DOCKER_SANDBOX_USER", None),
        )

    @classmethod
    def create_sandbox(
        cls,
        db: Session,
        workspace_id: int,
        spec: Optional[SandboxSpec] = None,
        provider: Optional[DockerProvider] = None
    ) -> Sandbox:
        """
        Create a new Docker sandbox container bound to a workspace.
        """
        docker_provider = provider or get_docker_provider()

        # 1. Check Docker availability
        is_avail, avail_msg = docker_provider.is_available()
        if not is_avail:
            raise DockerUnavailableError(avail_msg or "Docker daemon is unavailable.")

        # 2. Validate workspace exists
        workspace = db.query(Workspace).filter(
            Workspace.id == workspace_id,
            Workspace.deleted_at.is_(None)
        ).first()
        if not workspace:
            raise SandboxNotFoundError(f"Active workspace with ID {workspace_id} not found.")

        # 3. Validate workspace path exists on disk
        if not os.path.exists(workspace.path) or not os.path.isdir(workspace.path):
            raise MountSecurityError(f"Workspace directory does not exist: {workspace.path}")

        # 4. Check if an active non-removed sandbox already exists for this workspace
        existing = (
            db.query(Sandbox)
            .filter(
                Sandbox.workspace_id == workspace_id,
                Sandbox.status.notin_([SandboxStatus.REMOVED.value, SandboxStatus.FAILED.value])
            )
            .first()
        )
        if existing:
            return existing

        sandbox_spec = spec or cls.get_default_spec()
        container_name = f"codex-sandbox-ws{workspace_id}-{int(time.time())}"

        # 5. Create initial record in CREATING state
        sandbox = Sandbox(
            workspace_id=workspace_id,
            image=sandbox_spec.image,
            status=SandboxStatus.CREATING.value,
            cpu_limit=sandbox_spec.cpu_limit,
            memory_limit=sandbox_spec.memory_limit,
            timeout_seconds=sandbox_spec.timeout_seconds,
            network_enabled=sandbox_spec.network_enabled,
            pids_limit=sandbox_spec.pids_limit,
            error_message=None,
        )
        db.add(sandbox)
        db.commit()
        db.refresh(sandbox)

        # 6. Invoke provider to create container with isolated mount
        try:
            container_id = docker_provider.create_container(
                name=container_name,
                host_workspace_path=workspace.path,
                spec=sandbox_spec
            )
            sandbox.container_id = container_id
            sandbox.status = SandboxStatus.CREATED.value
            db.commit()
            db.refresh(sandbox)
            logger.info(f"Sandbox {sandbox.id} created successfully with container {container_id[:12]}")
            return sandbox
        except Exception as exc:
            sandbox.status = SandboxStatus.FAILED.value
            sandbox.error_message = str(exc)
            db.commit()
            db.refresh(sandbox)
            logger.error(f"Failed to create sandbox for workspace {workspace_id}: {exc}")
            raise

    @classmethod
    def start_sandbox(
        cls,
        db: Session,
        sandbox_id: int,
        provider: Optional[DockerProvider] = None
    ) -> Sandbox:
        """
        Transition sandbox from CREATED/STOPPED to RUNNING.
        """
        docker_provider = provider or get_docker_provider()
        sandbox = db.query(Sandbox).filter(Sandbox.id == sandbox_id).first()
        if not sandbox:
            raise SandboxNotFoundError(f"Sandbox with ID {sandbox_id} not found.")

        if sandbox.status == SandboxStatus.RUNNING.value:
            return sandbox

        if not sandbox.container_id:
            raise SandboxError("Sandbox has no container ID; it may need to be recreated.")

        sandbox.status = SandboxStatus.STARTING.value
        db.commit()

        try:
            docker_provider.start_container(sandbox.container_id)
            sandbox.status = SandboxStatus.RUNNING.value
            sandbox.started_at = datetime.now(timezone.utc)
            sandbox.error_message = None
            db.commit()
            db.refresh(sandbox)
            logger.info(f"Sandbox {sandbox_id} transitioned to RUNNING")
            return sandbox
        except Exception as exc:
            sandbox.status = SandboxStatus.FAILED.value
            sandbox.error_message = str(exc)
            db.commit()
            db.refresh(sandbox)
            logger.error(f"Failed to start sandbox {sandbox_id}: {exc}")
            raise

    @classmethod
    def stop_sandbox(
        cls,
        db: Session,
        sandbox_id: int,
        timeout: int = 10,
        provider: Optional[DockerProvider] = None
    ) -> Sandbox:
        """
        Stop a running sandbox container.
        """
        docker_provider = provider or get_docker_provider()
        sandbox = db.query(Sandbox).filter(Sandbox.id == sandbox_id).first()
        if not sandbox:
            raise SandboxNotFoundError(f"Sandbox with ID {sandbox_id} not found.")

        if sandbox.status in (SandboxStatus.STOPPED.value, SandboxStatus.REMOVED.value):
            return sandbox

        sandbox.status = SandboxStatus.STOPPING.value
        db.commit()

        try:
            if sandbox.container_id:
                docker_provider.stop_container(sandbox.container_id, timeout=timeout)
            sandbox.status = SandboxStatus.STOPPED.value
            sandbox.stopped_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(sandbox)
            logger.info(f"Sandbox {sandbox_id} transitioned to STOPPED")
            return sandbox
        except Exception as exc:
            sandbox.status = SandboxStatus.FAILED.value
            sandbox.error_message = str(exc)
            db.commit()
            db.refresh(sandbox)
            logger.error(f"Failed to stop sandbox {sandbox_id}: {exc}")
            raise

    @classmethod
    def remove_sandbox(
        cls,
        db: Session,
        sandbox_id: int,
        force: bool = True,
        provider: Optional[DockerProvider] = None
    ) -> Sandbox:
        """
        Stop and remove the container, marking status REMOVED.
        Crucially: Preserves host workspace files untouched.
        """
        docker_provider = provider or get_docker_provider()
        sandbox = db.query(Sandbox).filter(Sandbox.id == sandbox_id).first()
        if not sandbox:
            raise SandboxNotFoundError(f"Sandbox with ID {sandbox_id} not found.")

        if sandbox.status == SandboxStatus.REMOVED.value:
            return sandbox

        try:
            if sandbox.container_id:
                # Stop if currently running
                if sandbox.status == SandboxStatus.RUNNING.value:
                    try:
                        docker_provider.stop_container(sandbox.container_id, timeout=5)
                    except Exception as stop_err:
                        logger.warning(f"Error stopping container prior to removal: {stop_err}")

                docker_provider.remove_container(sandbox.container_id, force=force)

            sandbox.status = SandboxStatus.REMOVED.value
            sandbox.container_id = None
            sandbox.stopped_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(sandbox)
            logger.info(f"Sandbox {sandbox_id} successfully removed (workspace files preserved)")
            return sandbox
        except Exception as exc:
            sandbox.status = SandboxStatus.FAILED.value
            sandbox.error_message = str(exc)
            db.commit()
            db.refresh(sandbox)
            logger.error(f"Failed to remove sandbox {sandbox_id}: {exc}")
            raise

    @classmethod
    def execute_command(
        cls,
        db: Session,
        sandbox_id: int,
        command: str,
        timeout: Optional[int] = None,
        provider: Optional[DockerProvider] = None
    ) -> CommandResult:
        """
        Execute command inside the container and return structured CommandResult.
        Auto-starts sandbox if it is in CREATED or STOPPED state.
        """
        docker_provider = provider or get_docker_provider()
        sandbox = db.query(Sandbox).filter(Sandbox.id == sandbox_id).first()
        if not sandbox:
            raise SandboxNotFoundError(f"Sandbox with ID {sandbox_id} not found.")

        # Ensure container is running
        if sandbox.status != SandboxStatus.RUNNING.value:
            if sandbox.status in (SandboxStatus.CREATED.value, SandboxStatus.STOPPED.value):
                cls.start_sandbox(db, sandbox_id, provider=docker_provider)
            else:
                raise SandboxError(f"Cannot execute command in sandbox with status '{sandbox.status}'.")

        cmd_timeout = timeout or sandbox.timeout_seconds
        result = SandboxExecutor.execute(
            container_id=sandbox.container_id,
            command=command,
            timeout=cmd_timeout,
            workdir="/workspace",
            provider=docker_provider
        )
        return result

    @staticmethod
    def get_active_sandbox(db: Session, workspace_id: int) -> Optional[Sandbox]:
        """Fetch the current active (non-removed) sandbox for a workspace."""
        return (
            db.query(Sandbox)
            .filter(
                Sandbox.workspace_id == workspace_id,
                Sandbox.status != SandboxStatus.REMOVED.value
            )
            .order_by(Sandbox.created_at.desc())
            .first()
        )

    @staticmethod
    def get_sandbox_by_id(db: Session, sandbox_id: int) -> Optional[Sandbox]:
        """Fetch sandbox record by ID."""
        return db.query(Sandbox).filter(Sandbox.id == sandbox_id).first()
