import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.database import Base, engine
from backend.api import api_router
import backend.models  # Ensure models are imported so Base.metadata knows them

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("codex_os")

def _migrate_schema():
    """Ensure newly added columns exist in existing database schemas."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        if "engineering_runs" in inspector.get_table_names():
            existing_cols = {col["name"] for col in inspector.get_columns("engineering_runs")}
            new_columns = [
                ("started_at", "DATETIME"),
                ("completed_at", "DATETIME"),
                ("exit_code", "INTEGER"),
                ("stdout", "TEXT DEFAULT ''"),
                ("stderr", "TEXT DEFAULT ''"),
                ("error_message", "TEXT"),
                ("target_subpath", "VARCHAR(500)"),
                ("workspace_id", "INTEGER"),
                ("sandbox_id", "INTEGER"),
            ]
            with engine.connect() as conn:
                for col_name, col_type in new_columns:
                    if col_name not in existing_cols:
                        try:
                            conn.execute(text(f"ALTER TABLE engineering_runs ADD COLUMN {col_name} {col_type}"))
                            conn.commit()
                            logger.info(f"Schema migrated: added column '{col_name}' to engineering_runs")
                        except Exception as exc:
                            logger.warning(f"Failed to add column {col_name}: {exc}")

        if "agent_executions" in inspector.get_table_names():
            ae_cols = {col["name"] for col in inspector.get_columns("agent_executions")}
            if "iteration" not in ae_cols:
                with engine.connect() as conn:
                    try:
                        conn.execute(text("ALTER TABLE agent_executions ADD COLUMN iteration INTEGER DEFAULT 1"))
                        conn.commit()
                        logger.info("Schema migrated: added column 'iteration' to agent_executions")
                    except Exception as exc:
                        logger.warning(f"Failed to add iteration to agent_executions: {exc}")

        if "findings" in inspector.get_table_names():
            finding_cols = {col["name"] for col in inspector.get_columns("findings")}
            if "iteration" not in finding_cols:
                with engine.connect() as conn:
                    try:
                        conn.execute(text("ALTER TABLE findings ADD COLUMN iteration INTEGER DEFAULT 1"))
                        conn.commit()
                        logger.info("Schema migrated: added column 'iteration' to findings")
                    except Exception as exc:
                        logger.warning(f"Failed to add iteration to findings: {exc}")
            if "resolved_iteration" not in finding_cols:
                with engine.connect() as conn:
                    try:
                        conn.execute(text("ALTER TABLE findings ADD COLUMN resolved_iteration INTEGER NULL"))
                        conn.commit()
                        logger.info("Schema migrated: added column 'resolved_iteration' to findings")
                    except Exception as exc:
                        logger.warning(f"Failed to add resolved_iteration to findings: {exc}")
            if "resolved_at" not in finding_cols:
                with engine.connect() as conn:
                    try:
                        conn.execute(text("ALTER TABLE findings ADD COLUMN resolved_at TIMESTAMP NULL"))
                        conn.commit()
                        logger.info("Schema migrated: added column 'resolved_at' to findings")
                    except Exception as exc:
                        logger.warning(f"Failed to add resolved_at to findings: {exc}")
    except Exception as e:
        logger.warning(f"Schema migration check skipped: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for setup and teardown."""
    logger.info("Initializing Codex OS Database schema...")
    try:
        Base.metadata.create_all(bind=engine)
        _migrate_schema()
        logger.info("Database tables verified/created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
    yield
    logger.info("Codex OS backend shutting down.")
    try:
        from backend.codex.process import process_manager
        with process_manager._global_lock:
            active_runs = list(process_manager._processes.keys())
        for run_id in active_runs:
            logger.warning(f"Cancelling orphaned Codex process for run {run_id} on shutdown.")
            process_manager.cancel(run_id)
    except Exception as e:
        logger.error(f"Error during shutdown cleanup: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Codex OS — The Autonomous Software Engineering Sandbox (Phase 10: Final Hardening, Demo & Deployment Readiness)",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix=settings.API_PREFIX)

@app.get("/")
def root():
    """Root entry point with service metadata."""
    return {
        "service": "Codex OS API",
        "version": settings.VERSION,
        "phase": 10,
        "docs_url": "/docs",
        "health_url": f"{settings.API_PREFIX}/health"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return structured JSON."""
    logger.exception(f"Unhandled error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected internal error occurred."
            }
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True
    )
