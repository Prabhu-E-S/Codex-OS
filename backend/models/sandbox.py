from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class Sandbox(Base):
    __tablename__ = "sandboxes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)

    container_id = Column(String(128), nullable=True, index=True)
    image = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="CREATING")  # CREATING, CREATED, STARTING, RUNNING, STOPPING, STOPPED, FAILED, REMOVED

    # Resource & Security specifications
    cpu_limit = Column(Float, nullable=False, default=1.0)
    memory_limit = Column(String(50), nullable=False, default="512m")
    timeout_seconds = Column(Integer, nullable=False, default=60)
    network_enabled = Column(Boolean, nullable=False, default=False)
    pids_limit = Column(Integer, nullable=False, default=128)

    exit_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    workspace = relationship("Workspace", back_populates="sandboxes")
    runs = relationship("EngineeringRun", back_populates="sandbox")
