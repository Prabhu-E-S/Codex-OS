class OrchestratorError(Exception):
    """Base exception for all orchestration subsystem errors."""
    pass


class InvalidStateTransitionError(OrchestratorError):
    """Raised when an illegal workflow state transition is attempted."""
    def __init__(self, current_state: str, target_state: str, reason: str = ""):
        message = f"Invalid state transition from {current_state} to {target_state}"
        if reason:
            message += f": {reason}"
        super().__init__(message)
        self.current_state = current_state
        self.target_state = target_state


class MaxIterationsReachedError(OrchestratorError):
    """Raised when the maximum configured iteration limit is exceeded."""
    def __init__(self, run_id: int, max_iterations: int):
        super().__init__(f"Run {run_id} reached max iteration limit of {max_iterations}")
        self.run_id = run_id
        self.max_iterations = max_iterations
