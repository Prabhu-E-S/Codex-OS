import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Determine database path
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/taskforge.db")

# Ensure directory exists for sqlite database if file-based
if DATABASE_URL.startswith("sqlite:///"):
    db_file_path = DATABASE_URL.replace("sqlite:///", "")
    if db_file_path and not db_file_path.startswith(":memory:"):
        db_path = Path(db_file_path)
        if not db_path.is_absolute():
            # If relative, resolve relative to project root or current working dir
            db_path = Path.cwd() / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

# Create SQLAlchemy engine
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """Initialize database tables."""
    # Import all models to ensure they are registered with Base.metadata
    from app.models import user, project, task, comment  # noqa: F401
    Base.metadata.create_all(bind=engine)
