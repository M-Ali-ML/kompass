# Kompass App: System Architecture (Post-Building)

This document details the *implemented* system architecture of the Kompass travel planning application as of Phase 5.

---

## 1. Architectural Overview
The system consists of a Python FastAPI backend and a Next.js frontend, integrated using the AG-UI protocol and CopilotKit. The backend follows a hexagonal (ports & adapters) design, talks to a flights MCP server over stdio, persists trips/preferences in SQLite, and uses a grounded web-search sub-agent for live data.

```
        +-----------------------------------------------+
        |               Next.js Frontend                |
        |  CopilotKit v2 Chat + Generative-UI tool cards |
        |  (preferences, flights, dates, scenarios)      |
        |  Tailwind CSS v4 "Candy" theme                 |
        +-----------------------+-----------------------+
                                | SSE Streaming (AG-UI Protocol)
                                v
        +-----------------------+-----------------------+
        |                 FastAPI Web App               |
        |   main.py (lifespan: init_db + flights MCP)   |
        |   api/routes.py (/api/copilotkit + REST)      |
        +----------+-----------------------+------------+
                   |                       |
                   v                       v
        +----------+---------+   +---------+-----------+
        |  PydanticAI Agent  |   |  SQLite Persistence |
        |  agent/agent.py    |   |  db.py + adapters   |
        +----------+---------+   +---------------------+
                   |
        +----------+----------+-------------------+
        |          |          |                   |
        v          v          v                   v
  Prompt Svc   Flights MCP   Research sub-agent  Repositories
  (file)       (stdio)       (Gemini grounding)  (trips/profile)
```

---

## 2. Backend Layer (Hexagonal Architecture)
The backend follows a **Hexagonal Architecture (Ports & Adapters)** pattern to separate the core business logic (agent & models) from infrastructure details (prompt loading, flight data, persistence).

### A. Core Domain Models
Located in `backend/app/domain/`:
* [trip.py](file:///Users/aly/repos/kompass/backend/app/domain/trip.py) — `TripRequest` model (destination, duration, month, budget, traveler count).
* [user_preferences.py](file:///Users/aly/repos/kompass/backend/app/domain/user_preferences.py) — `UserPreferences` model (direct flights only, preferred transit modes, hotel class, vibe tags, `currency`) plus a `merged_with()` layering helper.
* [itinerary.py](file:///Users/aly/repos/kompass/backend/app/domain/itinerary.py) — `Itinerary` wrapping `Leg` (with `TransportMode` enum), `Accommodation`, and `DaySummary` (each day has a `title`, `description`, and a `schedule` of time-blocked `PlanItem`s).
* [scenario.py](file:///Users/aly/repos/kompass/backend/app/domain/scenario.py) — `Scenario` model plus `CostBreakdown` (transportation / accommodation / grand_total) and `StressFactors` (layover count, overnight travel, tight connection, total travel hours). Adds `comparison_label`, `start_date`/`end_date`, and `highlights`.
* [flights.py](file:///Users/aly/repos/kompass/backend/app/domain/flights.py) — `FlightOption` and `FlightDateOption` returned by the flight adapter.
* **ORM models** in `backend/app/domain/models/`: [trip.py](file:///Users/aly/repos/kompass/backend/app/domain/models/trip.py) (`Trip`, `Message`) and [profile.py](file:///Users/aly/repos/kompass/backend/app/domain/models/profile.py) (`UserProfile` singleton), registered on the shared `Base.metadata`.

### B. Ports (Interfaces)
Located in `backend/app/ports/`:
* [prompt_service.py](file:///Users/aly/repos/kompass/backend/app/ports/prompt_service.py) — `PromptServicePort` for loading prompt templates.
* [flight_service.py](file:///Users/aly/repos/kompass/backend/app/ports/flight_service.py) — `FlightServicePort` for `search_flights` / `find_cheapest_dates`.
* [trip_repository.py](file:///Users/aly/repos/kompass/backend/app/ports/trip_repository.py) — `TripRepository` (list/get/create/upsert/replace_messages/delete).
* [user_profile_repository.py](file:///Users/aly/repos/kompass/backend/app/ports/user_profile_repository.py) — `UserProfileRepository` (get/save preferences).

### C. Adapters (Implementations)
Located in `backend/app/adapters/`:
* [file_prompt_service.py](file:///Users/aly/repos/kompass/backend/app/adapters/file_prompt_service.py) — `FilePromptService` loading system prompt markdown.
* [mcp_flight_service.py](file:///Users/aly/repos/kompass/backend/app/adapters/mcp_flight_service.py) — `MCPFlightServiceAdapter` holding a persistent stdio MCP session and parsing results into `FlightOption` / `FlightDateOption`.
* [sqlite_trip_repository.py](file:///Users/aly/repos/kompass/backend/app/adapters/sqlite_trip_repository.py), [sqlite_user_profile_repository.py](file:///Users/aly/repos/kompass/backend/app/adapters/sqlite_user_profile_repository.py), and [sqlite_saved_scenario_repository.py](file:///Users/aly/repos/kompass/backend/app/adapters/sqlite_saved_scenario_repository.py) — SQLAlchemy async implementations of the repository ports.

### D. Persistence
* [db.py](file:///Users/aly/repos/kompass/backend/app/db.py) — shared async SQLAlchemy engine + `SessionLocal` sessionmaker (aiosqlite), `Base`, and `init_db()` which bootstraps the schema via `create_all`. Repositories depend on the sessionmaker, not the engine.
* Tables: `trips` (conversation per `thread_id`), `messages` (turns, cascade-deleted with the trip), `user_profiles` (global preferences), and `saved_scenarios` — user-bookmarked scenarios. A saved scenario stores the full `Scenario` JSON plus denormalized, queryable columns (`destination`, `grand_total`, `stress_score`, dates) and an optional `trip_id` (SET NULL so saves outlive a deleted conversation).

### E. MCP Servers
* [flights_server.py](file:///Users/aly/repos/kompass/backend/app/mcp_servers/flights_server.py) — a standalone FastMCP stdio server exposing `search_flights` and `find_cheapest_dates`, backed by the **SerpApi Google Flights API** (structured Google Flights results; key via `SERPAPI_API_KEY`, exported from `app.config` so the subprocess inherits it). Replaced the old `fli` scraper + synthetic fallback (unreliable / misleading fake prices). `find_cheapest_dates` probes a bounded set of candidate dates (`FLIGHTS_DATE_SAMPLES`, default 4) since SerpApi has no future date-grid. **Reliability contract:** when the key is missing or SerpApi errors/returns nothing, the tools return `available: false` with no fabricated data, and the agent falls back to `search_web`.

---

## 3. PydanticAI Agent Layer
The agent framework is managed via PydanticAI.

* **Agent Definition:** [agent.py](file:///Users/aly/repos/kompass/backend/app/agent/agent.py) instantiates `kompass_agent` with `output_type=Union[str, Scenario]`, `deps_type=AgentDependencies`, and `model_settings={'thinking': True}`.
* **Agent Tools:**
  * `gather_preferences` — extracts/registers `UserPreferences` and persists them to the global profile.
  * `find_cheapest_dates` / `search_flights` — structured flight tools (currency-aware). Currently return no data (provider being replaced); the agent falls back to `search_web`.
  * `search_web` — **primary live-price source**; delegates to the grounded research sub-agent (Gemini Google grounding).
  * `generate_scenarios` — presents 2-3 agent-built `Scenario` objects side-by-side; recomputes each `grand_total` from its parts, threads currency, flags `estimated`, and returns the render payload.
* **Research Sub-Agent:** [research_agent.py](file:///Users/aly/repos/kompass/backend/app/agent/research_agent.py) — an isolated PydanticAI agent using native `WebSearch` (Gemini Google Search grounding), kept separate because Gemini won't reliably combine grounding with function tools + structured output in one call.
* **System Prompt:** [system_prompt.md](file:///Users/aly/repos/kompass/backend/app/agent/prompts/system_prompt.md) — dynamic; injects the current **date** only (day-level granularity to keep the KV-cache prefix stable). Includes directives for seasonality, multi-modal routing, stress scoring, preference gathering, and scenario comparison.
* **Dependency Injection:** [dependency.py](file:///Users/aly/repos/kompass/backend/app/agent/dependency.py) — `AgentDependencies` dataclass enclosing `prompt_service`, `user_preferences`, `trip_repository`, `profile_repository`, `flight_service`, and `trip_id`.

---

## 4. Web Service Interface
* **FastAPI Entrypoint:** [main.py](file:///Users/aly/repos/kompass/backend/app/main.py) — configures CORS (any localhost origin) and a `lifespan` that runs `init_db()` and starts/stops the flights MCP client (non-fatal if MCP startup fails, since tools degrade gracefully).
* **Endpoints** ([routes.py](file:///Users/aly/repos/kompass/backend/app/api/routes.py)):
  * `GET /health` — health check.
  * `POST /api/copilotkit` — reconstructs effective `UserPreferences` (global profile baseline merged with conversation history), upserts the trip for the thread, dispatches the PydanticAI run to the AG-UI stream, and persists messages on completion.
  * `GET/POST /api/trips`, `GET/DELETE /api/trips/{id}` — trip session management.
  * `POST /api/saved-scenarios`, `GET /api/saved-scenarios?trip_id=`, `GET/DELETE /api/saved-scenarios/{id}` — saved scenarios (the "Save this trip" action in the scenario-detail popup).
  * `GET/PUT /api/profile` — global user profile (preferences).

---

## 5. Frontend Layer
* **Structure:** Next.js (App Router) application in `frontend/`. [page.js](file:///Users/aly/repos/kompass/frontend/app/page.js) composes [app-header.js](file:///Users/aly/repos/kompass/frontend/app/components/app-header.js), [trip-sidebar.js](file:///Users/aly/repos/kompass/frontend/app/components/trip-sidebar.js), and the CopilotKit `CopilotChat`.
* **State Hooks:** [use-active-trip.js](file:///Users/aly/repos/kompass/frontend/app/hooks/use-active-trip.js) (thread id sync, new/resume trip) and [use-trip-tools.js](file:///Users/aly/repos/kompass/frontend/app/hooks/use-trip-tools.js) (registers the `useRenderTool` generative-UI renderers).
* **Generative-UI Tool Cards:** in `frontend/app/components/tool-cards/` — `preferences-card`, `cheapest-dates-card`, `flights-card`, and `scenario-comparison-card`. Shared helpers live in [lib/format.js](file:///Users/aly/repos/kompass/frontend/app/lib/format.js); REST calls in [lib/trips-api.js](file:///Users/aly/repos/kompass/frontend/app/lib/trips-api.js).
* **Implementation Status:** CopilotKit React SDK v2 chat with streamed reasoning/tool events, trip sidebar (resume/new), and four generative-UI tool renderers including the Phase 5 scenario comparison cards.
