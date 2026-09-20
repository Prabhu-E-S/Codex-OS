# TaskForge Backend

FastAPI REST backend with SQLite and SQLAlchemy ORM for the TaskForge application.

## Structure
- `app/api/`: REST API routers (`users.py`, `projects.py`, `tasks.py`, `dashboard.py`)
- `app/database/`: SQLite engine, declarative base, and session generator
- `app/models/`: SQLAlchemy ORM models (`User`, `Project`, `Task`, `Comment`)
- `app/schemas/`: Pydantic validation schemas
- `app/services/`: Core business logic layer
- `tests/`: Pytest test suite

## Running Locally

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the development server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. Interactive Swagger docs:
Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.

## Running Tests

```bash
pytest tests/ -v
```
