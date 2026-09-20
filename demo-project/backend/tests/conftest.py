import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.main import app
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.models.comment import Comment

# In-memory SQLite with StaticPool ensures all connections share the same memory DB
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="function")
def db_session():
    """Create fresh database tables for each test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(scope="function")
def client(db_session):
    """Dependency override fixture for FastAPI TestClient."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def sample_data(db_session):
    """Seed baseline user, project, task, and comment."""
    user1 = User(
        email="alice@example.com",
        full_name="Alice Architect",
        role="admin",
        is_active=True
    )
    user2 = User(
        email="bob@example.com",
        full_name="Bob Builder",
        role="member",
        is_active=True
    )
    db_session.add_all([user1, user2])
    db_session.commit()
    db_session.refresh(user1)
    db_session.refresh(user2)

    project = Project(
        name="Apollo Launch",
        description="Core infrastructure project",
        status="active",
        owner_id=user1.id
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    # One normal task, one overdue task
    now = datetime.now(timezone.utc)
    task1 = Task(
        title="Implement authentication",
        description="Setup JWT tokens and session handling",
        status="in_progress",
        priority="high",
        due_date=now + timedelta(days=5),
        project_id=project.id,
        assignee_id=user2.id
    )
    task2 = Task(
        title="Legacy cleanup",
        description="Archive stale database migrations",
        status="todo",
        priority="low",
        due_date=now - timedelta(days=2),  # overdue
        project_id=project.id,
        assignee_id=user1.id
    )
    task3 = Task(
        title="Deploy to staging",
        description="Verify staging deployment scripts",
        status="done",
        priority="medium",
        due_date=now - timedelta(days=1),  # completed, so NOT overdue
        project_id=project.id,
        assignee_id=user2.id
    )
    db_session.add_all([task1, task2, task3])
    db_session.commit()
    db_session.refresh(task1)
    db_session.refresh(task2)
    db_session.refresh(task3)

    comment = Comment(
        content="Started working on JWT verification.",
        task_id=task1.id,
        author_id=user2.id
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)

    return {
        "user1": user1,
        "user2": user2,
        "project": project,
        "task1": task1,
        "task2": task2,
        "task3": task3,
        "comment": comment
    }
