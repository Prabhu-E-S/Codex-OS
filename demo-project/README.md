# TaskForge

**TaskForge** is a full-stack project tracking and task management application built intentionally for manual end-to-end testing, evaluation, and verification of autonomous engineering agents in the **Codex OS** platform.

The codebase features a clean, multi-layered architecture where autonomous agents must reason across multiple files—from frontend React components down to API endpoints, Pydantic schemas, service layer logic, SQLAlchemy models, and database persistence.

---

## Technologies Used

- **Frontend**: React 18, TypeScript, Vite, CSS custom design tokens (Dark Modern UI)
- **Backend**: Python 3.12, FastAPI, Pydantic v2
- **Database & ORM**: SQLite 3, SQLAlchemy 2.0
- **Testing**: Pytest, FastAPI TestClient
- **Containerization**: Docker, Docker Compose

---

## Project Structure

```
demo-project/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── dashboard.py         # Dashboard metrics route (/api/v1/dashboard/stats)
│   │   │   ├── projects.py          # Project CRUD routes (/api/v1/projects)
│   │   │   ├── router.py            # Aggregated v1 API router
│   │   │   ├── tasks.py             # Task & comment routes (/api/v1/tasks)
│   │   │   └── users.py             # User management routes (/api/v1/users)
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   └── session.py           # SQLite engine, session maker, get_db
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # TimestampMixin (created_at, updated_at)
│   │   │   ├── comment.py           # Comment ORM model
│   │   │   ├── project.py           # Project ORM model
│   │   │   ├── task.py              # Task ORM model (status, priority, due date)
│   │   │   └── user.py              # User ORM model
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── comment.py           # CommentCreate, CommentResponse
│   │   │   ├── dashboard.py         # DashboardStats schema
│   │   │   ├── project.py           # ProjectCreate, ProjectUpdate, ProjectResponse
│   │   │   ├── task.py              # TaskCreate, TaskUpdate, TaskResponse, TaskDetailResponse
│   │   │   └── user.py              # UserCreate, UserUpdate, UserResponse
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── comment_service.py   # Comment creation and querying logic
│   │   │   ├── dashboard_service.py # Cross-table KPI and breakdown calculation
│   │   │   ├── project_service.py   # Project lifecycle & cascade management
│   │   │   ├── task_service.py      # Search, multi-criteria filtering, overdue detection
│   │   │   └── user_service.py      # User validation and lookup
│   │   ├── __init__.py
│   │   └── main.py                  # FastAPI entry point, CORS, lifespan startup
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py              # In-memory SQLite fixtures & TestClient
│   │   ├── test_comments.py         # Task comment creation & retrieval tests
│   │   ├── test_dashboard.py        # Dashboard stats, status/priority breakdown tests
│   │   ├── test_projects.py         # Project CRUD & cascade deletion tests
│   │   ├── test_tasks.py            # Task CRUD, search, priority/status filter tests
│   │   └── test_users.py            # User validation, duplication & lookup tests
│   ├── Dockerfile                   # Python 3.12-slim container
│   ├── requirements.txt             # Python backend dependencies
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   ├── Badge.tsx        # Status, priority & overdue badge indicators
│   │   │   │   ├── Button.tsx       # Reusable button with loading states
│   │   │   │   ├── EmptyState.tsx   # Meaningful empty-state graphics
│   │   │   │   ├── ErrorMessage.tsx # Inline error alert banner with retry
│   │   │   │   └── LoadingSpinner.tsx
│   │   │   ├── DashboardView.tsx    # KPI stat cards & status/priority charts
│   │   │   ├── Navbar.tsx           # Sticky header with backend connectivity pill
│   │   │   ├── ProjectDetailModal.tsx
│   │   │   ├── ProjectList.tsx      # Project grid & creation modal
│   │   │   ├── TaskCard.tsx         # Card item with quick status update
│   │   │   ├── TaskDetailModal.tsx  # Detailed task view & comment thread
│   │   │   ├── TaskList.tsx         # Search bar, multi-filter toolbar, task grid
│   │   │   └── TaskModal.tsx        # Create & edit task modal
│   │   ├── services/
│   │   │   └── api.ts               # Typed fetch REST API client
│   │   ├── types/
│   │   │   └── index.ts             # TypeScript domain interfaces
│   │   ├── App.tsx                  # Master state, view tabs, modals
│   │   ├── index.css                # Custom CSS design system
│   │   ├── main.tsx                 # React DOM mount point
│   │   └── vite-env.d.ts            # Vite client type definitions
│   ├── Dockerfile                   # Multi-stage Node + Nginx container
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   └── README.md
│
├── docs/
│   ├── api.md                       # Comprehensive REST API reference
│   └── architecture.md              # Multi-layer design & reasoning paths
├── scripts/
│   ├── run_tests.bat                # Windows one-click pytest runner
│   └── seed_data.py                 # Seeds users, projects, tasks & comments
├── data/
│   ├── .gitkeep
│   └── taskforge.db                 # Auto-generated SQLite database
├── .env.example                     # Environment variables template
├── .gitignore
├── docker-compose.yml               # Multi-container local orchestration
└── README.md
```

---

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Install dependencies (or use existing Python virtual environment)
pip install -r requirements.txt

# Start backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend starts at `http://localhost:8000`.  
Explore interactive OpenAPI docs at `http://localhost:8000/docs`.

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

The frontend runs at `http://localhost:5173` with automatic API proxying to `http://localhost:8000`.

### 3. Seed Realistic Demo Data

To populate the database with realistic projects, team members, tasks, and comment threads:

```bash
python scripts/seed_data.py
```

### 4. Running Docker Compose

```bash
docker-compose up --build
```
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`

---

## Running Backend Tests

The test suite runs against an isolated, in-memory SQLite database:

```bash
# From workspace root
pytest demo-project/backend/tests -v

# Or using the Windows helper
demo-project\scripts\run_tests.bat
```

All 28 tests pass initially:
- `test_users.py`: User creation, duplicate email rejection, invalid role validation, user retrieval
- `test_projects.py`: Project CRUD, invalid owner handling, task count joins, cascade deletion
- `test_tasks.py`: Task CRUD, multi-criteria filtering (status, priority, project), search query matching, task detail retrieval
- `test_comments.py`: Comment creation, non-existent task handling, invalid author validation, thread retrieval
- `test_dashboard.py`: Total/pending/completed counts, dynamic overdue task calculation, status & priority distributions

---

## Codex OS Manual Test Scenarios

This demo project is specifically designed to be submitted as a target repository/workspace in the **Codex OS** platform.

### How to Use TaskForge in the Codex OS Frontend

1. **Open the Codex OS Web Interface**: Navigate to `http://localhost:5173` (or the configured Codex OS UI port).
2. **Select or Create a Project**:
   - Point the repository path to `D:\Projects\Codex OS`.
3. **Create an Engineering Run**:
   - Click **"New Run"** or **"Create Run"**.
   - **Target Subpath**: Enter `demo-project` (or `demo-project/backend` / `demo-project/frontend` for scoped runs). This confines agent scanning and execution strictly inside this project.
   - **User Intent / Prompt**: Enter one of the test scenarios below.
4. **Watch Multi-Agent Execution in Real-Time**:
   - **Architect Agent**: Inspects the multi-layer codebase, reads schemas, models, and UI components, then outputs a structured technical execution plan.
   - **Builder Agent**: Modifies the relevant files across layers without touching any files outside `demo-project`.
   - **Tester Agent**: Executes pytest in the background and evaluates whether the changes resolved the task and preserved existing functionality.
   - **Breaker Agent**: Evaluates boundary conditions (e.g. malformed inputs, empty payloads, edge cases, invalid status transitions) inside the sandbox.
   - **Security Agent**: Scans modified code for static security weaknesses, injection risks, and secret exposure.
   - **Evaluator & Orchestrator Decision**: Evaluates test outcomes, review findings, and produces a final `PASSED`/`FAILED` gate decision.
   - **Control Room / Timeline**: Click on individual agent tabs in the Codex OS Control Room to see intermediate outputs, logs, diffs, and verification metrics.

---

### Graded Manual Test Scenarios for Codex OS

#### Scenario 1: Simple Bug Fix (Target: Backend Service Layer)
- **Goal**: Test Architect and Builder's ability to locate a subtle bug in filtering logic.
- **Prompt to Codex OS**:
  ```text
  "In demo-project/backend/app/services/task_service.py, the search query filter currently searches title and description with an OR condition. Please update list_tasks so that if a search term contains multiple words, it matches tasks where all words appear in either the title or description."
  ```
- **What to Observe**:
  - **Architect**: Identifies `task_service.py` and plans word splitting logic.
  - **Builder**: Updates `list_tasks` using `and_(*[or_(Task.title.ilike(...), Task.description.ilike(...)) for word in words])`.
  - **Tester**: Confirms `test_tasks.py` still passes and suggests adding a multi-word search test.

#### Scenario 2: Feature Addition (Target: Multi-layer Dashboard & API)
- **Goal**: Test cross-file contract changes across schema, service, and API.
- **Prompt to Codex OS**:
  ```text
  "Add a new metric 'completion_rate' (percentage of completed tasks as a float between 0.0 and 100.0) to the dashboard stats API. Update the Pydantic schema, the backend calculation in dashboard_service.py, and add a test in test_dashboard.py."
  ```
- **What to Observe**:
  - **Architect**: Identifies `schemas/dashboard.py`, `services/dashboard_service.py`, and `tests/test_dashboard.py`.
  - **Builder**: Adds `completion_rate: float = 0.0` to `DashboardStats`, implements division by zero safe check `round((completed / total) * 100, 1) if total > 0 else 0.0`, and updates the test assertion.
  - **Tester**: Executes pytest and verifies the new field is properly validated.

#### Scenario 3: Test Expansion (Target: Tester Agent)
- **Goal**: Verify Tester and Breaker capability in finding untested edge cases.
- **Prompt to Codex OS**:
  ```text
  "Add comprehensive unit tests in demo-project/backend/tests/test_tasks.py for edge cases in task due dates: test tasks due exactly today, tasks with null due dates, and tasks that are marked done after being overdue."
  ```
- **What to Observe**:
  - **Tester**: Writes parametrized tests checking that completed tasks never report `is_overdue = True`, regardless of due date.
  - **Breaker**: Checks boundary conditions around timezone offsets (UTC vs local time).

#### Scenario 4: Security Inspection (Target: Security Agent)
- **Goal**: Exercise Codex OS Security Agent and static analysis.
- **Prompt to Codex OS**:
  ```text
  "Perform a security audit of demo-project/backend. Verify that all SQL operations use parameterized queries, user inputs in user_service.py and task_service.py are strictly validated, and no sensitive credentials or tokens are logged."
  ```
- **What to Observe**:
  - **Security Agent**: Analyzes SQLAlchemy query constructs, verifies ORM parameterization protects against SQL injection, inspects Pydantic model configurations, and checks CORS headers in `main.py`.

#### Scenario 5: Adversarial Boundary Testing (Target: Breaker Agent)
- **Goal**: Test Breaker's ability to generate malformed inputs.
- **Prompt to Codex OS**:
  ```text
  "Review the task creation API endpoint in demo-project/backend for invalid input handling: test extremely long titles (>255 characters), negative project IDs, and invalid priority strings."
  ```
- **What to Observe**:
  - **Breaker**: Identifies FastAPI Pydantic validation barriers (HTTP 422 for strings exceeding bounds or invalid priority patterns, HTTP 400 for non-existent project IDs).

#### Scenario 6: Full-Stack Multi-File Feature (Target: End-to-End Orchestration)
- **Goal**: Full stack change touching database model, schema, service, API, frontend type, and UI.
- **Prompt to Codex OS**:
  ```text
  "Add an optional 'estimated_hours' field (positive integer) to Tasks:
  1. Add the Column to backend Task model in app/models/task.py.
  2. Add it to TaskBase, TaskCreate, TaskUpdate, and TaskResponse in app/schemas/task.py.
  3. Update TaskService.create_task and update_task.
  4. Update frontend/src/types/index.ts.
  5. Add estimated_hours display in TaskCard and TaskDetailModal.
  6. Add an automated test in test_tasks.py."
  ```
- **What to Observe**:
  - **Architect**: Maps the complete contract from DB column to UI component.
  - **Builder**: Performs synchronous modifications across backend and frontend files.
  - **Tester**: Runs pytest to guarantee zero regressions.
  - **Evaluator**: Approves promotion based on complete test pass and schema conformance.

---

## API Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health status |
| `GET` | `/api/v1/dashboard/stats` | Aggregated dashboard metrics & breakdowns |
| `GET` | `/api/v1/projects` | List all projects with task counts |
| `POST` | `/api/v1/projects` | Create a new project |
| `GET` | `/api/v1/projects/{id}` | Get project details and owner |
| `PATCH`| `/api/v1/projects/{id}` | Update project attributes |
| `DELETE`|`/api/v1/projects/{id}`| Delete project (cascades to tasks) |
| `GET` | `/api/v1/tasks` | List tasks (supports `status`, `priority`, `project_id`, `search`) |
| `POST` | `/api/v1/tasks` | Create a new task |
| `GET` | `/api/v1/tasks/{id}` | Get task details and comments thread |
| `PATCH`| `/api/v1/tasks/{id}` | Update task status, priority, or fields |
| `DELETE`|`/api/v1/tasks/{id}`| Delete task |
| `GET` | `/api/v1/tasks/{id}/comments` | List comments for task |
| `POST`| `/api/v1/tasks/{id}/comments` | Add comment to task |
| `GET` | `/api/v1/users` | List team users |
| `POST`| `/api/v1/users` | Register team user |
| `GET` | `/api/v1/users/{id}` | Get user by ID |
