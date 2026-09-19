from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models.project import Project
from backend.models.run import EngineeringRun
from backend.schemas.project import ProjectCreate, ProjectResponse
from backend.schemas.run import RunCreate

class ProjectService:
    @staticmethod
    def get_projects(db: Session) -> List[dict]:
        """Fetch all projects along with run count."""
        projects = db.query(Project).order_by(Project.created_at.desc()).all()
        result = []
        for p in projects:
            p_dict = {
                "id": p.id,
                "name": p.name,
                "repository_path": p.repository_path,
                "description": p.description,
                "status": p.status,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "runs_count": len(p.runs)
            }
            result.append(p_dict)
        return result

    @staticmethod
    def get_project_by_id(db: Session, project_id: int) -> Optional[dict]:
        """Fetch a single project by id."""
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None
        return {
            "id": project.id,
            "name": project.name,
            "repository_path": project.repository_path,
            "description": project.description,
            "status": project.status,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "runs_count": len(project.runs)
        }

    @staticmethod
    def create_project(db: Session, project_in: ProjectCreate) -> dict:
        """Create a new project."""
        db_project = Project(
            name=project_in.name.strip(),
            repository_path=project_in.repository_path.strip(),
            description=project_in.description.strip() if project_in.description else None,
            status="ACTIVE"
        )
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return {
            "id": db_project.id,
            "name": db_project.name,
            "repository_path": db_project.repository_path,
            "description": db_project.description,
            "status": db_project.status,
            "created_at": db_project.created_at,
            "updated_at": db_project.updated_at,
            "runs_count": 0
        }

    @staticmethod
    def delete_project(db: Session, project_id: int) -> bool:
        """Delete a project and all associated runs."""
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return False
        db.delete(project)
        db.commit()
        return True

    @staticmethod
    def get_project_runs(db: Session, project_id: int) -> List[EngineeringRun]:
        """Fetch all engineering runs for a given project."""
        return (
            db.query(EngineeringRun)
            .filter(EngineeringRun.project_id == project_id)
            .order_by(EngineeringRun.created_at.desc())
            .all()
        )

    @staticmethod
    def create_run(db: Session, project_id: int, run_in: RunCreate) -> EngineeringRun:
        """Create an engineering run record for a project."""
        run = EngineeringRun(
            project_id=project_id,
            goal=run_in.goal.strip(),
            status=run_in.status or "PENDING",
            target_subpath=run_in.target_subpath.strip() if run_in.target_subpath else None,
            workspace_id=run_in.workspace_id,
            sandbox_id=run_in.sandbox_id
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    @staticmethod
    def get_run_by_id(db: Session, run_id: int) -> Optional[EngineeringRun]:
        """Fetch an engineering run by its ID."""
        return db.query(EngineeringRun).filter(EngineeringRun.id == run_id).first()
