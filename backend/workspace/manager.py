import os
import re
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.project import Project
from backend.models.workspace import Workspace
from backend.models.run import EngineeringRun
from backend.workspace.models import WorkspaceStatus
from backend.workspace.git import GitWorkspaceProvider, get_git_provider
from backend.workspace.exceptions import (
    WorkspaceError,
    GitError,
    InvalidWorkspaceNameError,
    WorkspacePathEscapeError,
    WorkspaceAlreadyExistsError,
    WorkspaceNotFoundError,
    ProjectRepositoryNotFoundError,
)

logger = logging.getLogger("codex_os.workspace.manager")

# Safe workspace name pattern: alphanumeric start, only alphanumeric, dashes, and underscores
WORKSPACE_NAME_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")

class WorkspaceManager:
    """
    Coordinates isolated Git worktree workspace creation, removal, path safety,
    and state transitions.
    """

    @staticmethod
    def validate_workspace_name(name: str) -> str:
        """Validate workspace name to prevent path traversal and shell injection."""
        if not name or not isinstance(name, str):
            raise InvalidWorkspaceNameError("Workspace name must be a non-empty string.")

        name = name.strip()
        if not WORKSPACE_NAME_REGEX.match(name):
            raise InvalidWorkspaceNameError(
                f"Invalid workspace name '{name}'. Names must start with an alphanumeric character "
                "and contain only alphanumeric characters, hyphens, and underscores (max 64 chars)."
            )

        if ".." in name or "/" in name or "\\" in name:
            raise WorkspacePathEscapeError("Workspace name cannot contain path separators or parent directory references.")

        return name

    @staticmethod
    def resolve_workspace_path(project_id: int, workspace_name: str) -> str:
        """
        Derive an absolute filesystem path strictly contained within CODEX_WORKSPACE_ROOT.
        """
        root = Path(settings.CODEX_WORKSPACE_ROOT).resolve()
        project_dir = (root / f"project-{project_id}").resolve()
        target_path = (project_dir / workspace_name).resolve()

        # Enforce that target_path is strictly within project_dir and root
        try:
            target_path.relative_to(project_dir)
        except ValueError:
            raise WorkspacePathEscapeError(f"Workspace path '{target_path}' escapes the project directory '{project_dir}'.")

        return str(target_path)

    @staticmethod
    def generate_branch_name(workspace_name: str) -> str:
        """Generate a deterministic Git branch name for the workspace."""
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "-", workspace_name)
        return f"codex/workspace/{sanitized}"

    @classmethod
    def create_workspace(
        cls,
        db: Session,
        project_id: int,
        name: str,
        git_provider: Optional[GitWorkspaceProvider] = None
    ) -> Workspace:
        """
        Create a new isolated Git worktree workspace for the specified project.
        """
        provider = git_provider or get_git_provider()

        # 1. Validate project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise WorkspaceNotFoundError(f"Project with ID {project_id} not found.")

        # 2. Validate project primary repository path exists on disk
        if not os.path.exists(project.repository_path) or not os.path.isdir(project.repository_path):
            raise ProjectRepositoryNotFoundError(
                f"Project primary repository path does not exist: {project.repository_path}"
            )

        # 3. Validate workspace name
        clean_name = cls.validate_workspace_name(name)

        # 4. Check if active workspace with same name exists for this project
        existing = (
            db.query(Workspace)
            .filter(
                Workspace.project_id == project_id,
                Workspace.name == clean_name,
                Workspace.status != WorkspaceStatus.REMOVED.value
            )
            .first()
        )
        if existing:
            raise WorkspaceAlreadyExistsError(
                f"Active workspace '{clean_name}' already exists for project {project_id}."
            )

        # 5. Resolve path and branch
        worktree_path = cls.resolve_workspace_path(project_id, clean_name)
        branch_name = cls.generate_branch_name(clean_name)

        logger.info(f"Creating workspace '{clean_name}' for project {project_id} at '{worktree_path}'")

        # 6. Create initial database record in CREATING state
        workspace = Workspace(
            project_id=project_id,
            name=clean_name,
            path=worktree_path,
            branch_name=branch_name,
            status=WorkspaceStatus.CREATING.value,
            error_message=None
        )
        db.add(workspace)
        db.commit()
        db.refresh(workspace)

        # 7. Create Git worktree via provider
        try:
            provider.create_worktree(
                repo_path=project.repository_path,
                worktree_path=worktree_path,
                branch_name=branch_name
            )
            workspace.status = WorkspaceStatus.READY.value
            workspace.error_message = None
            db.commit()
            db.refresh(workspace)
            logger.info(f"Workspace {workspace.id} created successfully with branch '{branch_name}'.")
            return workspace
        except Exception as exc:
            logger.exception(f"Failed to create Git worktree for workspace {workspace.id}: {exc}")
            workspace.status = WorkspaceStatus.ERROR.value
            workspace.error_message = str(exc)
            db.commit()
            db.refresh(workspace)
            raise

    @classmethod
    def remove_workspace(
        cls,
        db: Session,
        workspace_id: int,
        git_provider: Optional[GitWorkspaceProvider] = None
    ) -> Workspace:
        """
        Safely remove an isolated Git worktree workspace.
        """
        provider = git_provider or get_git_provider()

        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise WorkspaceNotFoundError(f"Workspace with ID {workspace_id} not found.")

        if workspace.status == WorkspaceStatus.REMOVED.value:
            return workspace

        # Check if active runs are executing in this workspace
        active_run = (
            db.query(EngineeringRun)
            .filter(
                EngineeringRun.workspace_id == workspace_id,
                EngineeringRun.status.in_(["STARTING", "RUNNING"])
            )
            .first()
        )
        if active_run:
            raise WorkspaceError(
                f"Cannot remove workspace {workspace_id} while run #{active_run.id} is actively running inside it."
            )

        project = db.query(Project).filter(Project.id == workspace.project_id).first()

        logger.info(f"Removing workspace {workspace_id} ('{workspace.name}') at '{workspace.path}'")
        workspace.status = WorkspaceStatus.REMOVING.value
        db.commit()

        try:
            if project and os.path.exists(project.repository_path):
                provider.remove_worktree(
                    repo_path=project.repository_path,
                    worktree_path=workspace.path,
                    force=True
                )
            workspace.status = WorkspaceStatus.REMOVED.value
            workspace.deleted_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(workspace)
            logger.info(f"Workspace {workspace_id} removed successfully.")
            return workspace
        except Exception as exc:
            logger.exception(f"Failed to remove Git worktree for workspace {workspace_id}: {exc}")
            workspace.status = WorkspaceStatus.ERROR.value
            workspace.error_message = str(exc)
            db.commit()
            db.refresh(workspace)
            raise

    @staticmethod
    def list_workspaces(db: Session, project_id: int) -> List[dict]:
        """List all non-removed workspaces for a project with active run counts."""
        workspaces = (
            db.query(Workspace)
            .filter(
                Workspace.project_id == project_id,
                Workspace.status != WorkspaceStatus.REMOVED.value
            )
            .order_by(Workspace.created_at.desc())
            .all()
        )
        result = []
        for w in workspaces:
            active_runs = (
                db.query(EngineeringRun)
                .filter(
                    EngineeringRun.workspace_id == w.id,
                    EngineeringRun.status.in_(["STARTING", "RUNNING"])
                )
                .count()
            )
            result.append({
                "id": w.id,
                "project_id": w.project_id,
                "name": w.name,
                "path": w.path,
                "branch_name": w.branch_name,
                "status": w.status,
                "error_message": w.error_message,
                "created_at": w.created_at,
                "updated_at": w.updated_at,
                "deleted_at": w.deleted_at,
                "active_runs_count": active_runs
            })
        return result

    @staticmethod
    def get_workspace_by_id(db: Session, workspace_id: int) -> Optional[dict]:
        """Fetch a single workspace by ID with active run count."""
        w = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not w:
            return None
        active_runs = (
            db.query(EngineeringRun)
            .filter(
                EngineeringRun.workspace_id == w.id,
                EngineeringRun.status.in_(["STARTING", "RUNNING"])
            )
            .count()
        )
        return {
            "id": w.id,
            "project_id": w.project_id,
            "name": w.name,
            "path": w.path,
            "branch_name": w.branch_name,
            "status": w.status,
            "error_message": w.error_message,
            "created_at": w.created_at,
            "updated_at": w.updated_at,
            "deleted_at": w.deleted_at,
            "active_runs_count": active_runs
        }
