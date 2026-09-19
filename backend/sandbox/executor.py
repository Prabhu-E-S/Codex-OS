import logging
import time
from typing import Optional

from backend.sandbox.models import CommandResult
from backend.sandbox.docker import DockerProvider, get_docker_provider
from backend.sandbox.exceptions import (
    CommandExecutionError,
    CommandTimeoutError,
    SandboxError,
)

logger = logging.getLogger("codex_os.sandbox.executor")

class SandboxExecutor:
    """
    Executes commands securely inside an active Docker sandbox container.
    Enforces working directory (/workspace), timeout limits, and output capture.
    """

    @staticmethod
    def execute(
        container_id: str,
        command: str,
        timeout: int = 60,
        workdir: str = "/workspace",
        provider: Optional[DockerProvider] = None
    ) -> CommandResult:
        """
        Execute command inside the specified container.
        """
        if not command or not command.strip():
            return CommandResult(
                exit_code=1,
                stdout="",
                stderr="Command must be a non-empty string.",
                duration_ms=0,
                timed_out=False,
                error_message="Empty command provided"
            )

        cmd_clean = command.strip()
        docker_provider = provider or get_docker_provider()

        logger.info(f"Executing command in sandbox {container_id[:12]} (timeout={timeout}s): {cmd_clean[:80]}")
        start_time = time.perf_counter()

        try:
            result = docker_provider.exec_run(
                container_id=container_id,
                command=cmd_clean,
                timeout=timeout,
                workdir=workdir
            )
            logger.info(
                f"Execution in sandbox {container_id[:12]} completed with exit code {result.exit_code} "
                f"in {result.duration_ms}ms (timed_out={result.timed_out})"
            )
            return result
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Execution error in sandbox {container_id[:12]}: {exc}")
            return CommandResult(
                exit_code=-1,
                stdout="",
                stderr=f"Sandbox command execution failed: {exc}",
                duration_ms=duration_ms,
                timed_out=False,
                error_message=str(exc)
            )
