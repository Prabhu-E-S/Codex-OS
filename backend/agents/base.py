from abc import ABC, abstractmethod
import logging
from backend.agents.models import AgentType, AgentResult
from backend.agents.context import AgentContext

logger = logging.getLogger("codex_os.agents.base")

class BaseAgent(ABC):
    """
    Abstract base class for all Codex OS agents.
    Defines common metadata, lifecycle, and execution interface.
    Every future agent (Architect, Builder, Tester) follows this contract.
    """
    agent_type: AgentType
    name: str
    role: str
    description: str

    def __init__(self):
        if not hasattr(self, "agent_type"):
            raise NotImplementedError("Subclasses of BaseAgent must define agent_type.")
        if not hasattr(self, "name"):
            self.name = self.agent_type.value.capitalize() + " Agent"
        if not hasattr(self, "role"):
            self.role = self.name
        if not hasattr(self, "description"):
            self.description = ""

    @abstractmethod
    def run(self, context: AgentContext) -> AgentResult:
        """
        Execute the agent's task within the provided AgentContext.
        Returns an AgentResult capturing status, output, and diagnostics.
        """
        pass
