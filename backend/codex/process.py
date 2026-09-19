import os
import sys
import subprocess
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

@dataclass
class ActiveProcess:
    process: subprocess.Popen
    started_at: datetime
    stdout_buffer: list[str] = field(default_factory=list)
    stderr_buffer: list[str] = field(default_factory=list)
    cancelled: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

class CodexProcessManager:
    """
    Thread-safe registry for active Codex execution processes.
    Manages streaming log buffers and safe cancellation of process trees.
    """
    def __init__(self):
        self._processes: Dict[int, ActiveProcess] = {}
        self._global_lock = threading.Lock()

    def register(self, run_id: int, process: subprocess.Popen) -> None:
        with self._global_lock:
            self._processes[run_id] = ActiveProcess(
                process=process,
                started_at=datetime.now(timezone.utc)
            )

    def append_stdout(self, run_id: int, text: str) -> None:
        with self._global_lock:
            active = self._processes.get(run_id)
        if active:
            with active.lock:
                active.stdout_buffer.append(text)

    def append_stderr(self, run_id: int, text: str) -> None:
        with self._global_lock:
            active = self._processes.get(run_id)
        if active:
            with active.lock:
                active.stderr_buffer.append(text)

    def get_live_logs(self, run_id: int) -> Tuple[Optional[str], Optional[str]]:
        with self._global_lock:
            active = self._processes.get(run_id)
        if not active:
            return None, None
        with active.lock:
            return "".join(active.stdout_buffer), "".join(active.stderr_buffer)

    def is_cancelled(self, run_id: int) -> bool:
        with self._global_lock:
            active = self._processes.get(run_id)
        return active.cancelled if active else False

    def cancel(self, run_id: int) -> bool:
        """
        Request cancellation of an active process and terminate its entire child process tree.
        """
        with self._global_lock:
            active = self._processes.get(run_id)
        if not active:
            return False

        with active.lock:
            active.cancelled = True
            proc = active.process

        if proc.poll() is not None:
            return True  # Already terminated

        # Terminate process tree safely
        try:
            if sys.platform == "win32":
                # On Windows, taskkill /F /T kills child processes as well
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False
                )
            else:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

        return True

    def unregister(self, run_id: int) -> None:
        with self._global_lock:
            self._processes.pop(run_id, None)

process_manager = CodexProcessManager()
