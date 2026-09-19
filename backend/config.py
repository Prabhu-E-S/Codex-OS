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

    # Security Scanner Engine (Phase 6)
    SECURITY_SCANNING_ENABLED: bool = os.getenv("SECURITY_SCANNING_ENABLED", "true").lower() in ("true", "1", "yes")
    SECURITY_SCANNERS: str = os.getenv("SECURITY_SCANNERS", "pattern_scanner,bandit,pip-audit,npm-audit,semgrep,gitleaks")
    SECURITY_SCAN_NETWORK: bool = os.getenv("SECURITY_SCAN_NETWORK", "false").lower() in ("true", "1", "yes")

    # Autonomous Orchestrator (Phase 7)
    ORCHESTRATOR_ENABLED: bool = os.getenv("ORCHESTRATOR_ENABLED", "true").lower() in ("true", "1", "yes")
    ORCHESTRATOR_DEFAULT_MAX_ITERATIONS: int = int(os.getenv("ORCHESTRATOR_DEFAULT_MAX_ITERATIONS", "3"))
    ORCHESTRATOR_MAX_ITERATIONS_LIMIT: int = int(os.getenv("ORCHESTRATOR_MAX_ITERATIONS_LIMIT", "10"))
    ORCHESTRATOR_DEFAULT_AGENT_TIMEOUT: int = int(os.getenv("ORCHESTRATOR_DEFAULT_AGENT_TIMEOUT", "900"))
    ORCHESTRATOR_TOTAL_RUN_TIMEOUT: int = int(os.getenv("ORCHESTRATOR_TOTAL_RUN_TIMEOUT", "3600"))

    # Evaluation & Engineering Score (Phase 8)
    EVALUATION_ENABLED: bool = os.getenv("EVALUATION_ENABLED", "true").lower() in ("true", "1", "yes")
    EVALUATION_SCORE_VERSION: str = os.getenv("EVALUATION_SCORE_VERSION", "v1")
    EVALUATION_WEIGHT_CORRECTNESS: float = float(os.getenv("EVALUATION_WEIGHT_CORRECTNESS", "0.30"))
    EVALUATION_WEIGHT_TEST_COVERAGE: float = float(os.getenv("EVALUATION_WEIGHT_TEST_COVERAGE", "0.15"))
    EVALUATION_WEIGHT_SECURITY: float = float(os.getenv("EVALUATION_WEIGHT_SECURITY", "0.20"))
    EVALUATION_WEIGHT_MAINTAINABILITY: float = float(os.getenv("EVALUATION_WEIGHT_MAINTAINABILITY", "0.15"))
    EVALUATION_WEIGHT_PERFORMANCE: float = float(os.getenv("EVALUATION_WEIGHT_PERFORMANCE", "0.10"))
    EVALUATION_WEIGHT_REGRESSION_RISK: float = float(os.getenv("EVALUATION_WEIGHT_REGRESSION_RISK", "0.10"))

    def get_evaluation_weights(self) -> dict[str, float]:
        weights = {
            "CORRECTNESS": self.EVALUATION_WEIGHT_CORRECTNESS,
            "TEST_COVERAGE": self.EVALUATION_WEIGHT_TEST_COVERAGE,
            "SECURITY": self.EVALUATION_WEIGHT_SECURITY,
            "MAINTAINABILITY": self.EVALUATION_WEIGHT_MAINTAINABILITY,
            "PERFORMANCE": self.EVALUATION_WEIGHT_PERFORMANCE,
            "REGRESSION_RISK": self.EVALUATION_WEIGHT_REGRESSION_RISK,
        }
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-5:
            raise ValueError(f"Evaluation weights must sum to 1.0; got {total:.4f}")
        return weights

    class Config:
        case_sensitive = True

settings = Settings()
