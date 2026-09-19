import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Search for .env in current directory or parent directory
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Codex OS"
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"
    
    # Database URL: default to SQLite if not provided or if postgres is not yet configured
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./codex_os.db")
    
    # Server settings
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"
    ]

    # Codex Execution Engine (Phase 2)
    CODEX_COMMAND: str | None = os.getenv("CODEX_COMMAND", None)
    CODEX_EXECUTION_TIMEOUT: int = int(os.getenv("CODEX_EXECUTION_TIMEOUT", "900"))

    # Git Worktree System (Phase 3)
    CODEX_WORKSPACE_ROOT: str = os.getenv("CODEX_WORKSPACE_ROOT", "./workspaces")
    CODEX_GIT_PROVIDER: str = os.getenv("CODEX_GIT_PROVIDER", "real")

    # Docker Sandbox Engine (Phase 4)
    DOCKER_SANDBOX_IMAGE: str = os.getenv("DOCKER_SANDBOX_IMAGE", "python:3.12-slim")
    DOCKER_SANDBOX_CPU_LIMIT: float = float(os.getenv("DOCKER_SANDBOX_CPU_LIMIT", "1.0"))
    DOCKER_SANDBOX_MEMORY_LIMIT: str = os.getenv("DOCKER_SANDBOX_MEMORY_LIMIT", "512m")
    DOCKER_SANDBOX_TIMEOUT: int = int(os.getenv("DOCKER_SANDBOX_TIMEOUT", "60"))
    DOCKER_SANDBOX_NETWORK: str = os.getenv("DOCKER_SANDBOX_NETWORK", "none")
    DOCKER_SANDBOX_PIDS_LIMIT: int = int(os.getenv("DOCKER_SANDBOX_PIDS_LIMIT", "128"))
    DOCKER_SANDBOX_PROVIDER: str = os.getenv("DOCKER_SANDBOX_PROVIDER", "real")
    DOCKER_SANDBOX_USER: str | None = os.getenv("DOCKER_SANDBOX_USER", None)

    class Config:

        case_sensitive = True

settings = Settings()
