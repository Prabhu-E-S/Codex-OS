import os
import sys
import shlex
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Tuple

from backend.config import settings
from backend.codex.models import RunStatus, ExecutionResult
from backend.codex.prompts import build_codex_prompt
from backend.codex.process import process_manager

class CodexRunner:
    """
    Dedicated runner responsible for preparing, starting, streaming, and monitoring
    Codex execution against a project's configured repository path.
    """

    @classmethod
    def is_available(cls) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verify whether Codex is configured and available in the host environment.
        Returns (is_available, command_or_path, error_message).
        """
        cmd = settings.CODEX_COMMAND
        if cmd and cmd.strip():
            cmd_name = cmd.strip()
            clean_cmd = cmd_name.strip("\"'")
            # If specified as a direct file path
            if os.path.isabs(clean_cmd) and (os.path.isfile(clean_cmd) or os.path.exists(clean_cmd)):
                return True, cmd_name, None

            # Try parsing with shlex (posix=True strips outer quotes from paths with spaces)
            try:
                tokens = shlex.split(cmd_name, posix=True)
                base_binary = tokens[0] if tokens else clean_cmd
            except Exception:
                base_binary = clean_cmd.split()[0] if clean_cmd.split() else clean_cmd

            base_binary_clean = base_binary.strip("\"'")
            if os.path.isabs(base_binary_clean) and (os.path.isfile(base_binary_clean) or os.path.exists(base_binary_clean)):
                return True, cmd_name, None

            if shutil.which(base_binary_clean):
                return True, cmd_name, None

            return False, None, "Codex is not available in the current environment. Configure the Codex execution environment before starting a run."

        # Auto-detect 'codex' binary in system PATH
        detected = shutil.which("codex")
        if detected:
            return True, detected, None

        return False, None, "Codex is not available in the current environment. Configure the Codex execution environment before starting a run."


    @classmethod
    def cancel_run(cls, run_id: int) -> bool:
        """Cancel an active execution process."""
        return process_manager.cancel(run_id)

    @staticmethod
    def _build_command_args(command_str: str) -> list[str]:
        """
        Build subprocess arguments for Codex execution.
        Bare `codex` starts the interactive CLI, so normalize it to the
        non-interactive exec mode and read the prompt from stdin.
        """
        clean_command = command_str.strip().strip("\"'")
        if os.path.isabs(clean_command) and os.path.exists(clean_command):
            cmd_args = [clean_command]
        else:
            try:
                cmd_args = shlex.split(command_str, posix=True)
            except Exception:
                cmd_args = [command_str]

        if cmd_args:
            executable = os.path.basename(cmd_args[0]).lower()
            if executable in ("codex", "codex.exe", "codex.cmd", "codex.ps1") and "exec" not in cmd_args[1:2]:
                cmd_args = [cmd_args[0], "exec", "-"] + cmd_args[1:]
            if sys.platform == "win32":
                ext = os.path.splitext(cmd_args[0])[1].lower()
                if ext in (".cmd", ".bat"):
                    cmd_args = ["cmd.exe", "/c"] + cmd_args
                elif ext == ".ps1":
                    cmd_args = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File"] + cmd_args

        return cmd_args

    @classmethod
    def execute(
        cls,
        run_id: int,
        goal: str,
        repository_path: str,
        project_name: Optional[str] = None,
        timeout_seconds: Optional[int] = None
    ) -> ExecutionResult:
        """
        Execute an engineering goal with Codex against the project repository path.
        Tracks live output, timeout, process exit, and cancellation.
        """
        started_at = datetime.now(timezone.utc)

        # 1. Verify Codex CLI availability
        available, command_str, avail_error = cls.is_available()
        if not available or not command_str:
            completed_at = datetime.now(timezone.utc)
            return ExecutionResult(
                status=RunStatus.FAILED,
                exit_code=-1,
                stdout="",
                stderr="Codex is not available in the current environment.\nConfigure the Codex execution environment before starting a run.",
                error_message="Codex is not available in the current environment. Configure the Codex execution environment before starting a run.",
                started_at=started_at,
                completed_at=completed_at
            )

        # 2. Verify repository path exists and is a directory
        if not os.path.exists(repository_path) or not os.path.isdir(repository_path):
            completed_at = datetime.now(timezone.utc)
            return ExecutionResult(
                status=RunStatus.FAILED,
                exit_code=-1,
                stdout="",
                stderr=f"Configured repository path does not exist or is not a directory: {repository_path}",
                error_message="The configured project path does not exist.",
                started_at=started_at,
                completed_at=completed_at
            )

        # 3. Build structured prompt
        prompt = build_codex_prompt(goal=goal, repository_path=repository_path, project_name=project_name)

        # 4. Prepare execution command
        cmd_args = cls._build_command_args(command_str)

        # Determine timeout
        timeout = timeout_seconds or settings.CODEX_EXECUTION_TIMEOUT

        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []

        try:
            # Start process in the repository working directory
            process = subprocess.Popen(
                cmd_args,
                cwd=repository_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1
            )
        except Exception as exc:
            completed_at = datetime.now(timezone.utc)
            return ExecutionResult(
                status=RunStatus.FAILED,
                exit_code=-1,
                stdout="",
                stderr=f"Failed to spawn Codex process: {exc}",
                error_message=f"Failed to spawn Codex process: {exc}",
                started_at=started_at,
                completed_at=completed_at
            )

        # Register active process
        process_manager.register(run_id, process)

        # Send prompt into stdin if stdin pipe is open
        def send_input():
            try:
                if process.stdin:
                    process.stdin.write(prompt)
                    process.stdin.close()
            except Exception:
                pass

        threading.Thread(target=send_input, daemon=True).start()

        # Reader threads for real-time streaming
        def read_stream(stream, append_func, chunk_list):
            try:
                for line in iter(stream.readline, ""):
                    chunk_list.append(line)
                    append_func(run_id, line)
            except Exception:
                pass
            finally:
                try:
                    stream.close()
                except Exception:
                    pass

        t_stdout = threading.Thread(
            target=read_stream,
            args=(process.stdout, process_manager.append_stdout, stdout_chunks),
            daemon=True
        )
        t_stderr = threading.Thread(
            target=read_stream,
            args=(process.stderr, process_manager.append_stderr, stderr_chunks),
            daemon=True
        )
        t_stdout.start()
        t_stderr.start()

        # Monitor execution loop with timeout and cancellation check
        start_mono = time.monotonic()
        timed_out = False

        while True:
            exit_code = process.poll()
            if exit_code is not None:
                break

            if process_manager.is_cancelled(run_id):
                break

            elapsed = time.monotonic() - start_mono
            if elapsed > timeout:
                timed_out = True
                process_manager.cancel(run_id)
                break

            time.sleep(0.1)

        t_stdout.join(timeout=1.0)
        t_stderr.join(timeout=1.0)
        completed_at = datetime.now(timezone.utc)

        full_stdout = "".join(stdout_chunks)
        full_stderr = "".join(stderr_chunks)

        # Check timeout
        if timed_out:
            process_manager.unregister(run_id)
            return ExecutionResult(
                status=RunStatus.TIMEOUT,
                exit_code=-1,
                stdout=full_stdout,
                stderr=full_stderr + f"\n[Codex OS] Run execution timed out after {timeout} seconds.",
                error_message="The Codex execution exceeded the configured time limit.",
                started_at=started_at,
                completed_at=completed_at
            )

        # Check cancellation
        if process_manager.is_cancelled(run_id):
            process_manager.unregister(run_id)
            return ExecutionResult(
                status=RunStatus.CANCELLED,
                exit_code=-1,
                stdout=full_stdout,
                stderr=full_stderr + "\n[Codex OS] Run execution was cancelled by user.",
                error_message="The engineering run was cancelled.",
                started_at=started_at,
                completed_at=completed_at
            )


        # Clean up registration
        process_manager.unregister(run_id)

        # Check exit code
        if exit_code == 0:
            return ExecutionResult(
                status=RunStatus.COMPLETED,
                exit_code=0,
                stdout=full_stdout,
                stderr=full_stderr,
                error_message=None,
                started_at=started_at,
                completed_at=completed_at
            )
        else:
            return ExecutionResult(
                status=RunStatus.FAILED,
                exit_code=exit_code,
                stdout=full_stdout,
                stderr=full_stderr,
                error_message="Codex execution failed.",
                started_at=started_at,
                completed_at=completed_at
            )
