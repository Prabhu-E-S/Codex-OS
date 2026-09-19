# Codex OS — System Architecture

> **Phase 10: Final Hardening, Demo & Deployment Readiness**

This document describes the complete architecture of Codex OS — the autonomous software engineering sandbox.

---

## System Topology

```mermaid
graph TB
    subgraph "Frontend (React + Vite)"
        UI[Control Room UI]
        API_CLIENT[API Client]
    end

    subgraph "Backend (FastAPI)"
        API[REST API Layer]
        ORCH[Orchestrator Manager]
        EVAL[Evaluation Engine]
        CTRL_SVC[Control Room Service]
        EXEC_SVC[Execution Service]
    end

    subgraph "Agent Pipeline"
        ARCH[Architect Agent]
        BUILD[Builder Agent]
        TEST[Tester Agent]
        BREAK[Breaker Agent]
        SEC[Security Agent]
    end

    subgraph "Infrastructure"
        DB[(SQLite / PostgreSQL)]
        WS[Git Worktree Workspaces]
        DOCKER[Docker Sandbox Engine]
        CODEX[Codex CLI]
    end

    UI --> API_CLIENT
    API_CLIENT --> API
    API --> ORCH
    API --> EVAL
    API --> CTRL_SVC
    API --> EXEC_SVC
    ORCH --> ARCH
    ORCH --> BUILD
    ORCH --> TEST
    ORCH --> BREAK
    ORCH --> SEC
    ARCH --> WS
    BUILD --> WS
    BUILD --> DOCKER
    TEST --> DOCKER
    BREAK --> DOCKER
    SEC --> DOCKER
    EXEC_SVC --> CODEX
    API --> DB
    CTRL_SVC --> DB
```

---

## Agent Pipeline Flow

The orchestrator drives a deterministic multi-iteration pipeline:

```mermaid
flowchart LR
    START([Run Created]) --> ARCH

    ARCH[🏗️ Architect\nAnalyzes codebase\nGenerates plan]
    ARCH --> BUILD

    BUILD[🔨 Builder\nImplements changes\nWrites code]
    BUILD --> TEST

    TEST[🧪 Tester\nRuns test suite\nReports coverage]
    TEST --> BREAK

    BREAK[💥 Breaker\nAdversarial fuzzing\nEdge case attacks]
    BREAK --> SEC

    SEC[🔒 Security\nScans for vulns\nPattern analysis]
    SEC --> DECIDE

    DECIDE{🎯 Decision\nPolicy Evaluation}
    DECIDE -->|STOP_SUCCESS| DONE([✅ Completed])
    DECIDE -->|STOP_FAILURE| FAIL([❌ Failed])
    DECIDE -->|RETRY_BUILDER| BUILD

    style ARCH fill:#4A90D9,color:#fff
    style BUILD fill:#7B68EE,color:#fff
    style TEST fill:#50C878,color:#fff
    style BREAK fill:#FF6B6B,color:#fff
    style SEC fill:#FFB347,color:#fff
    style DECIDE fill:#888,color:#fff
    style DONE fill:#2ecc71,color:#fff
    style FAIL fill:#e74c3c,color:#fff
```

---

## Orchestrator Decision Policy

After each iteration, `OrchestratorPolicy.evaluate()` inspects:

| Signal | Threshold | Effect |
|--------|-----------|--------|
| Tester status COMPLETED | — | Positive signal |
| Builder exit code 0 | — | Positive signal |
| Critical security findings | > 0 CRITICAL | → `STOP_FAILURE` |
| High security findings | > 5 HIGH | → `RETRY_BUILDER` |
| Breaker findings | > 10 | → `RETRY_BUILDER` |
| Max iterations reached | iter == max | → `STOP_FAILURE` or `STOP_SUCCESS` |

---

## Evaluation & Engineering Score

The `EvaluationEngine` assigns a 0–100 composite score across 6 weighted dimensions:

```mermaid
pie title Engineering Score Weights
    "Correctness" : 30
    "Security" : 20
    "Test Coverage" : 15
    "Maintainability" : 15
    "Performance" : 10
    "Regression Risk" : 10
```

Each dimension is scored `0–100` based on evidence extracted from agent outputs. The composite score is:

```
overall_score = Σ (dimension_score × weight) × 100
```

If insufficient evidence exists, the dimension reports `INSUFFICIENT_EVIDENCE` and contributes a penalized score of `30`.

---

## Sandbox Security Model

```mermaid
graph TD
    AGENT[Agent Executes Command] --> MGR[SandboxManager]
    MGR --> VALIDATE[validate_mount_security]
    VALIDATE -->|Rejects| BLOCK[🚫 MountSecurityError\nDocker socket\nPath traversal\nSystem dirs]
    VALIDATE -->|Allows| DOCKER[Docker Container]
    DOCKER --> LIMITS[Resource Limits\nCPU ≤ 4.0 cores\nMemory ≤ 8g\nPIDs ≤ 1024\nNetwork: none\nTimeout ≤ 3600s]
    LIMITS --> EXEC[Isolated /workspace\nnon-root user\ndisposable]
```

---

## Git Worktree Isolation

Each agent execution operates in an isolated Git worktree:

```
CODEX_WORKSPACE_ROOT/
  ├── ws-run-1-architect-20240101T120000/   ← Architect worktree
  ├── ws-run-1-builder-20240101T120100/     ← Builder worktree
  ├── ws-run-1-tester-20240101T120200/      ← Tester worktree
  └── ws-run-1-breaker-20240101T120300/     ← Breaker worktree
```

Worktrees are created from the project's `repository_path` base and deleted on completion. This guarantees agents never interfere with each other's in-progress changes.

---

## Database Schema

```mermaid
erDiagram
    Project ||--o{ EngineeringRun : has
    EngineeringRun ||--o| Workspace : uses
    EngineeringRun ||--o| Sandbox : uses
    EngineeringRun ||--o{ AgentExecution : spawns
    EngineeringRun ||--o{ Finding : produces
    EngineeringRun ||--o| OrchestrationState : tracks
    EngineeringRun ||--o{ Evaluation : scored_by

    AgentExecution ||--o| Workspace : allocated
    AgentExecution ||--o| Sandbox : runs_in
    AgentExecution ||--o{ Finding : generates
```

---

## API Surface (Phase 10)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health (DB + Docker + Codex status) |
| GET/POST | `/api/projects` | Project CRUD |
| GET/POST | `/api/projects/{id}/runs` | Run management |
| POST | `/api/runs/{id}/execute` | Start Codex execution |
| POST | `/api/runs/{id}/start-autonomous` | Launch orchestrated pipeline |
| GET | `/api/runs/{id}/orchestration` | Orchestration status |
| POST | `/api/runs/{id}/pause\|resume` | Boundary-safe control |
| GET | `/api/runs/{id}/control-room` | Full dashboard snapshot |
| POST | `/api/runs/{id}/evaluate` | Trigger evaluation scoring |
| GET | `/api/runs/{id}/findings` | Security/breaker findings |

---

## Deployment Architecture

```mermaid
graph LR
    USER[Browser] --> NGINX[Nginx :80\nFrontend SPA]
    NGINX --> API[FastAPI :8000\nBackend]
    API --> PG[(PostgreSQL :5432)]
    API --> DOCKER_SOCK[Docker Socket\n/var/run/docker.sock]
    DOCKER_SOCK --> SANDBOX[Isolated Sandbox\nContainers]
    API --> WORKSPACES[/app/workspaces\nGit Worktrees]
```

> ⚠️ **Security Note**: Mounting the Docker socket grants the backend container full control over the host Docker daemon. This is architecturally required for sandbox provisioning and should only be deployed in trusted environments.
