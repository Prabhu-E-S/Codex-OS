from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    engineering_run_id = Column(Integer, ForeignKey("engineering_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    agent_type = Column(String(50), nullable=False)  # ARCHITECT, BUILDER, TESTER
    agent_name = Column(String(100), nullable=False)

    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    sandbox_id = Column(Integer, ForeignKey("sandboxes.id", ondelete="SET NULL"), nullable=True, index=True)

    status = Column(String(50), nullable=False, default="PENDING")  # PENDING, STARTING, RUNNING, COMPLETED, FAILED, CANCELLED

    input_summary = Column(Text, nullable=True)
    output = Column(Text, default="", nullable=False)
    error_message = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    engineering_run = relationship("EngineeringRun", back_populates="agent_executions")
    workspace = relationship("Workspace")
    sandbox = relationship("Sandbox")

    @property
    def workspace_name(self) -> str | None:
        return self.workspace.name if self.workspace else None
