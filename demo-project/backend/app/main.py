import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.database.session import init_db
from app.api.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    yield

app = FastAPI(
    title="TaskForge API",
    description="Full-stack Task Management and Project Tracking REST API for Codex OS testing.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000")
origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 routes
app.include_router(api_router)

@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for container probes and testing."""
    return {"status": "healthy", "service": "taskforge-backend", "version": "1.0.0"}

@app.get("/", tags=["Root"])
def root():
    """API root redirect information."""
    return {
        "message": "Welcome to TaskForge API",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
        "health_check": "/health"
    }
