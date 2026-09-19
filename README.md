# Codex OS — The Autonomous Software Engineering Sandbox

> **Phase 1: Project Foundation | Phase 2: Codex Execution Engine | Phase 3: Git Worktree System | Phase 4: Docker Sandbox Engine**

Codex OS is an AI-native software engineering sandbox. The ultimate autonomous workflow will encompass:
**Understand → Plan → Build → Test → Break → Debug → Evaluate → Improve → Ship**

Phase 4 introduces the **Docker Sandbox Engine**, providing disposable, resource-constrained container execution environments bound directly to Phase 3 Git worktrees. Commands and autonomous engineering runs execute strictly inside the container's isolated `/workspace` bind mount rather than on the host system.

---

## Architecture Overview

```text
Codex OS
├── backend/                  # FastAPI Python Backend
│   ├── main.py               # Application entrypoint, CORS, and schema migrations
│   ├── config.py             # Settings, Codex, Worktrees, & Docker Sandbox config
│   ├── database.py           # SQLAlchemy engine & health check
│   ├── codex/                # Phase 2 Codex Execution Layer
│   │   ├── runner.py         # Subprocess invocation, safety checks, & execution loop
│   │   ├── process.py        # ProcessManager: streaming log buffers & PID tracking
│   │   ├── prompts.py        # Task prompt builder
│   │   └── models.py         # RunStatus enum & ExecutionResult dataclass
│   ├── workspace/            # Phase 3 Git Worktree System
│   │   ├── git.py            # GitWorkspaceProvider ABC, RealGit & MockGit providers
│   │   ├── manager.py        # WorkspaceManager: branch generation, path safety, lifecycle
│   │   ├── models.py         # WorkspaceStatus enum & WorktreeInfo dataclass
│   │   └── exceptions.py     # Workspace domain exceptions (path escape, invalid names)
│   ├── sandbox/              # Phase 4 Docker Sandbox Engine
│   │   ├── docker.py         # DockerProvider ABC, RealDocker & MockDocker providers, mount security
│   │   ├── executor.py       # SandboxExecutor: command execution, timeout guard, duration tracking
│   │   ├── manager.py        # SandboxManager: lifecycle, specs, workspace file preservation
│   │   ├── models.py         # SandboxStatus enum, CommandResult, SandboxSpec, ContainerState
│   │   └── exceptions.py     # Sandbox domain exceptions (DockerUnavailable, MountSecurity, etc.)
│   ├── models/               # SQLAlchemy Relational Models
│   │   ├── project.py        # Project model (with workspaces relationship)
│   │   ├── workspace.py      # Workspace model (name, path, branch, sandboxes relationship)
│   │   ├── sandbox.py        # Sandbox model (status, container_id, limits, timestamps)
│   │   └── run.py            # EngineeringRun model (with workspace_id & sandbox_id FKs)
│   ├── schemas/              # Pydantic validation schemas
│   │   ├── project.py        # Project schemas
│   │   ├── workspace.py      # WorkspaceCreate & WorkspaceResponse
│   │   ├── sandbox.py        # SandboxCreate, SandboxResponse, SandboxExecuteRequest, CommandResultResponse
│   │   └── run.py            # RunResponse & RunLogsResponse (with workspace & sandbox fields)
│   ├── api/                  # REST API Routers
│   │   ├── health.py         # GET /api/health
│   │   ├── projects.py       # CRUD /api/projects
│   │   ├── workspaces.py     # CRUD /api/projects/{id}/workspaces & /api/workspaces/{id}
│   │   ├── sandboxes.py      # Docker status, sandbox lifecycle, command execution
│   │   └── runs.py           # Project Engineering Runs, Execute, Logs, Cancel
│   ├── services/             # Business Logic Layer
│   │   ├── project_service.py # Project, Run, & Sandbox DB queries
│   │   └── execution_service.py # Background task execution, worktree & sandbox routing
│   └── tests/
│       ├── test_execution.py  # Phase 2 execution test suite
│       ├── test_workspaces.py # Phase 3 worktree test suite (zero-git mock provider)
│       └── test_sandbox.py    # Phase 4 sandbox test suite (mount security, lifecycle, APIs)
├── docker/                   # Container definitions
│   └── Dockerfile.sandbox    # Lightweight non-root sandbox image (python:3.12-slim)
└── frontend/                 # React + TypeScript + Vite Dashboard
    ├── src/
    │   ├── api/              # Type-safe API client (projects, runs, workspaces, sandboxes)
    │   ├── components/       # Header, Sidebar, Cards, Modals, Sandbox Panel & Terminal
    │   ├── views/            # OverviewView & WorkspacesView
    │   ├── App.tsx           # Application state & tab routing
    │   └── index.css         # GitHub/Linear/VS Code CSS design system & terminal styling
```

---

## Prerequisites

- **Python 3.10+** (Python 3.14 verified)
- **Node.js 18+** & **npm**
- **Docker Engine / Docker Desktop** (Optional in dev/testing; if the daemon is unavailable, Codex OS accurately reports status and supports `DOCKER_SANDBOX_PROVIDER=mock` for testing)
- **PostgreSQL** (Optional in dev; automatically falls back to SQLite `codex_os.db` if `DATABASE_URL` is omitted)
- **Codex CLI** (Configurable via `CODEX_COMMAND`; if omitted, checks system `PATH` for `codex`. If unavailable, reports a clear configuration notice)

---

## Environment Configuration

Copy `.env.example` to `.env` in the root directory:

```bash
cp .env.example .env
```

### Configuration Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL or SQLite connection string | `sqlite:///./codex_os.db` |
| `BACKEND_HOST` | FastAPI host interface | `0.0.0.0` |
| `BACKEND_PORT` | FastAPI listening port | `8000` |
| `BACKEND_URL` | Base URL for backend service | `http://localhost:8000` |
| `VITE_API_URL` | Frontend API target | `http://localhost:8000` |
| `NEXT_PUBLIC_API_URL` | Alternative frontend API target | `http://localhost:8000` |
| `CODEX_COMMAND` | Command or path to invoke Codex (e.g. `codex`) | Auto-detect `codex` on PATH |
| `CODEX_EXECUTION_TIMEOUT` | Maximum execution time in seconds | `900` (15 minutes) |
| `CODEX_WORKSPACE_ROOT` | Base directory for isolated Git worktrees | `./workspaces` |
| `CODEX_GIT_PROVIDER` | Git worktree provider (`real` or `mock`) | `real` |
| `DOCKER_SANDBOX_IMAGE` | Base container image for sandboxes | `python:3.12-slim` |
| `DOCKER_SANDBOX_CPU_LIMIT` | Maximum CPU cores allocated per sandbox | `1.0` |
| `DOCKER_SANDBOX_MEMORY_LIMIT` | Maximum memory limit per sandbox | `512m` |
| `DOCKER_SANDBOX_TIMEOUT` | Default command execution timeout in seconds | `120` |
| `DOCKER_SANDBOX_NETWORK` | Outbound network bridge enabled (`true`/`false`) | `false` |
| `DOCKER_SANDBOX_PIDS_LIMIT` | Max process limit per container (fork bomb defense) | `64` |
| `DOCKER_SANDBOX_PROVIDER` | Docker provider (`real` or `mock`) | `real` |
| `DOCKER_SANDBOX_USER` | Non-root container UID:GID | `1000:1000` |

---

## Running the Application

### 1. Backend (FastAPI)

From the project root:

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Start backend server with hot-reload
python -m uvicorn backend.main:app --reload --port 8000
```

The backend is accessible at:
- **API Base**: `http://localhost:8000`
- **Interactive OpenAPI Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/api/health`

### 2. Frontend (React + Vite)

In a separate terminal:

```bash
cd frontend

# Install frontend dependencies (if not already installed)
npm install

# Start development server
npm run dev
```

The frontend dashboard opens at `http://localhost:5173`.

---

## Running Backend Tests

Run the full automated test suite (16 tests, without executing any git commands):

```bash
# Run all Phase 2, Phase 3, and Phase 4 tests
python -m pytest backend/tests/ -v
```

Tests cover:
1. **Execution Engine (Phase 2)**:
   - Codex availability detection & clean unavailable state reporting
   - Repository path validation
   - Execution lifecycle (`PENDING` → `STARTING` → `RUNNING` → `COMPLETED`)
   - Real-time stdout/stderr log capture
   - Process cancellation (`CANCELLED`)
   - Configurable execution timeout safeguard (`TIMEOUT`)
2. **Git Worktree System (Phase 3)**:
   - Workspace creation with safe directory structure and branch generation (`codex/workspace/{name}`)
   - Workspace name regex validation (`^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$`)
   - Path traversal and project directory root escape prevention
   - Mock workspace provider simulation with zero Git commands
   - Provider failure handling & `ERROR` state tracking
   - Engineering run routing into `workspace.path` instead of primary repository
   - Dynamic workspace state transitions (`READY` → `IN_USE` → `READY`)
   - Worktree removal and directory cleanup
3. **Docker Sandbox Engine (Phase 4)**:
   - Docker daemon availability detection & informative fallback reporting
   - Strict mount security validation (rejecting root mounts and `/var/run/docker.sock`)
   - Full container lifecycle (`CREATE` → `START` → `EXECUTE` → `STOP` → `REMOVE` → recreation)
   - Workspace file preservation across container destructions
   - Command execution timeout enforcement and output capture
   - Full REST API integration flow with `MockDockerProvider`

---

## Workspace & Docker Sandbox Lifecycle

### Workspace Status Flow

```text
CREATING → READY ↔ IN_USE (during execution)
             ↓
           ERROR / REMOVING → REMOVED
```

### Docker Sandbox Status Flow

```text
POST /workspaces/{id}/sandbox
           ↓
        CREATED
       ↙       ↖
   (start)     (stop)
     ↓           ↑
  RUNNING ───────┘
     ↓ (remove)
  REMOVED (underlying workspace files preserved)
```

---

## API Endpoints

### Projects
- `GET /api/projects` — List all projects.
- `POST /api/projects` — Create project (`name`, `repository_path`, `description`).
- `GET /api/projects/{id}` — Fetch project details.
- `DELETE /api/projects/{id}` — Delete project and all associated runs and workspaces.

### Workspaces (Phase 3)
- `GET /api/projects/{id}/workspaces` — List all active worktree workspaces for a project.
- `POST /api/projects/{id}/workspaces` — Create an isolated worktree workspace (`name`).
- `GET /api/workspaces/{id}` — Fetch workspace details, branch, path, and status.
- `DELETE /api/workspaces/{id}` — Remove worktree and delete workspace directory.

### Sandboxes (Phase 4)
- `GET /api/sandboxes/status` — Check Docker daemon availability, version, and provider.
- `POST /api/workspaces/{id}/sandbox` — Provision a sandbox container bound to a worktree.
- `GET /api/workspaces/{id}/sandbox` — Retrieve active sandbox for a workspace.
- `GET /api/sandboxes/{id}` — Get sandbox status, container ID, and resource limits.
- `POST /api/sandboxes/{id}/start` — Start a created or stopped sandbox container.
- `POST /api/sandboxes/{id}/stop` — Stop a running sandbox container.
- `DELETE /api/sandboxes/{id}` — Remove container (preserves workspace files).
- `POST /api/sandboxes/{id}/execute` — Run command in `/workspace` with timeout & output capture.

### Engineering Runs
- `GET /api/projects/{id}/runs` — List runs for a project.
- `POST /api/projects/{id}/runs` — Create an engineering run (`goal`, optional `workspace_id`, optional `sandbox_id`).
- `GET /api/runs/{id}` — Fetch run details, status, timestamps, exit code, workspace & sandbox info.
- `POST /api/runs/{id}/execute` — Start execution (routes to sandbox container `/workspace` if sandbox configured).
- `GET /api/runs/{id}/logs` — Retrieve live streaming stdout/stderr or stored results.
- `POST /api/runs/{id}/cancel` — Terminate the active process safely and release resources.

---

## Sandbox Security Guarantees

1. **Mount Isolation**: Containers only mount the specified Git worktree at `/workspace`. Root filesystems (`/`, `C:\`) and host Docker sockets (`/var/run/docker.sock`) are strictly blocked.
2. **Resource Throttling**: CPU limits (`1.0` core), memory limits (`512m`), and process limits (`pids_limit=64`) prevent noisy neighbor and fork-bomb denial-of-service.
3. **Least Privilege**: Containers execute under a non-root `codex` user (UID 1000).
4. **Preserved Persistence**: Removing or replacing a sandbox container never touches or deletes the underlying Git worktree files.

---

## Out of Scope for Phase 4 (Scheduled for Future Phases)

- Phase 5: Multi-Agent Orchestration (Architect, Builder, Tester, Breaker, Security, Judge)
- Phase 6: Code Evaluation & Benchmark Pass Rate Scoring
- Phase 7: Automated Branch Merging & Pull Request Generation
- Real-time WebSockets
