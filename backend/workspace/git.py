import os
import shutil
import subprocess
import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from backend.config import settings
from backend.workspace.models import WorktreeInfo
from backend.workspace.exceptions import GitError

logger = logging.getLogger("codex_os.workspace.git")

class GitWorkspaceProvider(ABC):
    """Abstract interface for Git worktree management operations."""

    @abstractmethod
    def create_worktree(self, repo_path: str, worktree_path: str, branch_name: str) -> None:
        """Create an isolated worktree at worktree_path anchored to branch_name."""
        pass

    @abstractmethod
    def remove_worktree(self, repo_path: str, worktree_path: str, force: bool = True) -> None:
        """Remove a worktree at worktree_path."""
        pass

    @abstractmethod
    def list_worktrees(self, repo_path: str) -> List[WorktreeInfo]:
        """List all active worktrees for the repository."""
        pass

    @abstractmethod
    def worktree_exists(self, repo_path: str, worktree_path: str) -> bool:
        """Check if a worktree exists at the given path."""
        pass

    @abstractmethod
    def is_git_repository(self, repo_path: str) -> bool:
        """Check if repo_path is a valid Git repository."""
        pass


class RealGitWorkspaceProvider(GitWorkspaceProvider):
    """
    Production Git provider using safe subprocess argument lists.
    Never uses shell=True. Enforces timeouts and converts failures to GitError.
    """

    def __init__(self, git_binary: str = "git", timeout_seconds: int = 60):
        self.git_binary = git_binary
        self.timeout_seconds = timeout_seconds

    def _run_git(self, repo_path: str, args: List[str]) -> str:
        cmd = [self.git_binary] + args
        logger.debug(f"Executing Git command: {cmd} in {repo_path}")
        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False
            )
        except FileNotFoundError:
            raise GitError("Git executable not found in system PATH.")
        except subprocess.TimeoutExpired:
            raise GitError(f"Git command timed out after {self.timeout_seconds}s: {' '.join(cmd)}")
        except Exception as exc:
            raise GitError(f"Failed to execute Git command: {exc}")

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or f"Git exited with code {result.returncode}"
            logger.warning(f"Git command failed [{result.returncode}]: {error_msg}")
            raise GitError(
                message=f"Git operation failed: {error_msg}",
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr
            )

        return result.stdout

    def is_git_repository(self, repo_path: str) -> bool:
        if not os.path.exists(repo_path) or not os.path.isdir(repo_path):
            return False
        git_dir = os.path.join(repo_path, ".git")
        if os.path.exists(git_dir):
            return True
        try:
            self._run_git(repo_path, ["rev-parse", "--is-inside-work-tree"])
            return True
        except GitError:
            return False

    def create_worktree(self, repo_path: str, worktree_path: str, branch_name: str) -> None:
        parent_dir = os.path.dirname(worktree_path)
        os.makedirs(parent_dir, exist_ok=True)
        # git worktree add -b <branch_name> <worktree_path>
        self._run_git(repo_path, ["worktree", "add", "-b", branch_name, worktree_path])

    def remove_worktree(self, repo_path: str, worktree_path: str, force: bool = True) -> None:
        args = ["worktree", "remove"]
        if force:
            args.append("--force")
        args.append(worktree_path)
        self._run_git(repo_path, args)

    def list_worktrees(self, repo_path: str) -> List[WorktreeInfo]:
        output = self._run_git(repo_path, ["worktree", "list", "--porcelain"])
        worktrees: List[WorktreeInfo] = []
        current_path: Optional[str] = None
        current_branch: Optional[str] = None
        current_commit: Optional[str] = None

        for line in output.splitlines():
            line = line.strip()
            if line.startswith("worktree "):
                current_path = line[len("worktree "):].strip()
            elif line.startswith("HEAD "):
                current_commit = line[len("HEAD "):].strip()
            elif line.startswith("branch "):
                current_branch = line[len("branch "):].strip()
            elif line == "":
                if current_path:
                    worktrees.append(WorktreeInfo(
                        path=current_path,
                        branch=current_branch or "detached",
                        commit_hash=current_commit
                    ))
                current_path = None
                current_branch = None
                current_commit = None

        if current_path:
            worktrees.append(WorktreeInfo(
                path=current_path,
                branch=current_branch or "detached",
                commit_hash=current_commit
            ))

        return worktrees

    def worktree_exists(self, repo_path: str, worktree_path: str) -> bool:
        if not os.path.exists(worktree_path):
            return False
        try:
            trees = self.list_worktrees(repo_path)
            normalized_target = os.path.normcase(os.path.abspath(worktree_path))
            return any(os.path.normcase(os.path.abspath(t.path)) == normalized_target for t in trees)
        except GitError:
            return False


class MockGitWorkspaceProvider(GitWorkspaceProvider):
    """
    Mock implementation for tests and zero-Git environments.
    Simulates worktree creation/removal in memory and filesystem stubs without invoking Git.
    """

    def __init__(self, create_physical_stubs: bool = True):
        self.create_physical_stubs = create_physical_stubs
        self.worktrees: dict[str, WorktreeInfo] = {}
        self.created_calls: list[tuple[str, str, str]] = []
        self.removed_calls: list[tuple[str, str, bool]] = []
        self.simulate_error: Optional[str] = None

    def is_git_repository(self, repo_path: str) -> bool:
        return os.path.exists(repo_path) and os.path.isdir(repo_path)

    def create_worktree(self, repo_path: str, worktree_path: str, branch_name: str) -> None:
        self.created_calls.append((repo_path, worktree_path, branch_name))
        if self.simulate_error:
            raise GitError(self.simulate_error, exit_code=128)

        norm_path = os.path.normcase(os.path.abspath(worktree_path))
        self.worktrees[norm_path] = WorktreeInfo(
            path=worktree_path,
            branch=branch_name,
            commit_hash="mock000000000000000000000000000000000000"
        )

        if self.create_physical_stubs:
            os.makedirs(worktree_path, exist_ok=True)
            with open(os.path.join(worktree_path, ".codex_worktree"), "w", encoding="utf-8") as f:
                f.write(f"branch={branch_name}\nrepo={repo_path}\n")

    def remove_worktree(self, repo_path: str, worktree_path: str, force: bool = True) -> None:
        self.removed_calls.append((repo_path, worktree_path, force))
        if self.simulate_error:
            raise GitError(self.simulate_error, exit_code=128)

        norm_path = os.path.normcase(os.path.abspath(worktree_path))
        self.worktrees.pop(norm_path, None)

        if self.create_physical_stubs and os.path.exists(worktree_path):
            try:
                shutil.rmtree(worktree_path, ignore_errors=True)
            except Exception:
                pass

    def list_worktrees(self, repo_path: str) -> List[WorktreeInfo]:
        return list(self.worktrees.values())

    def worktree_exists(self, repo_path: str, worktree_path: str) -> bool:
        norm_path = os.path.normcase(os.path.abspath(worktree_path))
        return norm_path in self.worktrees


_provider_instance: Optional[GitWorkspaceProvider] = None

def get_git_provider(provider_type: Optional[str] = None) -> GitWorkspaceProvider:
    """Factory function returning the configured GitWorkspaceProvider singleton."""
    global _provider_instance
    chosen_type = provider_type or settings.CODEX_GIT_PROVIDER
    if _provider_instance is None or (provider_type and _provider_instance.__class__.__name__ != f"{chosen_type.capitalize()}GitWorkspaceProvider"):
        if chosen_type == "mock":
            _provider_instance = MockGitWorkspaceProvider()
        else:
            _provider_instance = RealGitWorkspaceProvider()
    return _provider_instance

def set_git_provider(provider: GitWorkspaceProvider) -> None:
    """Explicitly override the active GitWorkspaceProvider (useful in tests)."""
    global _provider_instance
    _provider_instance = provider
