from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class OrchestrationState(Base):
    __tablename__ = "orchestration_states"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    engineering_run_id = Column(
        Integer,
        ForeignKey("engineering_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Workflow state: PENDING, ARCHITECTING, BUILDING, TESTING, BREAKING, SECURITY_SCANNING, DECIDING, ITERATING, COMPLETED, FAILED, CANCELLED, PAUSED
    state = Column(String(50), nullable=False, default="PENDING", index=True)
    current_agent = Column(String(50), nullable=True)
    iteration = Column(Integer, nullable=False, default=1)
    max_iterations = Column(Integer, nullable=False, default=3)

    # Last decision & transparent reason
    last_decision = Column(String(50), nullable=True)
    last_decision_reason = Column(Text, nullable=True)

    # Boundary control flags
    pause_requested = Column(Boolean, nullable=False, default=False)
    cancel_requested = Column(Boolean, nullable=False, default=False)

    # Lightweight event log stored as serialized JSON array
    events_json = Column(Text, nullable=False, default="[]")

    failure_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationship
    engineering_run = relationship("EngineeringRun", back_populates="orchestration_state")
