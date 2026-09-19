class WorkspaceError(Exception):
    """Base exception for workspace operations."""
    pass

class GitError(WorkspaceError):
    """Raised when a Git command execution fails."""
    def __init__(self, message: str, exit_code: int = -1, stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr

class InvalidWorkspaceNameError(WorkspaceError):
    """Raised when an unsafe or invalid workspace name is provided."""
    pass

class WorkspacePathEscapeError(WorkspaceError):
    """Raised when a workspace path attempts to escape the configured root."""
    pass

class WorkspaceAlreadyExistsError(WorkspaceError):
    """Raised when a workspace with the given name already exists for the project."""
    pass

class WorkspaceNotFoundError(WorkspaceError):
    """Raised when the requested workspace does not exist."""
    pass

class ProjectRepositoryNotFoundError(WorkspaceError):
    """Raised when the project primary repository path does not exist on disk."""
    pass
