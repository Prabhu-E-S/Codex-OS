from fastapi import APIRouter
from backend.database import check_db_connection

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
def get_health():
    """Health check endpoint to verify backend service and database connectivity."""
    db_ok, info = check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "service": "codex-os",
        "version": "0.1.0",
        "phase": 1,
        "database": "connected" if db_ok else "disconnected",
        "database_dialect": info if db_ok else None,
        "database_error": None if db_ok else info
    }
