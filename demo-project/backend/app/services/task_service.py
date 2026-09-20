from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from app.models.task import Task
from app.models.project import Project
from app.models.user import User
from app.models.comment import Comment
from app.schemas.task import TaskCreate, TaskUpdate

class TaskService:
    @staticmethod
    def is_task_overdue(task: Task) -> bool:
        if not task.due_date or task.status == "done":
            return False
        # Normalize comparison to UTC
        due = task.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        return due < datetime.now(timezone.utc)

    @staticmethod
    def create_task(db: Session, task_in: TaskCreate) -> Task:
        # Verify project exists
        project = db.query(Project).filter(Project.id == task_in.project_id).first()
        if not project:
            raise ValueError(f"Project with id {task_in.project_id} does not exist.")

        # Verify assignee if provided
        if task_in.assignee_id:
            assignee = db.query(User).filter(User.id == task_in.assignee_id).first()
            if not assignee:
                raise ValueError(f"Assignee with id {task_in.assignee_id} does not exist.")

        task = Task(
            title=task_in.title,
            description=task_in.description,
            status=task_in.status,
            priority=task_in.priority,
            due_date=task_in.due_date,
            project_id=task_in.project_id,
            assignee_id=task_in.assignee_id
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def get_task_by_id(db: Session, task_id: int) -> Optional[Task]:
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    def list_tasks(
        db: Session,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        project_id: Optional[int] = None,
        assignee_id: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Tuple[Task, int]]:
        """
        List tasks with filtering and returns a tuple of (Task, comment_count).
        """
        # Comment count subquery
        comment_subquery = (
            db.query(Comment.task_id, func.count(Comment.id).label("comment_count"))
            .group_by(Comment.task_id)
            .subquery()
        )

        query = (
            db.query(Task, func.coalesce(comment_subquery.c.comment_count, 0))
            .outerjoin(comment_subquery, Task.id == comment_subquery.c.task_id)
        )

        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
        if project_id:
            query = query.filter(Task.project_id == project_id)
        if assignee_id:
            query = query.filter(Task.assignee_id == assignee_id)
        if search:
            search_terms = search.strip().split()
            if search_terms:
                query = query.filter(
                    and_(
                        *(
                            or_(
                                Task.title.ilike(f"%{term}%"),
                                Task.description.ilike(f"%{term}%")
                            )
                            for term in search_terms
                        )
                    )
                )

        # Order by priority weight or due_date or created_at desc
        query = query.order_by(Task.created_at.desc())
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def update_task(db: Session, task: Task, task_in: TaskUpdate) -> Task:
        update_data = task_in.model_dump(exclude_unset=True)

        if "project_id" in update_data and update_data["project_id"] is not None:
            project = db.query(Project).filter(Project.id == update_data["project_id"]).first()
            if not project:
                raise ValueError(f"Project with id {update_data['project_id']} does not exist.")

        if "assignee_id" in update_data and update_data["assignee_id"] is not None:
            assignee = db.query(User).filter(User.id == update_data["assignee_id"]).first()
            if not assignee:
                raise ValueError(f"Assignee with id {update_data['assignee_id']} does not exist.")

        for field, value in update_data.items():
            setattr(task, field, value)

        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def delete_task(db: Session, task: Task) -> None:
        db.delete(task)
        db.commit()
