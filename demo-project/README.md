# TaskForge AI — Autonomous Engineering Benchmark

## Overview

**TaskForge AI** is a full-stack project tracking and task management application built intentionally as a realistic, multi-tiered verification benchmark and demonstration target for autonomous software engineering agents in **Codex OS**.

The application features a clean, production-grade layered architecture spanning modern React frontend components, RESTful FastAPI routes, Pydantic data schemas, business service layers, SQLAlchemy models, and relational database persistence. It presents complex real-world code patterns that require autonomous agents to reason across multiple interconnected files.

---

## Problem Statement

Evaluating autonomous software engineering agents on isolated LeetCode snippets or trivial single-file scripts fails to test real-world readiness:

1. **Lack of Architectural Depth**: Real software requires updating relational models, migrating database schemas, validating request payloads, and updating UI states simultaneously.
2. **Missing Edge Cases**: Toy benchmarks lack boundary conditions (e.g., negative pagination limits, duplicate unique constraints, overdue date calculations, cascade deletions).
3. **No Realistic Test Harness**: Agents need access to real test suites with database fixtures, HTTP test clients, and measurable test pass rates to prove self-healing capability.

---

## Solution

TaskForge AI provides a realistic, full-stack application environment equipped with a comprehensive test suite and targeted edge cases:

* **Complete Layered Architecture**: Clear separation of concerns between API routers, service layers, schemas, and ORM models.
* **Realistic Business Logic**: Project lifecycles, task prioritization, status transitions (TODO $\to$ IN_PROGRESS $\to$ COMPLETED), activity comments, and cross-table dashboard analytics.
* **Deterministic Verification Surface**: Includes 31 pre-built Pytest unit tests, providing a ground truth for the Tester Agent to verify Builder modifications.
* **Targeted Adversarial Attack Surfaces**: Designed with boundary conditions (such as task pagination limits and unique email collision handling) that allow red-team agents (Breaker and Security) to detect real findings and verify self-healing multi-iteration workflows.

---

## Features

* **Project Lifecycle Management**: Full CRUD operations for projects, tracking active task counts and cascading relationships.
* **Task Tracking & Prioritization**: Multi-attribute task management supporting priority levels (LOW, MEDIUM, HIGH, URGENT), statuses, and due date tracking.
* **Search, Filtering & Pagination**: Multi-criteria task search by query string, status, priority, and assigned project with limit/skip pagination.
* **Discussion & Activity Comments**: Task-associated activity comment thread with automatic timestamping and relational cascade deletions.
* **Real-Time Analytics Dashboard**: Aggregates total projects, task completion rates, overdue task metrics, and priority breakdown distributions.
* **31 Automated Unit Tests**: Comprehensive Pytest test suite testing positive paths, 404 handling, cascade deletions, and constraint violations.

---

## Tech Stack

* **Frontend:** React 18, TypeScript, Vite, Lucide React Icons, custom Vanilla CSS design system (Dark Modern UI).
* **Backend:** Python 3.12, FastAPI (ASGI framework), Pydantic v2 data validation schemas, SQLAlchemy 2.0 ORM.
* **Database:** SQLite 3 (local zero-dependency testing) / PostgreSQL compatible.
* **APIs / Services:** RESTful JSON v1 API with automated OpenAPI / Swagger documentation.
* **Hosting / Deployment:** Dockerfile, Docker Compose.
* **Other Tools:** Pytest, FastAPI TestClient, Uvicorn.

---

## Codex / OpenAI Usage

TaskForge AI was constructed and verified in collaboration with OpenAI models and the Codex OS autonomous pipeline:

* **Ideation & Schema Design**: OpenAI models helped define the relational foreign-key schemas, cascade deletion rules, and boundary condition requirements.
* **Full-Stack Code Generation**: Used Codex to scaffold clean, modular Python service layers, FastAPI endpoints, Pydantic validation schemas, and React TypeScript components.
* **Test Suite Authoring**: Automated generation of 31 comprehensive Pytest unit and integration tests covering CRUD operations, filtering, and constraint enforcement.
* **Adversarial Test Surface Creation**: Prompted OpenAI to identify subtle boundary conditions (such as unvalidated pagination parameters and case-insensitive email collision handling) to serve as verification targets for Breaker and Security agents.
* **Documentation & Verification**: Generated API documentation, seed data scripts, and automated verification procedures.

---

## Demo

### Live Demo

* **Frontend Web App**: `http://localhost:3000` *(or port 5173 when launched via Vite)*
* **Backend API Docs**: `http://localhost:8001/docs` *(or port 8000 when running standalone)*
* **Live Deployment Link**: *[https://taskforge.demo.app](https://github.com/Prabhu-E-S/Codex-OS)* *(Replace with your deployed project link)*

### Demo / Pitch Video

* **Walkthrough Video**: *[Watch the TaskForge Demo on YouTube](https://youtu.be/example)* *(Add your demo or pitch video link here)*
* *Summary*: Video demonstrating TaskForge UI task management, dashboard statistics, API endpoints, and autonomous self-healing via Codex OS agents.

---

## Screenshots

| Dashboard Analytics | Task Management Board |
|:---:|:---:|
| ![TaskForge Dashboard](https://raw.githubusercontent.com/Prabhu-E-S/Codex-OS/main/demo-project/docs/screenshots/dashboard.png) | ![Task Board](https://raw.githubusercontent.com/Prabhu-E-S/Codex-OS/main/demo-project/docs/screenshots/tasks.png) |

---

## How to Run Locally

### 1. Backend Setup

```bash
cd demo-project/backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
python -m app.main
```
*Backend runs at:* `http://localhost:8000`  
*Swagger Docs:* `http://localhost:8000/docs`

### 2. Frontend Setup

```bash
cd demo-project/frontend
npm install
npm run dev
```
*Frontend runs at:* `http://localhost:5173`

### 3. Run Automated Tests

```bash
cd demo-project/backend
python -m pytest tests/ -q
```
*(All 31 unit tests pass out of the box)*

### 4. 1-Command Docker Deployment

```bash
cd demo-project
docker-compose up --build -d
```

---

## Additional Notes

* **Autonomous Target Role**: TaskForge AI is pre-configured as Project ID `349` in the Codex OS database, enabling instant multi-iteration autonomous test runs.
* **Deterministic Fixtures**: All backend tests utilize in-memory SQLite fixtures (`tests/conftest.py`) with full transaction isolation, ensuring tests execute in under 1 second without leaving residual state.
* **Future Enhancements**:
  * WebSocket-based real-time collaborative task updates.
  * Role-based access control (RBAC) and user authentication.
  * File attachment uploads with S3/MinIO backend storage.
