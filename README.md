# Kompass: The Autonomous AI Travel Architect

Kompass is an autonomous travel planning application that automatically optimizes itineraries, budgets, and connections. It features a FastAPI backend utilizing PydanticAI (powered by Gemini) and an event-driven Next.js frontend integrated with CopilotKit.

> 🧭 **See the architecture & full request flow visually:** [m-ali-ml.github.io/kompass](https://m-ali-ml.github.io/kompass/) — an interactive, step-by-step walkthrough of the whole system.

---

## 📁 Repository Structure

* **`backend/`**: Python web service built with FastAPI, PydanticAI, and SQLite persistence, conforming to Hexagonal Architecture patterns.
* **`frontend/`**: Next.js React client styled with Tailwind CSS v4, integrating CopilotKit and an interactive Google Map (via `@vis.gl/react-google-maps`).
* **`docs/`**: Living, post-building documentation representing what has *actually* been built in the project.
* **`pre-docs/`**: Static requirements, PRD, and design specs created *before* construction.
* **`sessions/`**: Developer session logs updated at the end of each work stream.
* **`.agents/`**: Core guidelines and automation instructions (skills) for AI coding assistants.

---

## 📖 Project Documentation

The post-building docs live in `docs/` as a single connected site — an interactive flow demo plus five visual reference pages, all cross-linked with a shared nav — published via GitHub Pages at [m-ali-ml.github.io/kompass](https://m-ali-ml.github.io/kompass/). Each HTML page has a markdown twin with the same content in prose form:

* [🧭 Interactive Flow Visualization](https://m-ali-ml.github.io/kompass/) — the homepage: a piece-by-piece, click-through walkthrough of the whole app (source: [`docs/index.html`](./docs/index.html))
* [Architecture & Flow Guide](https://m-ali-ml.github.io/kompass/architecture.html) ([markdown](./docs/architecture.md))
* [Design & Styling Specs](https://m-ali-ml.github.io/kompass/design.html) ([markdown](./docs/design.md))
* [Product & Feature Status](https://m-ali-ml.github.io/kompass/product.html) ([markdown](./docs/product.md))
* [User Story Progress Tracker](https://m-ali-ml.github.io/kompass/user-stories.html) ([markdown](./docs/user-stories.md))
* [Eval Learnings Log](https://m-ali-ml.github.io/kompass/evals.html) ([markdown](./docs/evals.md)) — the technical reference and running record for the agent-behavior eval suite (`backend/evals/`)
* [Agent Eval Suite — Learnings Log](https://m-ali-ml.github.io/kompass/evals.html) ([markdown reference](./docs/evals.md)) — how the LLM agent is evaluated (golden dataset, deterministic + LLM-judge scoring), and a chronological log of what each eval run found

Historical blueprints and requirements can be found in:

* [Product Requirements Document (PRD)](./pre-docs/product.md)
* [System Architecture Specification](./pre-docs/architecture.md)
* [Vibe Design Guidelines](./pre-docs/design.md)
* [Product User Stories](./pre-docs/user-stories.md)

---

## 🚀 Getting Started

### 1. Backend Setup

The backend uses **Python 3.14+** and is managed via **`uv`**.

1. Navigate to the backend directory:

   ```bash
   cd backend
   ```

2. Sync dependencies:

   ```bash
   uv sync
   ```

3. Copy environment configuration and configure your secrets (e.g., API keys for Gemini, Langfuse):

   ```bash
   cp .env.example .env
   ```

4. Start the backend development server:

   ```bash
   uv run uvicorn app.main:app --reload
   ```

   The API will be available at `http://localhost:8000`.

### 2. Frontend Setup

The frontend is built on **Next.js 16** and **React 19**.

1. Navigate to the frontend directory:

   ```bash
   cd frontend
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Copy environment configuration and configure any required environment variables:

   ```bash
   cp .env.example .env.local
   ```

4. Start the frontend development server:

   ```bash
   npm run dev
   ```

   The interface will be available at `http://localhost:3000`.

### 3. One-command dev environment

`scripts/dev.sh` starts both servers together (backend on `:8000`, frontend on `:3000`), logging to a temporary `dev.log` at the repo root:

```bash
./scripts/dev.sh        # dev mode (hot reload)
./scripts/dev.sh -p     # production build + start
```

### 4. Environment notes

* **`MCP_MODE`** (backend): defaults to `mock` — the accommodations tool serves deterministic fake data with no network calls. Set `MCP_MODE=live` (and a `SERPAPI_API_KEY`) for real Google Hotels prices. Flights always use the keyless Kiwi.com MCP.
* **Production URLs** (frontend): set `BACKEND_URL` (server-side rewrite target) and `NEXT_PUBLIC_COPILOTKIT_ENDPOINT` (streaming agent endpoint) when the backend isn't `localhost:8000`.

---

## ✅ Running Tests

```bash
# Backend unit/integration tests
cd backend && uv run python -m pytest

# Frontend unit tests (Vitest)
cd frontend && npm run test:unit

# Frontend lint
cd frontend && npm run lint

# End-to-end tests (Playwright; boots both servers on isolated ports + DB)
cd frontend && npm run test:e2e

# Agent-behavior eval suite (real LLM against deterministic fixtures — see docs/evals.md)
cd backend && uv run python -m evals.run
```

These test *code*. The agent's *behavior* (tool selection, constraint adherence,
anti-fabrication, HITL) is measured separately by an LLM eval suite — a 30-case
golden dataset run headless against the real agent with deterministic fakes for
flights/hotels/research, scored by 10 evaluators (7 deterministic + 3
LLM-as-judge):

```bash
# Full eval run against the model configured in backend/.env
cd backend && uv run python -m evals.run

# Live dashboard reading artifacts/eval_report/eval_report_*.json (auto-refreshes)
cd backend && uv run python -m evals.dashboard   # → http://localhost:8420
```

See [`docs/evals.md`](./docs/evals.md) for the architecture and
[`docs/evals.html`](https://m-ali-ml.github.io/kompass/evals.html) for the
running log of what each eval run has found.

---

## 🛠️ Developer Skills & Guidelines

Coding agents operating on this repository must follow instructions listed in the `.agents/skills` directory:

* [Daily Session Logging Guide](./.agents/skills/session-logging/SKILL.md)
* [Post-Docs Maintenance Guide](./.agents/skills/post-docs-updater/SKILL.md)
