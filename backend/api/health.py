from fastapi import APIRouter
from backend.database import check_db_connection
from backend.sandbox.docker import get_docker_provider
from backend.codex.runner import CodexRunner

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
def get_health():
    """Health check endpoint to verify backend service and database connectivity."""
    db_ok, info = check_db_connection()
    docker_ok, docker_info = get_docker_provider().is_available()
    codex_ok, codex_cmd, codex_info = CodexRunner.is_available()

    overall_status = "ok" if (db_ok and docker_ok and codex_ok) else "degraded"

    return {
        "status": overall_status,
        "service": "codex-os",
        "version": "0.1.0",
        "phase": 10,
        "database": "connected" if db_ok else "disconnected",
        "database_dialect": info if db_ok else None,
        "database_error": None if db_ok else info,
        "docker": "available" if docker_ok else "unavailable",
        "docker_error": None if docker_ok else docker_info,
        "codex": "available" if codex_ok else "unavailable",
        "codex_command": codex_cmd,
        "codex_error": None if codex_ok else codex_info
    }
