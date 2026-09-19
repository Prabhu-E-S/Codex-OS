# Codex OS — The Autonomous Software Engineering Sandbox

> **Phase 1: Project Foundation | Phase 2: Codex Execution Engine | Phase 3: Git Worktree System | Phase 4: Docker Sandbox Engine | Phase 5: First Autonomous Agent Team | Phase 6: Breaker + Security Agents**

Codex OS is an AI-native software engineering sandbox. The ultimate autonomous workflow encompasses:
**Understand → Plan → Build → Test → Break → Security → Debug → Evaluate → Ship**

Phase 6 extends the **Autonomous Agent Team** to 5 specialized agents:
1. **Architect Agent**: Inspects repository architecture, dependencies, and constraints to produce a structured implementation plan without modifying code.
2. **Builder Agent**: Implements the Architect's plan inside its assigned isolated workspace and sandbox without touching the primary repository.
3. **Tester Agent**: Verifies the implementation by executing automated tests in its controlled sandbox and outputting structured pass/fail metrics.
4. **Breaker Agent**: Actively attacks the implementation by designing and executing adversarial test scenarios (edge cases, empty/null inputs, boundary conditions, invalid state transitions) inside the sandbox, producing structured evidence-backed findings.
5. **Security Agent**: Inspects the implementation for vulnerabilities, hard-coded secrets, injection vectors, and misconfigurations using a pluggable scanner abstraction and static analysis, honestly reporting scanner availability without fabricating findings.

Sequential Execution Workflow:
$$\text{Engineering Goal} \longrightarrow \text{Architect} \longrightarrow \text{Builder} \longrightarrow \text{Tester} \longrightarrow \text{Breaker} \longrightarrow \text{Security} \longrightarrow \text{Findings & Report}$$

---

## Architecture Overview

```text
Codex OS
├── backend/                  # FastAPI Python Backend
│   ├── main.py               # Application entrypoint, CORS, and schema migrations
│   ├── config.py             # Settings, Codex, Worktrees, Docker Sandbox, & Security config
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
│   ├── security/             # Phase 6 Security Scanner Abstraction
│   │   ├── models.py         # ScannerFinding, ScannerReport, AggregatedScanReport dataclasses
│   │   ├── providers.py      # BaseScannerProvider ABC, Bandit, Pip-audit, Npm-audit, Semgrep, Gitleaks, Pattern
│   │   ├── scanner.py        # SecurityScannerManager: honest availability discovery & aggregated scanning
│   │   └── exceptions.py     # Security scanner domain exceptions
│   ├── agents/               # Autonomous Agent Team (Phases 5 & 6)
│   │   ├── base.py           # BaseAgent abstract base class
│   │   ├── context.py        # AgentContext (encapsulated run, workspace, and upstream results)
│   │   ├── models.py         # AgentType (5 agents), AgentStatus, AgentResult dataclasses
│   │   ├── prompts.py        # Specialized prompts for Architect, Builder, Tester, Breaker, Security
│   │   ├── architect.py      # ArchitectAgent (repository inspection & plan generation)
│   │   ├── builder.py        # BuilderAgent (code implementation inside isolated workspace)
│   │   ├── tester.py         # TesterAgent (sandbox test execution & structured metrics)
│   │   ├── breaker.py        # BreakerAgent (adversarial testing & weakness discovery)
│   │   ├── security.py       # SecurityAgent (scanner coordination & static vulnerability analysis)
│   │   ├── manager.py        # AgentManager (sequential 5-agent coordination & finding persistence)
│   │   └── exceptions.py     # Agent subsystem domain exceptions
│   ├── models/               # SQLAlchemy Relational Models
│   │   ├── project.py        # Project model (with workspaces relationship)
│   │   ├── workspace.py      # Workspace model (name, path, branch, sandboxes relationship)
│   │   ├── sandbox.py        # Sandbox model (status, container_id, limits, timestamps)
│   │   ├── agent_execution.py# AgentExecution model (run, agent_type, status, output, workspace, sandbox)
│   │   ├── finding.py        # Finding model (run, agent_exec, type, severity, category, evidence, remediation)
│   │   └── run.py            # EngineeringRun model (workspace_id, sandbox_id, agent_executions, findings)
│   ├── schemas/              # Pydantic validation schemas
│   │   ├── project.py        # Project schemas
│   │   ├── workspace.py      # WorkspaceCreate & WorkspaceResponse
│   │   ├── sandbox.py        # SandboxCreate, SandboxResponse, SandboxExecuteRequest, CommandResultResponse
│   │   ├── agent.py          # AgentExecutionResponse, AgentWorkflowStatusResponse
│   │   ├── finding.py        # FindingResponse, FindingsSummaryResponse
│   │   └── run.py            # RunResponse & RunLogsResponse
│   ├── api/                  # REST API Routers
│   │   ├── health.py         # GET /api/health
│   │   ├── projects.py       # CRUD /api/projects
│   │   ├── workspaces.py     # CRUD /api/projects/{id}/workspaces & /api/workspaces/{id}
│   │   ├── sandboxes.py      # Docker status, sandbox lifecycle, command execution
│   │   ├── agents.py         # Execute agent workflow, list agents, inspect execution, cancel
│   │   ├── findings.py       # Query findings, filter by type/severity/category, summary metrics
│   │   └── runs.py           # Project Engineering Runs, Execute, Logs, Cancel
│   ├── services/             # Business Logic Layer
│   │   ├── project_service.py # Project, Run, & Sandbox DB queries
│   │   └── execution_service.py # Background task execution, worktree & sandbox routing
│   └── tests/
│       ├── test_execution.py  # Phase 2 execution test suite
│       ├── test_workspaces.py # Phase 3 worktree test suite (zero-git mock provider)
│       ├── test_sandbox.py    # Phase 4 sandbox test suite (mount security, lifecycle, APIs)
│       ├── test_agents.py     # Phase 5 agent test suite (context, isolation, sequential workflow)
│       └── test_breaker_security.py # Phase 6 Breaker, Security, scanner abstraction, & Finding APIs
├── docker/                   # Container definitions
│   └── Dockerfile.sandbox    # Lightweight non-root sandbox image (python:3.12-slim)
└── frontend/                 # React + TypeScript + Vite Dashboard
    ├── src/
    │   ├── api/              # Type-safe API client (projects, runs, workspaces, sandboxes, agents, findings)
    │   ├── components/       # Header, Sidebar, Cards, Modals, 5-Agent Pipeline, Findings UI, Terminal
    │   ├── views/            # OverviewView, WorkspacesView, and AgentsView (5-agent profiles & guarantees)
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
| `DOCKER_SANDBOX_TIMEOUT` | Default command execution timeout in seconds | `60` |
| `DOCKER_SANDBOX_NETWORK` | Outbound network bridge enabled (`none` or `bridge`) | `none` |
| `DOCKER_SANDBOX_PIDS_LIMIT` | Max process limit per container (fork bomb defense) | `128` |
| `DOCKER_SANDBOX_PROVIDER` | Docker provider (`real` or `mock`) | `real` |
| `DOCKER_SANDBOX_USER` | Non-root container UID:GID | Optional |
| `SECURITY_SCANNING_ENABLED` | Enable automated security scanner engines | `true` |
| `SECURITY_SCANNERS` | Enabled scanner providers list | `pattern_scanner,bandit,pip-audit,npm-audit,semgrep,gitleaks` |
| `SECURITY_SCAN_NETWORK` | Network access for security scanners (offline isolation) | `false` |

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

Run the full automated test suite (32 tests across 5 suites, without executing any git commands):

```bash
# Run all Phase 2, Phase 3, Phase 4, Phase 5, and Phase 6 tests
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
4. **Autonomous Agent Team (Phase 5)**:
   - AgentContext encapsulation and upstream result passing
   - Architect Agent plan generation without source code mutations
   - Builder Agent plan ingestion and workspace execution
   - Tester Agent sandbox execution and structured pass/fail metrics parsing
   - Strict agent isolation (distinct workspaces and sandboxes per agent)
   - Sequential workflow completion (`Architect` → `Builder` → `Tester`)
   - Fail-fast error handling halting workflow without automatic retries
   - Full REST API integration flow for agent team execution and cancellation
5. **Breaker & Security Agents (Phase 6)**:
   - Breaker Agent adversarial test generation, execution, and structured finding extraction
   - Security Agent scanner discovery, unavailable scanner honesty, and static vulnerability parsing
   - Built-in regex pattern scanner for secrets (AWS, private keys, API keys), SQL injection, command injection, and path traversal
   - Structured `Finding` model database persistence and cascade deletion
   - Findings REST APIs: retrieval, multi-dimensional filtering (`type`, `severity`, `category`), and summary distribution
   - Complete 5-agent sequential workflow (`Architect` → `Builder` → `Tester` → `Breaker` → `Security`)
   - Fail-fast policy verification: Builder failure halts before Tester/Breaker/Security; Tester failure halts before Breaker/Security; Breaker failure halts before Security

---

## Agent Team & Workspace Architecture

### Agent Isolation Guarantee

```text
Architect Agent  ──>  Workspace A (run-{id}-architect)  ──>  Sandbox A
Builder Agent    ──>  Workspace B (run-{id}-builder)    ──>  Sandbox B
Tester Agent     ──>  Workspace C (run-{id}-tester)     ──>  Sandbox C
Breaker Agent    ──>  Workspace D (run-{id}-breaker)    ──>  Sandbox D
Security Agent   ──>  Workspace E (run-{id}-security)   ──>  Sandbox E
```

Agents never share a writable worktree directory. Each agent operates within its dedicated workspace and sandbox.
Breaker and Security operate strictly in read/test/scan mode and do NOT mutate production implementation files.

### Sequential Workflow Flow

```text
Engineering Goal
       │
       ▼
Architect Agent  ──>  Implementation Plan
       │
       ▼
Builder Agent    ──>  Implementation Summary
       │
       ▼
Tester Agent     ──>  Verified Test Report (Passed / Failed)
       │
       ▼
Breaker Agent    ──>  Adversarial Test Findings (Edge Cases, Boundaries)
       │
       ▼
Security Agent   ──>  Security Findings (Secrets, Injections, Vulnerabilities)
```

**Fail-Fast Policy**: If an agent fails at any stage, the workflow immediately halts, subsequent agents are not executed, and the engineering run is marked `FAILED`. No automatic retries occur in Phase 6.

---

## Structured Finding Model

Every discovered weakness or security vulnerability is stored as an evidence-backed record:

| Field | Description | Example |
| :--- | :--- | :--- |
| `type` | Finding engine source | `BREAKER` or `SECURITY` |
| `severity` | Impact rating | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO` |
| `category` | Technical weakness category | `INPUT_VALIDATION`, `SECRET`, `INJECTION`, `EDGE_CASE`, etc. |
| `title` | Concise descriptive title | `Application crashes on empty input array` |
| `file_path` | Source file location | `src/parser.py` |
| `line_number` | Line number where applicable | `42` |
| `evidence` | Verifiable execution output or code snippet | `IndexError: list index out of range at parser.py:42` |
| `reproduction` | Exact command or payload to reproduce | `parser.parse([])` |
| `remediation` | Recommended fix for the Builder | `Validate input array length before accessing elements.` |
| `status` | Lifecycle status | `OPEN` |

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

### Autonomous Agent Team (Phases 5 & 6)
- `POST /api/runs/{run_id}/agents/execute` — Start sequential 5-agent workflow (Architect $\rightarrow$ Builder $\rightarrow$ Tester $\rightarrow$ Breaker $\rightarrow$ Security).
- `GET /api/runs/{run_id}/agents` — List all agent executions and step statuses for a run.
- `GET /api/agent-executions/{agent_execution_id}` — Get detailed agent output, input summary, and diagnostics.
- `POST /api/runs/{run_id}/agents/cancel` — Cancel active agent workflow safely.

### Findings (Phase 6)
- `GET /api/runs/{run_id}/findings` — Retrieve findings for a run, with optional query filters (`type`, `severity`, `category`).
- `GET /api/runs/{run_id}/findings/summary` — Retrieve aggregated findings distribution (total, breaker, security, by severity, by category).
- `GET /api/runs/{run_id}/findings/{finding_id}` — Get single finding details with evidence, reproduction, and remediation.

### Engineering Runs
- `GET /api/projects/{id}/runs` — List runs for a project.
- `POST /api/projects/{id}/runs` — Create an engineering run (`goal`, optional `workspace_id`, optional `sandbox_id`).
- `GET /api/runs/{id}` — Fetch run details, status, timestamps, exit code, workspace & sandbox info.
- `POST /api/runs/{id}/execute` — Start direct execution.
- `GET /api/runs/{id}/logs` — Retrieve live streaming stdout/stderr or stored results.
- `POST /api/runs/{id}/cancel` — Terminate the active process safely and release resources.

---

## Out of Scope for Phase 6 (Scheduled for Future Phases)

- **Judge Agent** (Phase 8: Evaluation & pass-rate scoring)
- **Engineering Score** (Phase 8)
- **Autonomous Retry & Recovery Loops** (Phase 7: Self-healing Builder loops based on Breaker/Security findings)
- **Automatic Fix Application** (Breaker and Security identify weaknesses; Builder remains responsible for fixes in Phase 7)
- **Automated Branch Merging & Pull Request Generation**
- **Real-time WebSockets**
