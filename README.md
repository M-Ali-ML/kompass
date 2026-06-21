# Kompass: The Autonomous AI Travel Architect

Kompass is an autonomous travel planning application that automatically optimizes itineraries, budgets, and connections. It features a FastAPI backend utilizing PydanticAI (powered by Gemini) and an event-driven Next.js frontend integrated with CopilotKit.

---

## 📁 Repository Structure

* **`backend/`**: Python web service built with FastAPI, PydanticAI, and SQLite persistence, conforming to Hexagonal Architecture patterns.
* **`frontend/`**: Next.js React client styled with Tailwind CSS v4, supporting CopilotKit and Leaflet maps.
* **`docs/`**: Living, post-building documentation representing what has *actually* been built in the project.
* **`pre-docs/`**: Static requirements, PRD, and design specs created *before* construction.
* **`sessions/`**: Developer session logs updated at the end of each work stream.
* **`.agents/`**: Core guidelines and automation instructions (skills) for AI coding assistants.

---

## 📖 Project Documentation

For detailed guides on the implemented system, refer to the post-building docs:

* [Architecture & Flow Guide](file:///Users/aly/repos/kompass/docs/architecture.md)
* [Design & Styling Specs](file:///Users/aly/repos/kompass/docs/design.md)
* [Product & Feature Status](file:///Users/aly/repos/kompass/docs/product.md)
* [User Story Progress Tracker](file:///Users/aly/repos/kompass/docs/user-stories.md)

Historical blueprints and requirements can be found in:

* [Product Requirements Document (PRD)](file:///Users/aly/repos/kompass/pre-docs/product.md)
* [System Architecture Specification](file:///Users/aly/repos/kompass/pre-docs/architecture.md)
* [Vibe Design Guidelines](file:///Users/aly/repos/kompass/pre-docs/design.md)
* [Product User Stories](file:///Users/aly/repos/kompass/pre-docs/user-stories.md)

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

---

## 🛠️ Developer Skills & Guidelines

Coding agents operating on this repository must follow instructions listed in the `.agents/skills` directory:

* [Daily Session Logging Guide](file:///Users/aly/repos/kompass/.agents/skills/session-logging/SKILL.md)
* [Post-Docs Maintenance Guide](file:///Users/aly/repos/kompass/.agents/skills/post-docs-updater/SKILL.md)
