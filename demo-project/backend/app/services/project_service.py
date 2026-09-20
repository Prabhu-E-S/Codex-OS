from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.project import Project
from app.models.user import User
from app.models.task import Task
from app.schemas.project import ProjectCreate, ProjectUpdate

class ProjectService:
    @staticmethod
    def create_project(db: Session, project_in: ProjectCreate) -> Project:
        owner = db.query(User).filter(User.id == project_in.owner_id).first()
        if not owner:
            raise ValueError(f"Owner with id {project_in.owner_id} does not exist.")

        project = Project(
            name=project_in.name,
            description=project_in.description,
            status=project_in.status,
            owner_id=project_in.owner_id
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def get_project_by_id(db: Session, project_id: int) -> Optional[Project]:
        return db.query(Project).filter(Project.id == project_id).first()

    @staticmethod
    def list_projects(db: Session, skip: int = 0, limit: int = 100) -> List[Tuple[Project, int]]:
        """Return list of (project, task_count) tuples."""
        subquery = (
            db.query(Task.project_id, func.count(Task.id).label("task_count"))
            .group_by(Task.project_id)
            .subquery()
        )
        results = (
            db.query(Project, func.coalesce(subquery.c.task_count, 0))
            .outerjoin(subquery, Project.id == subquery.c.project_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
        return results

    @staticmethod
    def update_project(db: Session, project: Project, project_in: ProjectUpdate) -> Project:
        update_data = project_in.model_dump(exclude_unset=True)
        if "owner_id" in update_data and update_data["owner_id"]:
            owner = db.query(User).filter(User.id == update_data["owner_id"]).first()
            if not owner:
                raise ValueError(f"Owner with id {update_data['owner_id']} does not exist.")

        for field, value in update_data.items():
            setattr(project, field, value)

        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete_project(db: Session, project: Project) -> None:
        db.delete(project)
        db.commit()
