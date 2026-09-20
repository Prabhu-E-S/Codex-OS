from fastapi import APIRouter
from app.api.users import router as users_router
from app.api.projects import router as projects_router
from app.api.tasks import router as tasks_router
from app.api.dashboard import router as dashboard_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(users_router)
api_router.include_router(projects_router)
api_router.include_router(tasks_router)
api_router.include_router(dashboard_router)
