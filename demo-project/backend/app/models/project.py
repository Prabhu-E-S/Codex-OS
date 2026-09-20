from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.models.base import TimestampMixin

class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="active", nullable=False)  # active, completed, archived
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="owned_projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
