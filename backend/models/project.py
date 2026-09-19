from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from backend.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    repository_path = Column(String(1024), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationship to Engineering Runs
    runs = relationship(
        "EngineeringRun",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(EngineeringRun.created_at)"
    )

    # Relationship to Workspaces (Phase 3)
    workspaces = relationship(
        "Workspace",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(Workspace.created_at)"
    )

