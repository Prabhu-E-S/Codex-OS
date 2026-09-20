# TaskForge Architecture

TaskForge is structured as a realistic multi-layered full-stack application designed specifically to evaluate autonomous software engineering platforms like **Codex OS**.

```
┌────────────────────────────────────────────────────────┐
│               Frontend (React + Vite)                  │
│   Components ──► State/Hooks ──► Typed API Client      │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTP / JSON (REST API)
┌──────────────────────────▼─────────────────────────────┐
│               Backend (Python FastAPI)                 │
│                                                        │
│  API Routers (/api/v1/projects, /tasks, /users, etc.)  │
│                           │                            │
│                  Pydantic Schemas                      │
│                           │                            │
│                    Service Layer                       │
│    (Business logic, overdue calculation, filtering)   │
│                           │                            │
│                 SQLAlchemy ORM Models                  │
│                           │                            │
│                 SQLite Database Engine                 │
└────────────────────────────────────────────────────────┘
```

## Layer Descriptions

### 1. Presentation Layer (Frontend)
- **Framework**: React 18 with TypeScript and Vite.
- **Components**:
  - `DashboardView`: Aggregated KPIs (projects, tasks, completed, pending, overdue) and status/priority breakdown charts.
  - `ProjectList` & `ProjectDetailModal`: Project CRUD, progress tracking, and cascade navigation.
  - `TaskList` & `TaskCard`: Interactive filtering by status, priority, project, and search query.
  - `TaskModal`: Validated forms for task creation and editing.
  - `TaskDetailModal`: Detailed metadata and interactive comment threads.
- **Design System**: Vanilla CSS design tokens with sleek dark mode aesthetics, glassmorphic cards, and responsive layouts.
- **API Client**: `services/api.ts` provides typed, promise-based HTTP communication with error handling and environment fallback.

### 2. API & Routing Layer (Backend)
- **Framework**: FastAPI (Python 3.12+).
- **Routers**:
  - `/api/v1/users`: User provisioning and lookups.
  - `/api/v1/projects`: Project lifecycle management.
  - `/api/v1/tasks`: Task operations with multi-parameter filtering and comment sub-endpoints.
  - `/api/v1/dashboard`: High-performance statistics calculation.
- **Middleware**: CORS middleware supporting configurable origins for development and production sandboxes.

### 3. Schema & Validation Layer
- **Library**: Pydantic v2.
- **Validation**: Strict type checks, regex email validation, regex enumeration on status (`todo`, `in_progress`, `review`, `done`) and priority (`low`, `medium`, `high`, `urgent`), min/max bounds.

### 4. Service Layer
- Encapsulates pure business logic away from HTTP transport:
  - `TaskService`: Computes dynamic overdue state, performs fuzzy title/description searches, and coordinates comment counts.
  - `ProjectService`: Manages relationship cascades and task count aggregation.
  - `DashboardService`: Aggregates cross-table metrics and priority/status distributions.
  - `UserService`: Enforces email uniqueness and profile updates.

### 5. Persistence Layer
- **Engine**: SQLite (`data/taskforge.db`) using SQLAlchemy 2.0 ORM.
- **Models**:
  - `User`: Team members with assigned roles.
  - `Project`: Work containers with foreign key to owner.
  - `Task`: Action items with foreign keys to project and assignee.
  - `Comment`: Conversation records linked to tasks and author.
- **Cascade Behavior**: Deleting a project cascades to delete associated tasks and comments.

---

## Autonomous Agent Reasoning Paths

Codex OS agents exercise realistic software engineering workflows across these layers:

1. **Architect Agent**: Must trace changes across database models, Pydantic schemas, and API contracts (e.g. adding task tags requires schema additions, DB column additions, and frontend badge updates).
2. **Builder Agent**: Modifies Python backend routes/services and React frontend components concurrently.
3. **Tester Agent**: Executes pytest suites in an isolated in-memory test database, verifying zero regression and functional coverage.
4. **Breaker Agent**: Evaluates boundary handling (e.g. negative IDs, empty strings, invalid status values, SQL injection resistance).
5. **Security Agent**: Scans static dependencies, input sanitation, CORS configuration, and credential isolation.
