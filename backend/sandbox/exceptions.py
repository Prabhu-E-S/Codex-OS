class SandboxError(Exception):
    """Base exception for all Docker sandbox subsystem errors."""
    pass


class DockerUnavailableError(SandboxError):
    """Raised when the Docker daemon is unreachable or Docker SDK is unavailable."""
    pass


class MountSecurityError(SandboxError):
    """Raised when a mount path violates isolation or security rules."""
    pass


class SandboxNotFoundError(SandboxError):
    """Raised when the requested sandbox does not exist."""
    pass


class ContainerCreationError(SandboxError):
    """Raised when Docker container creation fails."""
    pass


class ContainerStartError(SandboxError):
    """Raised when Docker container start fails."""
    pass


class ContainerStopError(SandboxError):
    """Raised when Docker container stop fails."""
    pass


class ContainerRemovalError(SandboxError):
    """Raised when Docker container removal fails."""
    pass


class CommandExecutionError(SandboxError):
    """Raised when command execution inside a container fails."""
    pass


class CommandTimeoutError(SandboxError):
    """Raised when command execution inside a container exceeds the timeout."""
    pass
