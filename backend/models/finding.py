from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    engineering_run_id = Column(Integer, ForeignKey("engineering_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_execution_id = Column(Integer, ForeignKey("agent_executions.id", ondelete="SET NULL"), nullable=True, index=True)

    # Type: BREAKER or SECURITY
    type = Column(String(50), nullable=False, index=True)

    # Severity: INFO, LOW, MEDIUM, HIGH, CRITICAL
    severity = Column(String(50), nullable=False, index=True)

    # Category: EDGE_CASE, INPUT_VALIDATION, ERROR_HANDLING, SECRET, INJECTION, etc.
    category = Column(String(50), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    file_path = Column(String(500), nullable=True)
    line_number = Column(Integer, nullable=True)

    evidence = Column(Text, nullable=True)
    reproduction = Column(Text, nullable=True)
    remediation = Column(Text, nullable=True)

    # Status: OPEN, CONFIRMED, RESOLVED, DISMISSED
    status = Column(String(50), nullable=False, default="OPEN")
    iteration = Column(Integer, nullable=False, default=1)
    resolved_iteration = Column(Integer, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    engineering_run = relationship("EngineeringRun", back_populates="findings")
    agent_execution = relationship("AgentExecution", back_populates="findings")
