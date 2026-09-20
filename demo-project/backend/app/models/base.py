from datetime import datetime, timezone
from sqlalchemy import Column, DateTime
from app.database.session import Base

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
