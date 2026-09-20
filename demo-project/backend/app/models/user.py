from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.models.base import TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="member", nullable=False)  # admin, manager, member
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    owned_projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    assigned_tasks = relationship("Task", back_populates="assignee")
    comments = relationship("Comment", back_populates="author")
