# Kompass App: System Architecture (Post-Building)

This document details the *implemented* system architecture of the Kompass travel planning application as of Phase 7.

---

## 1. Architectural Overview
The system consists of a Python FastAPI backend and a Next.js frontend, integrated using the AG-UI protocol and CopilotKit. The backend follows a hexagonal (ports & adapters) design, talks to two data MCP servers over stdio (**flights** and **accommodations**, both backed by SerpApi), persists trips/preferences/saved scenarios in SQLite, and uses a grounded web-search sub-agent (Gemini Google grounding) for live research, accommodation/flight price fallback, and ground-transport (train/bus/ferry) routing. Agent runs are traced to Langfuse via OpenTelemetry.

```
        +-----------------------------------------------+
        |               Next.js Frontend                |
        |  CopilotKit v2 Chat + Generative-UI tool cards |
        |  (preferences, flights, dates, accommodations, |
        |   research, scenarios) + trip/saved sidebar     |
        |  Tailwind CSS v4 "Candy" theme                 |
        +-----------------------+-----------------------+
                                | SSE Streaming (AG-UI Protocol)
                                v
        +-----------------------+-----------------------+
        |                 FastAPI Web App               |
        |  main.py (lifespan: telemetry + init_db +     |
        |   flights MCP + accommodations MCP)           |
        |  api/routes.py (/api/copilotkit + REST)       |
        +----------+-----------------------+------------+
                   |                       |
                   v                       v
        +----------+---------+   +---------+-----------+
        |  PydanticAI Agent  |   |  SQLite Persistence |
        |  agent/agent.py    |   |  db.py + adapters   |
        +----------+---------+   +---------------------+
                   |
        +----------+-------+----------------+----------------+
        |          |       |                |                |
        v          v       v                v                v
  Prompt Svc  Flights MCP  Accommodations  Research sub-agent  Repositories
  (file)      (stdio,      MCP (stdio,     (Gemini grounding:  (trips/profile/
              SerpApi)     SerpApi)        research, fallback,  saved scenarios)
                                           ground transport)
```

All agent runs are instrumented with OpenTelemetry and exported to **Langfuse** (no-op when keys are absent).

---

## 2. Backend Layer (Hexagonal Architecture)
The backend follows a **Hexagonal Architecture (Ports & Adapters)** pattern to separate the core business logic (agent & models) from infrastructure details (prompt loading, flight/accommodation data, persistence).

### A. Core Domain Models
Located in `backend/app/domain/`:
* [trip.py](file:///Users/aly/repos/kompass/backend/app/domain/trip.py) — `TripRequest` model (destination, duration, month, budget, traveler count).
* [user_preferences.py](file:///Users/aly/repos/kompass/backend/app/domain/user_preferences.py) — `UserPreferences` model (direct flights only, preferred transit modes, hotel class, vibe tags, `currency`) plus a `merged_with()` layering helper.
* [itinerary.py](file:///Users/aly/repos/kompass/backend/app/domain/itinerary.py) — `Itinerary` wrapping `Leg` (with `TransportMode` enum: flight/train/bus/ferry/car/other), `Accommodation` (with optional `booking_link`), and `DaySummary` (each day has a `day_number`, `title`, `description`, and a `schedule` of time-blocked `PlanItem`s with `period`/`activity`/`details`/`location`).
* [flights.py](file:///Users/aly/repos/kompass/backend/app/domain/flights.py) — `FlightOption` and `FlightDateOption` returned by the flight adapter.
* [accommodations.py](file:///Users/aly/repos/kompass/backend/app/domain/accommodations.py) — `AccommodationOption` (name, property type, nightly + total rate, currency, rating, reviews, hotel class, amenities, link, coordinates, `estimated`) returned by the accommodations adapter.
* [scenario.py](file:///Users/aly/repos/kompass/backend/app/domain/scenario.py) — `Scenario` model plus `CostBreakdown` (transportation / accommodation / grand_total) and `StressFactors` (layover count, overnight travel, tight connection, total travel hours). Adds `comparison_label`, `start_date`/`end_date`, and `highlights`.
* **ORM models** in `backend/app/domain/models/`: [trip.py](file:///Users/aly/repos/kompass/backend/app/domain/models/trip.py) (`Trip` with a `message_history` JSON column, `Message`), [profile.py](file:///Users/aly/repos/kompass/backend/app/domain/models/profile.py) (`UserProfile` singleton), and [saved_scenario.py](file:///Users/aly/repos/kompass/backend/app/domain/models/saved_scenario.py) (`SavedScenario`), all registered on the shared `Base.metadata`.

### B. Ports (Interfaces)
Located in `backend/app/ports/`:
* [prompt_service.py](file:///Users/aly/repos/kompass/backend/app/ports/prompt_service.py) — `PromptServicePort` for loading prompt templates.
* [flight_service.py](file:///Users/aly/repos/kompass/backend/app/ports/flight_service.py) — `FlightServicePort` for `search_flights` / `find_cheapest_dates`.
* [accommodation_service.py](file:///Users/aly/repos/kompass/backend/app/ports/accommodation_service.py) — `AccommodationServicePort` for `search_accommodations`.
* [trip_repository.py](file:///Users/aly/repos/kompass/backend/app/ports/trip_repository.py) — `TripRepository` (list/get/create/upsert/replace_messages/save_message_history/delete).
* [user_profile_repository.py](file:///Users/aly/repos/kompass/backend/app/ports/user_profile_repository.py) — `UserProfileRepository` (get/save preferences).
* [saved_scenario_repository.py](file:///Users/aly/repos/kompass/backend/app/ports/saved_scenario_repository.py) — `SavedScenarioRepository` (save/list/get/delete).

### C. Adapters (Implementations)
Located in `backend/app/adapters/`:
* [file_prompt_service.py](file:///Users/aly/repos/kompass/backend/app/adapters/file_prompt_service.py) — `FilePromptService` loading prompt markdown.
* [mcp_flight_service.py](file:///Users/aly/repos/kompass/backend/app/adapters/mcp_flight_service.py) — `MCPFlightServiceAdapter` holding a persistent stdio MCP session and parsing results into `FlightOption` / `FlightDateOption`.
* [mcp_accommodation_service.py](file:///Users/aly/repos/kompass/backend/app/adapters/mcp_accommodation_service.py) — `MCPAccommodationServiceAdapter` (same persistent stdio lifecycle as the flights adapter) parsing results into `AccommodationOption`.
* [sqlite_trip_repository.py](file:///Users/aly/repos/kompass/backend/app/adapters/sqlite_trip_repository.py), [sqlite_user_profile_repository.py](file:///Users/aly/repos/kompass/backend/app/adapters/sqlite_user_profile_repository.py), and [sqlite_saved_scenario_repository.py](file:///Users/aly/repos/kompass/backend/app/adapters/sqlite_saved_scenario_repository.py) — SQLAlchemy async implementations of the repository ports.

### D. Persistence
* [db.py](file:///Users/aly/repos/kompass/backend/app/db.py) — shared async SQLAlchemy engine + `SessionLocal` sessionmaker (aiosqlite), `Base`, and `init_db()` which bootstraps the schema via `create_all`. Repositories depend on the sessionmaker, not the engine.
* Tables:
  * `trips` — one row per conversation `thread_id`. Carries a `message_history` JSON column holding the **full AG-UI history** (user/assistant/tool turns incl. tool calls + results) so generative-UI cards rehydrate on reload.
  * `messages` — flattened plain-text turns (legacy/fallback), cascade-deleted with the trip.
  * `user_profiles` — singleton of global preferences.
  * `saved_scenarios` — user-bookmarked scenarios. Stores the full `Scenario` JSON plus denormalized, queryable columns (`destination`, `grand_total`, `stress_score`, dates, `currency`, labels) and an optional `trip_id` (SET NULL so saves outlive a deleted conversation).

### E. MCP Servers
Located in `backend/app/mcp_servers/`:
* [flights_server.py](file:///Users/aly/repos/kompass/backend/app/mcp_servers/flights_server.py) — a standalone FastMCP stdio server exposing `search_flights` and `find_cheapest_dates`, backed by the **SerpApi Google Flights API** (key via `SERPAPI_API_KEY`, exported from `app.config` so the subprocess inherits it). `find_cheapest_dates` probes a bounded set of candidate dates (`FLIGHTS_DATE_SAMPLES`, default 4) since SerpApi has no future date-grid.
* [accommodations_server.py](file:///Users/aly/repos/kompass/backend/app/mcp_servers/accommodations_server.py) — a standalone FastMCP stdio server exposing `search_accommodations`, backed by the **SerpApi Google Hotels API** (reuses `SERPAPI_API_KEY`). Returns nightly + total rates, ratings, amenities, and links (cheapest first, capped by `ACCOMMODATIONS_TOP_N`).
* [_dev.py](file:///Users/aly/repos/kompass/backend/app/mcp_servers/_dev.py) — shared dev helpers: `mock_mode()` (`MCP_MODE=mock` returns deterministic, clearly-flagged fake data with **no** network calls / no key — handy so dev doesn't burn the shared SerpApi quota) and `log_call()` (when `MCP_LOG_FILE` is set, every tool request/response is appended as a JSON line for inspection).
* **Reliability contract:** when the key is missing or SerpApi errors/returns nothing, the tools return `available: false` with **no fabricated data**, and the agent falls back to `search_web`. We never invent prices.

---

## 3. PydanticAI Agent Layer
The agent framework is managed via PydanticAI.

* **Agent Definition:** [agent.py](file:///Users/aly/repos/kompass/backend/app/agent/agent.py) instantiates `kompass_agent` with `output_type=Union[str, Scenario]`, `deps_type=AgentDependencies`, and `model_settings={'thinking': True}`. Model selected from `settings.llm_model` (default `google:gemini-2.5-pro`).
* **Agent Tools:**
  * `gather_preferences` — extracts/registers `UserPreferences` (layered via `merged_with`) and persists them to the global profile.
  * `find_cheapest_dates` / `search_flights` — **live structured Google Flights** (SerpApi) via the flights MCP, currency-aware and honoring `direct_flights_only`. Fall back to `search_web` when `available: false`.
  * `search_accommodations` — **live structured Google Hotels** (SerpApi) via the accommodations MCP, currency-aware, supports `max_price` / `min_rating`. Falls back to `search_web` when `available: false`.
  * `search_web` — grounded research sub-agent (Gemini Google grounding); primary source for destination knowledge and the price fallback for flights/lodging.
  * `search_ground_transport` — grounded train/bus/ferry routing via the research sub-agent (operators, times, duration, frequency, fare range) used to build non-flight `Leg`s and onward hops after a flight.
  * `generate_scenarios` — presents 2-3 agent-built `Scenario` objects side-by-side; recomputes each `grand_total` from its parts, threads currency, flags `estimated`, and returns the render payload. **Validates input**: rejects (once, with a corrective message) a single scenario, and rejects (once, bounded by `day_validation_retries`) scenarios whose `itinerary.days` count is materially short of the trip span — enforcing a complete day-by-day plan.
* **Research Sub-Agent:** [research_agent.py](file:///Users/aly/repos/kompass/backend/app/agent/research_agent.py) — an isolated PydanticAI agent using native `WebSearch` (Gemini Google Search grounding), kept separate because Gemini won't reliably combine grounding with function tools + structured output in one call. Loads its own [research_prompt.md](file:///Users/aly/repos/kompass/backend/app/agent/prompts/research_prompt.md).
* **System Prompt:** [system_prompt.md](file:///Users/aly/repos/kompass/backend/app/agent/prompts/system_prompt.md) — dynamic; injects the current **date** only (day-level granularity to keep the KV-cache prefix stable). Includes directives for seasonality, multi-modal routing (sequence ground legs after flights with realistic transfer buffers), round-trip-by-default, stress scoring, preference gathering, scenario comparison, and a complete day-by-day plan.
* **Dependency Injection:** [dependency.py](file:///Users/aly/repos/kompass/backend/app/agent/dependency.py) — `AgentDependencies` dataclass enclosing `prompt_service`, `user_preferences`, `trip_repository`, `profile_repository`, `flight_service`, `accommodation_service`, `trip_id`, and `day_validation_retries`.

---

## 4. Configuration & Observability
* **Configuration:** [config.py](file:///Users/aly/repos/kompass/backend/app/config.py) — `pydantic-settings` `Settings` loaded from `backend/.env`. Secrets use `SecretStr` (auto-masked). Keys: `GOOGLE_API_KEY`, `LLM_MODEL`, `SERPAPI_API_KEY`, `MCP_MODE` (live/mock), `MCP_LOG_FILE`, `LANGFUSE_*`, `DATABASE_URL`, `HOST`/`PORT`, `LOG_LEVEL`. Relevant values are exported to `os.environ` so MCP subprocesses and third-party SDKs (Gemini, Langfuse) pick them up.
* **Telemetry:** [telemetry.py](file:///Users/aly/repos/kompass/backend/app/telemetry.py) — wires Langfuse v4 (OpenTelemetry) and calls `Agent.instrument_all()` so every PydanticAI agent run (main + research) exports spans. `stream_with_attributes` wraps the AG-UI streaming body so trace attributes (`session_id` = trip thread, tags) cover the lazily-executed run. No-op when Langfuse keys are absent.
* **Logging:** [logging_config.py](file:///Users/aly/repos/kompass/backend/app/logging_config.py) — `configure_logging()` sets up consistent app logging at `LOG_LEVEL`.

---

## 5. Web Service Interface
* **FastAPI Entrypoint:** [main.py](file:///Users/aly/repos/kompass/backend/app/main.py) — configures CORS (any localhost origin) and a `lifespan` that initializes telemetry, runs `init_db()`, and starts/stops both the flights and accommodations MCP clients (non-fatal if MCP startup fails, since tools degrade gracefully), flushing telemetry on shutdown.
* **Endpoints** ([routes.py](file:///Users/aly/repos/kompass/backend/app/api/routes.py)):
  * `GET /health` — health check.
  * `POST /api/copilotkit` — reconstructs effective `UserPreferences` (global profile baseline merged with conversation history), upserts the trip for the thread, dispatches the PydanticAI run to the AG-UI stream (wrapped with Langfuse trace attributes), and persists messages on completion.
  * `GET/POST /api/trips`, `GET/DELETE /api/trips/{id}` — trip session management. `GET` returns both plain-text `messages` and the full `message_history`.
  * `PUT /api/trips/{id}/messages` — persists the full AG-UI message history for a trip (called by the client after each run so generative-UI cards survive a reload).
  * `POST /api/saved-scenarios`, `GET /api/saved-scenarios?trip_id=`, `GET/DELETE /api/saved-scenarios/{id}` — saved scenarios (the "Save this trip" action in the scenario-detail popup).
  * `GET/PUT /api/profile` — global user profile (preferences).

---

## 6. Frontend Layer
* **Structure:** Next.js (App Router) application in `frontend/`. [page.js](file:///Users/aly/repos/kompass/frontend/app/page.js) composes [app-header.js](file:///Users/aly/repos/kompass/frontend/app/components/app-header.js), [trip-sidebar.js](file:///Users/aly/repos/kompass/frontend/app/components/trip-sidebar.js), and the CopilotKit `CopilotChat`. The CopilotKit provider + agent endpoint are configured in [copilotkit-provider.js](file:///Users/aly/repos/kompass/frontend/app/copilotkit-provider.js) and [lib/config.js](file:///Users/aly/repos/kompass/frontend/app/lib/config.js).
* **State Hooks:** [use-active-trip.js](file:///Users/aly/repos/kompass/frontend/app/hooks/use-active-trip.js) (thread id sync, new/resume trip, message-history rehydration) and [use-trip-tools.js](file:///Users/aly/repos/kompass/frontend/app/hooks/use-trip-tools.js) (registers the `useRenderTool` generative-UI renderers).
* **Sidebar:** [trip-sidebar.js](file:///Users/aly/repos/kompass/frontend/app/components/trip-sidebar.js) has two tabs — **Trips** (resume/new/delete) and **Saved** ([saved-list.js](file:///Users/aly/repos/kompass/frontend/app/components/saved-list.js), the bookmarked scenarios, opening the shared scenario detail modal).
* **Generative-UI Tool Cards:** in `frontend/app/components/tool-cards/` — `preferences-card`, `cheapest-dates-card`, `flights-card`, `accommodations-card`, `research-card`, and `scenario-comparison-card`. Shared helpers live in [lib/format.js](file:///Users/aly/repos/kompass/frontend/app/lib/format.js); REST calls in [lib/trips-api.js](file:///Users/aly/repos/kompass/frontend/app/lib/trips-api.js).
* **Scenario Detail Modal:** `ScenarioComparisonCard` renders 2-3 cards with a "View details" action opening `ScenarioDetailModal` — a full popup with price, stress gauge, cost breakdown, stress factors, a per-direction travel timeline (with layover/overnight/tight-connection chips and Google Flights / booking links), accommodation list, an **expandable day-by-day itinerary**, reasoning, and a "Save this trip" action.
* **Implementation Status:** CopilotKit React SDK v2 chat with streamed reasoning/tool events, a two-tab trip/saved sidebar, six generative-UI tool renderers, and a full scenario detail modal. Leaflet/react-leaflet are installed for a future map view (not yet implemented).
