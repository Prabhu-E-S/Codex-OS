from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.models.base import TimestampMixin

class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="todo", nullable=False, index=True)  # todo, in_progress, review, done
    priority = Column(String(50), default="medium", nullable=False, index=True)  # low, medium, high, urgent
    due_date = Column(DateTime, nullable=True, index=True)
    
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Relationships
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="assigned_tasks")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")
