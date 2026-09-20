#!/usr/bin/env python3
"""
Seed realistic demo data for TaskForge application.
Can be executed directly:
    python scripts/seed_data.py
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure backend directory is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Ensure data directory exists
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{DATA_DIR / 'taskforge.db'}"

from app.database.session import SessionLocal, init_db
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.models.comment import Comment

def seed():
    print(f"Initializing TaskForge database at: {os.environ['DATABASE_URL']}")
    init_db()
    db = SessionLocal()

    try:
        # Check if already seeded
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"Database already contains {existing_users} users. Skipping seeding.")
            return

        print("Seeding initial users...")
        users = [
            User(email="sarah.connor@example.com", full_name="Sarah Connor", role="admin"),
            User(email="alex.chen@example.com", full_name="Alex Chen", role="manager"),
            User(email="elena.rostova@example.com", full_name="Elena Rostova", role="member"),
            User(email="marcus.vance@example.com", full_name="Marcus Vance", role="member"),
        ]
        db.add_all(users)
        db.commit()
        for u in users:
            db.refresh(u)

        print("Seeding projects...")
        projects = [
            Project(
                name="Codex Engine 2.0",
                description="Next generation multi-agent autonomous engineering framework.",
                status="active",
                owner_id=users[0].id
            ),
            Project(
                name="Security Hardening Initiative",
                description="Audit dependencies, enforce role boundaries, and improve static analysis.",
                status="active",
                owner_id=users[1].id
            ),
            Project(
                name="Customer Portal Redesign",
                description="Revamp frontend UI with responsive dashboard and streamlined forms.",
                status="completed",
                owner_id=users[0].id
            ),
        ]
        db.add_all(projects)
        db.commit()
        for p in projects:
            db.refresh(p)

        print("Seeding tasks...")
        now = datetime.now(timezone.utc)
        tasks = [
            # Codex Engine 2.0 tasks
            Task(
                title="Implement AST parser for Python code refactoring",
                description="Create an AST visitor that safely checks syntax tree mutations.",
                status="in_progress",
                priority="urgent",
                due_date=now + timedelta(days=2),
                project_id=projects[0].id,
                assignee_id=users[2].id
            ),
            Task(
                title="Integrate Pytest JSON reporter into test runner",
                description="Parse structured test output to capture test failures and assertions cleanly.",
                status="todo",
                priority="high",
                due_date=now + timedelta(days=4),
                project_id=projects[0].id,
                assignee_id=users[3].id
            ),
            Task(
                title="Design sandbox worktree manager",
                description="Allow ephemeral git worktree creation without polluting main repository branch.",
                status="done",
                priority="high",
                due_date=now - timedelta(days=3),
                project_id=projects[0].id,
                assignee_id=users[0].id
            ),
            # Security Hardening tasks
            Task(
                title="Perform static dependency vulnerability scan",
                description="Review pip and npm dependencies for known CVEs and outdated packages.",
                status="in_progress",
                priority="high",
                due_date=now + timedelta(days=1),
                project_id=projects[1].id,
                assignee_id=users[1].id
            ),
            Task(
                title="Fix input validation on user registration endpoint",
                description="Sanitize user inputs and restrict role assignment privileges.",
                status="todo",
                priority="urgent",
                due_date=now - timedelta(days=1),  # Overdue task
                project_id=projects[1].id,
                assignee_id=users[1].id
            ),
            # Customer Portal tasks
            Task(
                title="Ship responsive navigation bar and theme toggle",
                description="Provide unified header layout with quick-action project selector.",
                status="done",
                priority="medium",
                due_date=now - timedelta(days=5),
                project_id=projects[2].id,
                assignee_id=users[2].id
            ),
            Task(
                title="Add export to CSV for task analytics",
                description="Allow managers to download task completion reports directly from the dashboard.",
                status="todo",
                priority="low",
                due_date=now + timedelta(days=7),
                project_id=projects[2].id,
                assignee_id=users[3].id
            ),
        ]
        db.add_all(tasks)
        db.commit()
        for t in tasks:
            db.refresh(t)

        print("Seeding task comments...")
        comments = [
            Comment(
                content="I've mapped out the AST node visitor pattern. Working on unit tests.",
                task_id=tasks[0].id,
                author_id=users[2].id
            ),
            Comment(
                content="Make sure to test recursive tree traversal for deeply nested lambdas.",
                task_id=tasks[0].id,
                author_id=users[0].id
            ),
            Comment(
                content="Identified 2 minor dependency warnings; submitting patches today.",
                task_id=tasks[3].id,
                author_id=users[1].id
            ),
            Comment(
                content="This is overdue! We need this patched before the next release cycle.",
                task_id=tasks[4].id,
                author_id=users[0].id
            ),
        ]
        db.add_all(comments)
        db.commit()

        print("Database seeded successfully with realistic TaskForge data!")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
