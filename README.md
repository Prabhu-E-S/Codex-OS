# Codex OS

**The Autonomous Software Engineering Sandbox**

Codex OS is a full-stack platform that orchestrates a team of autonomous AI agents to analyze, build, test, attack, and evaluate software — end to end, with no human in the loop.

![Phase 10](https://img.shields.io/badge/Phase-10%20%E2%80%94%20Deployment%20Ready-blue)
![Python](https://img.shields.io/badge/Python-3.12-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-teal)
![React](https://img.shields.io/badge/React-19-blue)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## What is Codex OS?

Codex OS gives you a **Control Room** for autonomous software engineering. You define an engineering goal — "fix all division-by-zero bugs" or "add input validation to the public API" — and Codex OS dispatches a pipeline of specialized agents that work in isolated environments, report findings, iterate until quality thresholds are met, and produce a quantified Engineering Score.

### Core Innovation

| Capability | Description |
|------------|-------------|
| **Autonomous Agent Pipeline** | Architect → Builder → Tester → Breaker → Security → Decision, running in a multi-iteration loop |
| **Isolated Execution** | Every agent gets its own Git worktree + Docker sandbox container — no shared state contamination |
| **Adversarial Testing** | Breaker Agent fuzzes and stress-tests code the Builder just wrote |
| **Security Scanning** | Pattern scanner, Bandit, pip-audit, Semgrep, and gitleaks run automatically |
| **Engineering Score** | 6-dimensional weighted score (Correctness, Security, Test Coverage, Maintainability, Performance, Regression Risk) |
| **Live Control Room** | Real-time dashboard polling agent status, findings, evaluation, and logs at 3-second cadence |
| **Self-Healing Loop** | If tests fail or critical vulnerabilities are found, the orchestrator sends feedback to the Builder and retries |

---

## Architecture

```
Frontend (React/Vite)
      │
      ▼
FastAPI Backend ──► Orchestrator ──► Agent Pipeline
      │                              │
      ▼                              ▼
SQLite/PostgreSQL          Git Worktrees + Docker Sandboxes
```

Full architecture diagrams (Mermaid): [`docs/architecture.md`](docs/architecture.md)

---

## Agent Pipeline

```
🏗️  Architect    →  Analyzes codebase, generates implementation plan
🔨  Builder      →  Implements the plan, writes code and tests
🧪  Tester       →  Runs the test suite, reports pass/fail/coverage
💥  Breaker      →  Adversarially fuzzes the implementation
🔒  Security     →  Scans for vulnerabilities and compliance issues
🎯  Orchestrator →  Evaluates findings and decides: ship, fail, or retry
```

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker Desktop (for sandbox engine) — optional but recommended

### 1. Clone & configure

```bash
git clone <repo-url>
cd "Codex OS"
cp .env.example .env
# Edit .env as needed — defaults work for local SQLite dev
```

### 2. Backend

```bash
cd "Codex OS"
pip install -r backend/requirements.txt
python -m backend.main
```

Backend will start at: **http://localhost:8000**
Interactive API docs: **http://localhost:8000/docs**

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will start at: **http://localhost:5173**

### 4. (Optional) Docker Deployment

Full stack with PostgreSQL and Nginx:

```bash
cp .env.example .env
# Edit database credentials if needed
docker-compose up --build -d
```

- Frontend: **http://localhost:80**
- Backend API: **http://localhost:8000**
- PostgreSQL: **localhost:5432**

---

## Running a Demo

A ready-made demonstration target is included at [`demo-project/`](demo-project/). It contains a Python calculator with deliberate bugs (division-by-zero, missing input validation, no error handling for negative inputs).

### Demo Steps

1. Start the backend and frontend
2. Open Codex OS in your browser
3. Create a new project:
   - **Name**: `Calculator Demo`
   - **Repository Path**: full path to `demo-project/` on your system
4. Create a new engineering run:
   - **Goal**: `Identify and fix all crashes and missing input validation in the calculator module. Ensure all tests pass.`
5. Click **Start Autonomous Run** (3 iterations recommended)
6. Watch the Control Room — agents will execute in sequence

**Expected outcome**: The Builder fixes `divide()`, `sqrt()`, and `factorial()`. The Tester reports all tests green. The Security agent finds no critical issues. Engineering Score: ~85/100.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./codex_os.db` | Database connection (SQLite or PostgreSQL) |
| `BACKEND_HOST` | `0.0.0.0` | API server host |
| `BACKEND_PORT` | `8000` | API server port |
| `CODEX_COMMAND` | _(auto-detect)_ | Path or command for Codex CLI |
| `CODEX_EXECUTION_TIMEOUT` | `900` | Codex run timeout in seconds |
| `CODEX_WORKSPACE_ROOT` | `./workspaces` | Base directory for Git worktrees |
| `CODEX_GIT_PROVIDER` | `real` | `real` or `mock` (for tests) |
| `DOCKER_SANDBOX_IMAGE` | `python:3.12-slim` | Base Docker image for sandboxes |
| `DOCKER_SANDBOX_CPU_LIMIT` | `1.0` | CPU limit per sandbox container |
| `DOCKER_SANDBOX_MEMORY_LIMIT` | `512m` | Memory limit per sandbox |
| `DOCKER_SANDBOX_TIMEOUT` | `60` | Command timeout inside sandbox |
| `DOCKER_SANDBOX_NETWORK` | `none` | Network isolation (`none` recommended) |
| `DOCKER_SANDBOX_PROVIDER` | `real` | `real` or `mock` (for tests) |
| `SECURITY_SCANNING_ENABLED` | `true` | Enable automated security scanners |
| `SECURITY_SCANNERS` | `pattern_scanner,bandit,...` | Comma-separated scanner list |
| `ORCHESTRATOR_ENABLED` | `true` | Enable autonomous orchestrator |
| `ORCHESTRATOR_DEFAULT_MAX_ITERATIONS` | `3` | Default iteration limit |
| `ORCHESTRATOR_MAX_ITERATIONS_LIMIT` | `10` | Hard cap on iterations |
| `ORCHESTRATOR_TOTAL_RUN_TIMEOUT` | `3600` | Total run timeout in seconds |
| `EVALUATION_ENABLED` | `true` | Enable Engineering Score evaluation |
| `EVALUATION_WEIGHT_CORRECTNESS` | `0.30` | Correctness dimension weight |
| `EVALUATION_WEIGHT_SECURITY` | `0.20` | Security dimension weight |
| `EVALUATION_WEIGHT_TEST_COVERAGE` | `0.15` | Test coverage dimension weight |
| `EVALUATION_WEIGHT_MAINTAINABILITY` | `0.15` | Maintainability dimension weight |
| `EVALUATION_WEIGHT_PERFORMANCE` | `0.10` | Performance dimension weight |
| `EVALUATION_WEIGHT_REGRESSION_RISK` | `0.10` | Regression risk dimension weight |

---

## API Reference

### Health

```http
GET /api/health
```

Returns status of database, Docker daemon, and Codex CLI availability.

```json
{
  "status": "ok",
  "phase": 10,
  "database": "connected",
  "docker": "available",
  "codex": "available"
}
```

### Projects

```http
GET  /api/projects                          # List all projects
POST /api/projects                          # Create project
GET  /api/projects/{id}                     # Get project
DEL  /api/projects/{id}                     # Delete project
```

### Engineering Runs

```http
GET  /api/projects/{project_id}/runs        # List runs
POST /api/projects/{project_id}/runs        # Create run
GET  /api/runs/{id}                         # Get run
POST /api/runs/{id}/execute                 # Start Codex execution
GET  /api/runs/{id}/logs                    # Get logs
POST /api/runs/{id}/cancel                  # Cancel run
```

### Autonomous Orchestration

```http
POST /api/runs/{id}/start-autonomous        # Launch agent pipeline
GET  /api/runs/{id}/orchestration           # Get workflow state
POST /api/runs/{id}/pause                   # Pause at next boundary
POST /api/runs/{id}/resume                  # Resume from PAUSED
POST /api/runs/{id}/orchestration/cancel    # Cancel
```

### Control Room

```http
GET  /api/runs/{id}/control-room            # Full dashboard snapshot
```

### Evaluation

```http
POST /api/runs/{id}/evaluate                # Compute Engineering Score
GET  /api/runs/{id}/evaluations             # List evaluations for run
GET  /api/evaluations/{id}                  # Get evaluation details
GET  /api/evaluations/{id}/dimensions       # Dimension breakdown
GET  /api/evaluations/{id}/evidence         # Evidence items
```

---

## Running Tests

```bash
cd "Codex OS"
python -m pytest backend/tests/ -v
```

Test suites:
- `test_hardening.py` — Phase 10 hardening: input validation, error format, health check shape
- `test_control_room.py` — Control Room snapshot and telemetry
- `test_evaluation.py` — Engineering Score computation
- `test_orchestrator.py` — Orchestration state machine
- `test_breaker_security.py` — Breaker and Security agents
- `test_agents.py` — Agent execution pipeline
- `test_sandbox.py` — Docker sandbox engine
- `test_workspaces.py` — Git worktree management
- `test_execution.py` — Codex execution service

---

## Security Model

Codex OS applies defense in depth at every layer:

| Layer | Protection |
|-------|-----------|
| **Input Validation** | Path traversal rejected; goal length capped; sandbox params clamped |
| **Error Responses** | No stack traces or internal details in HTTP responses |
| **Sandbox Isolation** | No network (`--network none`), no privileged mode, non-root user, pids limit |
| **Mount Security** | Docker socket mounts blocked; system paths blocked; path traversal blocked |
| **Secret Redaction** | All agent outputs and evidence pass through `redact_sensitive_text` before DB storage |
| **CORS** | Configured explicitly; wildcard only for local development |
| **Database** | Parameterized queries via SQLAlchemy ORM; no raw SQL interpolation |

---

## Project Structure

```
Codex OS/
├── backend/
│   ├── api/              # FastAPI routers (projects, runs, agents, sandboxes, …)
│   ├── agents/           # Agent implementations (Architect, Builder, Tester, Breaker, Security)
│   ├── codex/            # Codex CLI runner, process manager, prompts
│   ├── evaluation/       # Engineering Score engine
│   ├── models/           # SQLAlchemy ORM models
│   ├── orchestrator/     # State machine, policy, feedback, manager
│   ├── sandbox/          # Docker sandbox engine
│   ├── schemas/          # Pydantic request/response schemas
│   ├── security/         # Security scanner implementations
│   ├── services/         # Execution service, Control Room service
│   ├── tests/            # Pytest test suites
│   └── workspace/        # Git worktree provider
├── frontend/
│   └── src/
│       ├── api/          # Type-safe API client
│       ├── components/   # Shared UI components + Control Room panels
│       ├── hooks/        # useRunControlRoom polling hook
│       └── views/        # Page-level views (Overview, Control Room, …)
├── demo-project/         # Demonstration target (buggy Python calculator)
├── docker/               # Sandbox Docker image
├── docs/                 # Architecture documentation
├── docker-compose.yml    # Full-stack deployment
└── .env.example          # Environment variable reference
```

---

## Phases Completed

| Phase | Title |
|-------|-------|
| 1 | Project Foundation — FastAPI, SQLAlchemy, database |
| 2 | Codex Execution Engine — CLI runner, process manager |
| 3 | Git Worktree System — isolated workspace provider |
| 4 | Docker Sandbox Engine — container lifecycle, security |
| 5 | Autonomous Agent Team — Architect, Builder, Tester |
| 6 | Breaker + Security Agents — adversarial testing, scanning |
| 7 | Autonomous Orchestrator — state machine, policy, iteration loop |
| 8 | Evaluation & Engineering Score — 6-dimension weighted scoring |
| 9 | Codex OS Control Room — real-time dashboard, telemetry |
| **10** | **Final Hardening, Demo & Deployment Readiness** |

---

## Known Limitations

- **Codex CLI required**: The Codex execution engine requires the `codex` CLI to be installed and in PATH. Runs will fail gracefully if unavailable.
- **Docker required for sandboxes**: The sandbox engine requires Docker Desktop running locally. Configure `DOCKER_SANDBOX_PROVIDER=mock` for daemon-free development.
- **SQLite concurrency**: SQLite is suitable for single-user development. For production multi-user workloads, use PostgreSQL.
- **Windows path handling**: Git worktree paths on Windows use backslashes. The workspace provider handles normalization, but ensure `CODEX_WORKSPACE_ROOT` uses an accessible Windows path.

---

## License

MIT — see [LICENSE](LICENSE)
