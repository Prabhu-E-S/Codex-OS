import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.config import settings

logger = logging.getLogger("codex_os.database")

# Handle SQLite vs PostgreSQL arguments
connect_args = {}
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

try:
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        pool_pre_ping=True
    )
except Exception as e:
    logger.error(f"Failed to initialize engine with {db_url}: {e}. Falling back to SQLite.")
    engine = create_engine(
        "sqlite:///./codex_os.db",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency that yields a database session and ensures closure."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connection() -> tuple[bool, str]:
    """Test database connectivity with a lightweight query."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        dialect = engine.dialect.name
        return True, dialect
    except Exception as exc:
        logger.warning(f"Database health check failed: {exc}")
        return False, str(exc)
