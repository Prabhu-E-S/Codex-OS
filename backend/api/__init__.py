from fastapi import APIRouter
from backend.api.health import router as health_router
from backend.api.projects import router as projects_router
from backend.api.runs import router as runs_router
from backend.api.workspaces import router as workspaces_router
from backend.api.sandboxes import router as sandboxes_router
from backend.api.agents import router as agents_router
from backend.api.findings import router as findings_router
from backend.api.orchestration import router as orchestration_router
from backend.api.evaluations import router as evaluations_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(projects_router)
api_router.include_router(runs_router)
api_router.include_router(workspaces_router)
api_router.include_router(sandboxes_router)
api_router.include_router(agents_router)
api_router.include_router(findings_router)
api_router.include_router(orchestration_router)
api_router.include_router(evaluations_router)

__all__ = ["api_router"]

