from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class EngineeringRun(Base):
    __tablename__ = "engineering_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="PENDING")
    goal = Column(Text, nullable=False)

    # Execution tracking fields (Phase 2)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    exit_code = Column(Integer, nullable=True)
    stdout = Column(Text, default="", nullable=False)
    stderr = Column(Text, default="", nullable=False)
    error_message = Column(Text, nullable=True)

    # Workspace relationship (Phase 3)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)

    # Sandbox relationship (Phase 4)
    sandbox_id = Column(Integer, ForeignKey("sandboxes.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    project = relationship("Project", back_populates="runs")
    workspace = relationship("Workspace", back_populates="runs")
    sandbox = relationship("Sandbox", back_populates="runs")
    agent_executions = relationship(
        "AgentExecution",
        back_populates="engineering_run",
        cascade="all, delete-orphan",
        order_by="AgentExecution.id"
    )
    findings = relationship(
        "Finding",
        back_populates="engineering_run",
        cascade="all, delete-orphan",
        order_by="Finding.id"
    )
    orchestration_state = relationship(
        "OrchestrationState",
        back_populates="engineering_run",
        uselist=False,
        cascade="all, delete-orphan"
    )

    @property
    def workspace_name(self) -> str | None:
        return self.workspace.name if self.workspace else None


