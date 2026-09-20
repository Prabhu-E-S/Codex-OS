from datetime import datetime, timezone
from typing import Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.project import Project
from app.models.task import Task
from app.services.task_service import TaskService
from app.schemas.dashboard import DashboardStats
from app.schemas.task import TaskResponse
from app.schemas.project import ProjectResponse

class DashboardService:
    @staticmethod
    def get_stats(db: Session) -> DashboardStats:
        total_projects = db.query(func.count(Project.id)).scalar() or 0
        total_tasks = db.query(func.count(Task.id)).scalar() or 0
        completed_tasks = db.query(func.count(Task.id)).filter(Task.status == "done").scalar() or 0
        pending_tasks = total_tasks - completed_tasks

        # Overdue tasks calculation
        now_utc = datetime.now(timezone.utc)
        overdue_tasks = (
            db.query(func.count(Task.id))
            .filter(Task.due_date.isnot(None))
            .filter(Task.due_date < now_utc)
            .filter(Task.status != "done")
            .scalar() or 0
        )

        # Priority breakdown
        priority_counts: Dict[str, int] = {"low": 0, "medium": 0, "high": 0, "urgent": 0}
        priority_rows = db.query(Task.priority, func.count(Task.id)).group_by(Task.priority).all()
        for p, count in priority_rows:
            if p in priority_counts:
                priority_counts[p] = count

        # Status breakdown
        status_counts: Dict[str, int] = {"todo": 0, "in_progress": 0, "review": 0, "done": 0}
        status_rows = db.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
        for s, count in status_rows:
            if s in status_counts:
                status_counts[s] = count

        # Recent tasks (up to 5)
        recent_tasks_db = TaskService.list_tasks(db, limit=5)
        recent_task_responses = []
        for task, c_count in recent_tasks_db:
            resp = TaskResponse.model_validate(task)
            resp.project_name = task.project.name if task.project else None
            resp.is_overdue = TaskService.is_task_overdue(task)
            resp.comment_count = c_count
            recent_task_responses.append(resp)

        # Recent projects (up to 5)
        recent_projects_db = db.query(Project).order_by(Project.created_at.desc()).limit(5).all()
        recent_project_responses = []
        for proj in recent_projects_db:
            p_resp = ProjectResponse.model_validate(proj)
            p_resp.task_count = len(proj.tasks)
            recent_project_responses.append(p_resp)

        return DashboardStats(
            total_projects=total_projects,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            pending_tasks=pending_tasks,
            overdue_tasks=overdue_tasks,
            tasks_by_priority=priority_counts,
            tasks_by_status=status_counts,
            recent_tasks=recent_task_responses,
            recent_projects=recent_project_responses
        )
