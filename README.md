# Codex OS — The Autonomous Software Engineering Sandbox

## Overview

**Codex OS** is an autonomous software engineering platform that orchestrates a collaborative team of specialized AI agents to analyze, build, test, attack, and evaluate codebases end-to-end with zero human intervention in the loop. 

Users define an engineering objective—such as fixing boundary condition bugs, implementing an API endpoint, or refactoring security vulnerabilities—and Codex OS dispatches an autonomous multi-iteration pipeline:

$$\text{Architect} \longrightarrow \text{Builder} \longrightarrow \text{Tester} \longrightarrow \text{Breaker} \longrightarrow \text{Security} \longrightarrow \text{Orchestrator Decision}$$

Operating within isolated Git worktrees and governed Docker sandboxes, the agents write code, execute test suites, adversarially fuzz implementations, and run comprehensive vulnerability scans. When issues are discovered, the orchestrator initiates a closed-loop self-healing retry cycle, feeding validated findings back into the Builder until quality thresholds are verified and an evidence-backed Engineering Score is generated.

---

## Problem Statement

While modern AI coding assistants (Copilot, ChatGPT, Claude) have accelerated snippet generation, autonomous software engineering remains broken in production:

1. **Hallucination Without Verification**: Single-shot LLM code generation regularly produces code that looks plausible but fails unit tests, breaks existing functionality, or crashes under runtime edge cases.
2. **Missing Adversarial & Security Hardening**: Code generation models do not adversarially test their own outputs. They overlook boundary overflows, null-pointer dereferences, secret leaks, and injection risks.
3. **Contaminated Host Environments**: Executing arbitrary AI-generated code directly on development machines risks data loss, file system contamination, and untracked side-effects.
4. **Human Review Bottlenecks**: Developers still spend hours manually reviewing diffs, debugging regressions, and writing test cases for code that AI claimed was complete.
5. **Absence of Objective Quality Metrics**: Existing tools produce vague qualitative explanations rather than transparent, deterministic, mathematical metrics proving whether a code modification is safe to merge.

---

## Solution

Codex OS solves these fundamental limitations by providing an **isolated, adversarial, and self-healing multi-agent sandbox**:

* **Role-Specialized Autonomous Agents**:
  * **Architect Agent**: Ingests repository structure, documentation, and goals to formulate a phased implementation blueprint.
  * **Builder Agent**: Executes isolated code modifications in a dedicated workspace following the Architect's plan.
  * **Tester Agent**: Executes automated test suites (e.g., Pytest, Jest), measuring test pass rates, failures, and line coverage.
  * **Breaker Agent**: Acts as an adversarial fuzzing red team, discovering negative input crashes and edge-case failure conditions.
  * **Security Agent**: Executes static analyzers, dependency vulnerability scanners (Bandit, pip-audit, Semgrep), and secret detection.
* **Evidence-Based Finding Lifecycle**: Findings discovered by Breaker or Security enter a deterministic lifecycle (`OPEN` $\to$ `RESOLVED`). Issues are resolved **only** when subsequent validation runs confirm the defect is absent—never based on Builder claims.
* **Hermetic Sandbox Isolation**: Every agent executes within isolated Git worktrees and constrained Docker containers (governed CPU, memory, timeout, and `--network none` isolation).
* **Deterministic Self-Healing Orchestration**: A state-machine policy evaluates active validation findings and test outcomes to automatically retry the Builder with actionable feedback (`RETRY_BUILDER`) or complete the run (`STOP_SUCCESS`).
* **Honest 6-Dimensional Engineering Score**: Calculates an evidence-based quality score (0–100) assessing Correctness, Security, Test Coverage, Maintainability, Performance, and Regression Risk.

---

## Features

* **Autonomous 5-Agent Pipeline**: Seamless, fully automated multi-agent workflow consisting of Architect, Builder, Tester, Breaker, and Security agents.
* **Self-Healing Iteration Loop**: Closed-loop multi-iteration retry cycle that feeds compiler errors, failing test traces, and adversarial findings back to the Builder.
* **Evidence-Based Finding Lifecycle**: Deterministic finding identity matching and state reconciliation between iterations; findings transition to `RESOLVED` only upon verified validation agent confirmation.
* **Real-Time Control Room UI**: Live observability dashboard displaying real-time agent execution states, iteration timelines, sanitized logs, event streams, and open vs. resolved finding tallies.
* **Multi-Layered Sandbox Isolation**: Prevents host contamination using Git worktrees for branch isolation and Docker containers with strict resource and network constraints.
* **6-Dimensional Engineering Score**: Transparent, formulaic grading system that scores software across Correctness (30%), Security (20%), Test Coverage (15%), Maintainability (15%), Performance (10%), and Regression Risk (10%).
* **Multi-Scanner Security Auditing**: Native aggregation of automated tools including Bandit AST scanning, Pip-audit CVE checks, secret pattern detection, and Semgrep rules.
* **Repository-Agnostic Operation**: Capable of executing autonomous engineering runs across diverse Python and TypeScript/JavaScript codebases.

---

## Tech Stack

* **Frontend:** React 19, TypeScript, Vite, Lucide Icons, Vanilla CSS with custom design system tokens (Dark Modern UI).
* **Backend:** Python 3.12+, FastAPI (ASGI), Pydantic v2 schemas, SQLAlchemy 2.0 ORM, Uvicorn server.
* **Database:** PostgreSQL (production deployment) / SQLite 3 (local zero-configuration development) with automated schema migrations.
* **APIs / Services:** OpenAI Codex / GPT API integration, Codex CLI execution runner, RESTful API endpoints, 3-second live telemetry polling.
* **Hosting / Deployment:** Docker, Docker Compose, Nginx reverse proxy.
* **Other Tools:** Pytest, Bandit, Pip-audit, Semgrep, Git Worktrees, AnyIO, Process Manager.

---

## Codex / OpenAI Usage

Codex OS leverages **OpenAI Codex, GPT models, and prompt orchestration** as core cognitive engines throughout the engineering workflow:

* **Ideation & Adversarial Personas**: OpenAI models were used during initial design to establish the separation of concerns between creator (Builder) and adversary (Breaker), ensuring agents have orthogonal incentives.
* **Autonomous Code Generation (Builder Agent)**: The Builder uses the Codex execution engine to read repository context, parse the Architect's blueprint, and perform multi-file code modifications, bug fixes, and new feature implementations.
* **Adversarial Fuzzing & Boundary Testing (Breaker Agent)**: Utilizes OpenAI prompts trained on negative test patterns, fuzz payloads, and edge cases to find inputs that induce unhandled exceptions or denial-of-service conditions.
* **Architectural Planning (Architect Agent)**: Uses OpenAI reasoning to analyze project file trees, dependency graphs, and user goals, producing structured implementation plans without modifying code.
* **Security Auditing (Security Agent)**: Combines deterministic AST scanner reports with OpenAI static analysis to detect injection flaws, hardcoded credentials, and insecure configurations, providing concrete remediation snippets.
* **Contextual Retry & Feedback Loops**: Formulates dynamic retry prompts (`build_builder_retry_prompt`) that feed exact test failure traces, compiler diagnostics, and Breaker findings back into Codex for closed-loop remediation.
* **UI/UX & Documentation**: Assisted in synthesizing responsive CSS design tokens for the Control Room and structuring interactive API schemas.

---

## Demo

### Live Demo
After setting up
* **Local Web Interface**: `http://localhost:5173` (Frontend) & `http://localhost:8000/docs` (Interactive API Docs)


### Demo / Pitch Video

* **Walkthrough Video**: *[Watch the Codex OS Autonomous Demo on Drive]([https://youtu.be/example](https://drive.google.com/drive/folders/13WLFOb98MgdJw0CkvnP-OKSFON3sOlY_?usp=sharing))* *(Add your demo or pitch video link here)*
* *Summary*: The demo video demonstrates creating an autonomous run on a target project (`Task Forge AI`), observing Iteration 1 Breaker finding discovery, watching Builder self-heal the codebase in Iteration 2, and verifying finding resolution to `RESOLVED` in the Control Room.

---

## Screenshots

Project Overiew
<img width="1918" height="862" alt="image" src="https://github.com/user-attachments/assets/57ee190e-334c-41ba-97fc-88d9e4e2be14" />

Control Room
<img width="1897" height="863" alt="image" src="https://github.com/user-attachments/assets/e99becfb-3069-4762-926b-d185dd5f2015" />

Workspace and Sandboxes
<img width="1917" height="832" alt="image" src="https://github.com/user-attachments/assets/e1db4ba9-f6b9-4a81-8df1-58d7a448d982" />

---

## How to Run Locally

### Prerequisites

* Python 3.12+
* Node.js 20+ and npm
* Docker Desktop (optional, for containerized sandbox execution)
* OpenAI API Key or Codex CLI installed in PATH

### 1. Clone & Configure

```bash
git clone https://github.com/Prabhu-E-S/Codex-OS.git
cd "Codex OS"
cp .env.example .env
# Configure OPENAI_API_KEY or CODEX_COMMAND in .env if needed
```

### 2. Run Backend

```bash
# Set up Python virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

pip install -r backend/requirements.txt
python -m backend.main
```
*Backend runs at:* `http://localhost:8000`  
*Interactive Swagger API Docs:* `http://localhost:8000/docs`

### 3. Run Frontend

```bash
# In a new terminal:
cd frontend
npm install
npm run dev
```
*Frontend runs at:* `http://localhost:5173`

### 4. (Alternative) 1-Command Docker Deployment

```bash
docker-compose up --build -d
```
* Access Frontend: `http://localhost:80`
* Access Backend API: `http://localhost:8000`
* PostgreSQL Database: `localhost:5432`

### 5. Run Automated Test Suite

```bash
python -m pytest backend/tests/ -q
```
*(All 101 tests pass cleanly out of the box)*

---

## Additional Notes

* **Evidence-Based Finding Verification**: Unlike systems that trust LLM claims of having "fixed" a bug, Codex OS enforces cryptographic and execution verification. A finding only transitions from `OPEN` to `RESOLVED` when the authoritative red-team agent (Breaker or Security) executes against the new code and confirms the issue is gone.
* **Governed Resource Constraints**: Sandbox containers run with non-root users, `--network none`, capped memory (512MB default), CPU limits (1.0 core), and strict timeout bounds to prevent resource exhaustion or runaway processes.
* **Audited Demo Project Included**: A dedicated target application (`TaskForge AI`, located in [`demo-project/`](demo-project/)) is included for live verification of multi-agent autonomous runs.
* **Future Roadmap**:
  * Multi-repository cross-service orchestration.
  * Native GitHub Pull Request creation and CI/CD webhooks.
  * Support for additional runtime languages (Go, Rust, Java).
  * Automated synthetic benchmark generation from production incident logs.
