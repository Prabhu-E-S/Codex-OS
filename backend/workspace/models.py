from dataclasses import dataclass
from enum import Enum
from typing import Optional

class WorkspaceStatus(str, Enum):
    CREATING = "CREATING"
    READY = "READY"
    IN_USE = "IN_USE"
    ERROR = "ERROR"
    REMOVING = "REMOVING"
    REMOVED = "REMOVED"

@dataclass
class WorktreeInfo:
    path: str
    branch: str
    commit_hash: Optional[str] = None
    is_bare: bool = False
    is_clean: bool = True
