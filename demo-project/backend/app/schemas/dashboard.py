from typing import Dict, List, Optional
from pydantic import BaseModel
from app.schemas.task import TaskResponse
from app.schemas.project import ProjectResponse

class DashboardStats(BaseModel):
    total_projects: int
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    overdue_tasks: int
    tasks_by_priority: Dict[str, int]
    tasks_by_status: Dict[str, int]
    recent_tasks: Optional[List[TaskResponse]] = []
    recent_projects: Optional[List[ProjectResponse]] = []
