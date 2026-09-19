class AgentError(Exception):
    """Base exception for all agent subsystem errors."""
    pass

class AgentNotFoundError(AgentError):
    """Raised when a requested agent or agent execution is not found."""
    pass

class AgentExecutionError(AgentError):
    """Raised when an error occurs during agent execution."""
    pass

class AgentWorkflowError(AgentError):
    """Raised when workflow validation or orchestration fails."""
    pass

class InvalidAgentContextError(AgentError):
    """Raised when required context items are missing or malformed."""
    pass

class AgentTimeoutError(AgentError):
    """Raised when agent execution exceeds its allocated time limit."""
    pass
