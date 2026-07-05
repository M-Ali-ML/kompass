# Kompass App: System Architecture (Post-Building)

This document details the *implemented* system architecture of the Kompass travel planning application as of Phase 10.

---

## 1. Architectural Overview
The system consists of a Python FastAPI backend and a Next.js frontend, integrated using the AG-UI protocol and CopilotKit. The backend follows a hexagonal (ports & adapters) design. For **flights** it connects directly to the official **Kiwi.com MCP** (remote, streamable HTTP, no API key); for **accommodations** it runs a local **SerpApi** Google Hotels MCP server over stdio. It persists trips/preferences/saved scenarios in SQLite, and uses a grounded web-search sub-agent (Gemini Google grounding) for live research, accommodation/flight price fallback, and ground-transport (train/bus/ferry) routing. A third, fire-and-forget sub-agent paints a per-trip "vibe" background image once a destination is known. Agent runs are traced to Langfuse via OpenTelemetry. A separate **eval suite** (`backend/evals/`, see [evals.md](evals.md)) runs the real agent against deterministic fixtures to score behavior on every prompt/model change.

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
        |   Kiwi flights MCP + accommodations MCP)      |
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
  Prompt Svc  Flights      Accommodations  Research sub-agent  Repositories
  (file)      (Kiwi MCP,   MCP (stdio,     (Gemini grounding:  (trips/profile/
              remote)      SerpApi)        research, fallback,  saved scenarios)
                                           ground transport)
```

All agent runs are instrumented with OpenTelemetry and exported to **Langfuse** (no-op when keys are absent).

---

## 2. Backend Layer (Hexagonal Architecture)
The backend follows a **Hexagonal Architecture (Ports & Adapters)** pattern to separate the core business logic (agent & models) from infrastructure details (prompt loading, flight/accommodation data, persistence).

### A. Core Domain Models
Located in `backend/app/domain/`:
* [trip.py](../backend/app/domain/trip.py) — `TripRequest` model (destination, duration, month, budget, traveler count).
* [user_preferences.py](../backend/app/domain/user_preferences.py) — `UserPreferences` model (`home_city`/departure origin, direct flights only, preferred transit modes, hotel class, vibe tags, `currency`) plus a `merged_with()` layering helper.
* [itinerary.py](../backend/app/domain/itinerary.py) — `Itinerary` wrapping `Leg` (with `TransportMode` enum: flight/train/bus/ferry/car/other), `Accommodation` (with optional `booking_link`), and `DaySummary` (each day has a `day_number`, `title`, `description`, and a `schedule` of time-blocked `PlanItem`s with `period`/`activity`/`details`/`location`).
* [flights.py](../backend/app/domain/flights.py) — `FlightOption` (incl. `booking_link` deep link and a routing-label `airline`, since Kiwi exposes no carrier name) and `FlightDateOption` returned by the flight adapter.
* [accommodations.py](../backend/app/domain/accommodations.py) — `AccommodationOption` (name, property type, nightly + total rate, currency, rating, reviews, hotel class, amenities, link, coordinates, `estimated`) returned by the accommodations adapter.
* [scenario.py](../backend/app/domain/scenario.py) — `Scenario` model plus `CostBreakdown` (transportation / accommodation / grand_total) and `StressFactors` (layover count, overnight travel, tight connection, total travel hours). Adds `comparison_label`, `start_date`/`end_date`, and `highlights`.
* **ORM models** in `backend/app/domain/models/`: [trip.py](../backend/app/domain/models/trip.py) (`Trip` with a `message_history` JSON column, `Message`), [profile.py](../backend/app/domain/models/profile.py) (`UserProfile` singleton), [saved_scenario.py](../backend/app/domain/models/saved_scenario.py) (`SavedScenario`), and [trip_background.py](../backend/app/domain/models/trip_background.py) (`TripBackground` — one row per trip storing the generated "vibe" image bytes plus a `pending`/`ready`/`error` lifecycle status), all registered on the shared `Base.metadata`.

### B. Ports (Interfaces)
Located in `backend/app/ports/`:
* [prompt_service.py](../backend/app/ports/prompt_service.py) — `PromptServicePort` for loading prompt templates.
* [flight_service.py](../backend/app/ports/flight_service.py) — `FlightServicePort` for `search_flights` / `find_cheapest_dates`.
* [accommodation_service.py](../backend/app/ports/accommodation_service.py) — `AccommodationServicePort` for `search_accommodations`.
* [research_service.py](../backend/app/ports/research_service.py) — `ResearchServicePort` for grounded web research (`research(query) -> str`), extracted so the eval suite can swap in a deterministic fake.
* [trip_repository.py](../backend/app/ports/trip_repository.py) — `TripRepository` (list/get/create/upsert/replace_messages/save_message_history/delete).
* [user_profile_repository.py](../backend/app/ports/user_profile_repository.py) — `UserProfileRepository` (get/save preferences).
* [saved_scenario_repository.py](../backend/app/ports/saved_scenario_repository.py) — `SavedScenarioRepository` (save/list/get/delete).
* [trip_background_repository.py](../backend/app/ports/trip_background_repository.py) — `TripBackgroundRepository` (get/try_begin/save_ready/set_status/clear) — a small state machine so concurrent turns of the same trip don't race to generate duplicate images.

### C. Adapters (Implementations)
Located in `backend/app/adapters/`:
* [file_prompt_service.py](../backend/app/adapters/file_prompt_service.py) — `FilePromptService` loading prompt markdown.
* [mcp_flight_service.py](../backend/app/adapters/mcp_flight_service.py) — `KiwiMCPFlightServiceAdapter` connecting to the remote Kiwi.com MCP (`KIWI_MCP_URL`, default `https://mcp.kiwi.com/mcp`) over streamable HTTP and parsing Kiwi's `search-flight` results into `FlightOption` / `FlightDateOption`. `search_flights` is one call plus client-side `max_stops` / `preferred_time` filtering (Kiwi has no such server-side filters); `find_cheapest_dates` fires several ±3-day flex-window searches **concurrently** (`KIWI_DATE_SAMPLES` searches total, throttled to `KIWI_MAX_CONCURRENT_SEARCHES` in flight at once — opening all of them at once was a real trigger for connection failures) and keeps the cheapest fare per departure date. Each search uses a short-lived connection; a **transport/protocol failure** (dead connection, timeout, an `isError` result) raises `KiwiTransportError` rather than silently returning `[]`, so it's never confused with Kiwi genuinely finding zero itineraries — see the reliability contract below.
* [mcp_accommodation_service.py](../backend/app/adapters/mcp_accommodation_service.py) — `MCPAccommodationServiceAdapter` (same persistent stdio lifecycle as the flights adapter) parsing results into `AccommodationOption`.
* [grounded_research_service.py](../backend/app/adapters/grounded_research_service.py) — `GroundedResearchService` implementing `ResearchServicePort` over the [research_agent.py](../backend/app/agent/research_agent.py) sub-agent (Gemini Google Search grounding).
* [sqlite_trip_repository.py](../backend/app/adapters/sqlite_trip_repository.py), [sqlite_user_profile_repository.py](../backend/app/adapters/sqlite_user_profile_repository.py), [sqlite_saved_scenario_repository.py](../backend/app/adapters/sqlite_saved_scenario_repository.py), and [sqlite_trip_background_repository.py](../backend/app/adapters/sqlite_trip_background_repository.py) — SQLAlchemy async implementations of the repository ports.

### D. Persistence
* [db.py](../backend/app/db.py) — shared async SQLAlchemy engine + `SessionLocal` sessionmaker (aiosqlite), `Base`, and `init_db()` which bootstraps the schema via `create_all`. Repositories depend on the sessionmaker, not the engine.
* Tables:
  * `trips` — one row per conversation `thread_id`. Carries a `message_history` JSON column holding the **full AG-UI history** (user/assistant/tool turns incl. tool calls + results) so generative-UI cards rehydrate on reload.
  * `messages` — flattened plain-text turns (legacy/fallback), cascade-deleted with the trip.
  * `user_profiles` — singleton of global preferences.
  * `saved_scenarios` — user-bookmarked scenarios. Stores the full `Scenario` JSON plus denormalized, queryable columns (`destination`, `grand_total`, `stress_score`, dates, `currency`, labels) and an optional `trip_id` (SET NULL so saves outlive a deleted conversation).
  * `trip_backgrounds` — one row per trip (cascade-deleted with it), keyed by `trip_id`. Holds the generated image bytes + MIME type, the destination/scene prompt it was generated from, and a `pending`/`ready`/`error` `status` that doubles as a generation lock.

### E. Flight & Accommodation data sources
* **Flights — Kiwi.com MCP (remote):** the agent reaches Kiwi's official MCP `search-flight` tool directly through `KiwiMCPFlightServiceAdapter` (above). There is no local flights MCP server — Kiwi is already an MCP server, so the adapter is the only translation layer. No API key is required.
* [accommodations_server.py](../backend/app/mcp_servers/accommodations_server.py) — a standalone FastMCP stdio server exposing `search_accommodations`, backed by the **SerpApi Google Hotels API** (`SERPAPI_API_KEY`, exported from `app.config` so the subprocess inherits it). Returns nightly + total rates, ratings, amenities, and links (cheapest first, capped by `ACCOMMODATIONS_TOP_N`).
* [_dev.py](../backend/app/mcp_servers/_dev.py) — shared dev helpers for the accommodations server: `mock_mode()` (`MCP_MODE=mock` returns deterministic, clearly-flagged fake data with **no** network calls / no key — handy so dev doesn't burn the SerpApi quota) and `log_call()` (when `MCP_LOG_FILE` is set, every tool request/response is appended as a JSON line for inspection).
* **Reliability contract:** when a source errors or returns nothing (Kiwi unreachable, or SerpApi key missing/erroring), the tools return **no fabricated data** (flights: an empty option list; accommodations: `available: false`), and the agent falls back to `search_web`. We never invent prices. For flights specifically, the adapter distinguishes *why* the list is empty: a confirmed zero-itinerary response from Kiwi is just `{"options": []}`, while a transport/protocol failure (`KiwiTransportError`, raised by `mcp_flight_service.py`) is caught by the `search_flights`/`find_cheapest_dates` agent tools and surfaced as `{"options": [], "data_source_error": true}` — the agent's fallback behavior is identical either way, but the failure mode stays visible in logs/Langfuse traces instead of looking like a legitimate "no flights on this route" answer.

---

## 3. PydanticAI Agent Layer
The agent framework is managed via PydanticAI.

* **Agent Definition:** [agent.py](../backend/app/agent/agent.py) instantiates `kompass_agent` with `output_type=str` (plain text only — travel plans are always delivered through the `generate_scenarios` tool, so a second `Union[str, Scenario]` output path would just re-ship the Scenario JSON schema on every request for nothing), `deps_type=AgentDependencies`, `retries={'tools': 2, 'output': 2}` (extra output retries absorb Flash's occasional empty completion on a large final-synthesis context), and `model_settings={'temperature': 0.2, 'thinking': False}` (low temperature for reliable tool-calling; thinking disabled so Flash doesn't spend its whole budget "thinking" and return an empty completion). Model selected from `settings.llm_model` (default `google:gemini-2.5-flash`).
* **Agent Tools:**
  * `gather_preferences` — extracts/registers `UserPreferences` (layered via `merged_with`) and persists them to the global profile.
  * `find_cheapest_dates` / `search_flights` — **live structured flights** via the remote Kiwi.com MCP, currency-aware and honoring `direct_flights_only` (applied client-side). `find_cheapest_dates` samples a month with concurrent ±3-day flex searches. Fall back to `search_web` when no options are returned.
  * `search_accommodations` — **live structured Google Hotels** (SerpApi) via the accommodations MCP, currency-aware, supports `max_price` / `min_rating`. Falls back to `search_web` when `available: false`.
  * `search_web` — grounded research sub-agent (Gemini Google grounding); primary source for destination knowledge and the price fallback for flights/lodging.
  * `search_ground_transport` — grounded train/bus/ferry routing via the research sub-agent (operators, times, duration, frequency, fare range) used to build non-flight `Leg`s and onward hops after a flight.
  * `generate_scenarios` — presents 2-3 agent-built `Scenario` objects side-by-side; recomputes each `grand_total` from its parts, threads currency, flags `estimated`, and returns the render payload. **Validates input**: rejects (once, with a corrective message) a single scenario, and rejects (once, bounded by `day_validation_retries`) scenarios whose `itinerary.days` count is materially short of the trip span — enforcing a complete day-by-day plan. Supports **targeted refinement**: re-called once with the full set when the traveler refines one scenario (by `comparison_label`), others carried over unchanged.
  * `ask_clarifying_question` — a **frontend human-in-the-loop tool** (not backend code). Registered via CopilotKit `useHumanInTheLoop` in [use-trip-tools.js](../frontend/app/hooks/use-trip-tools.js); PydanticAI's AG-UI `_AGUIFrontendToolset` exposes it to the agent automatically and handles the deferred result, so the run pauses until the traveler answers and resumes with the chosen text.
  * `set_background_image` — fire-and-forget: only called when the traveler explicitly asks to change/refresh the trip's vibe background, kicking off `spawn_trip_background(..., force=True)` with the requested scene. Never called as part of normal planning (an image is generated automatically for every trip).
* **Research Sub-Agent:** [research_agent.py](../backend/app/agent/research_agent.py) — an isolated PydanticAI agent using native `WebSearch` (Gemini Google Search grounding), kept separate because Gemini won't reliably combine grounding with function tools + structured output in one call. Loads its own [research_prompt.md](../backend/app/agent/prompts/research_prompt.md). Wrapped behind `ResearchServicePort` by [grounded_research_service.py](../backend/app/adapters/grounded_research_service.py) so the eval suite can substitute a deterministic fake.
* **Background-Image Sub-Agent:** [image_agent.py](../backend/app/agent/image_agent.py) — a small, self-contained fire-and-forget module (never in the main agent's request path) mirroring the research sub-agent's pattern. Its `scene_agent` (a cheap PydanticAI agent, `settings.image_scene_model`) reads the conversation + vibe tags and emits a structured `BackgroundScene{destination, scene_prompt}`; once a destination is known, `_generate_image()` calls a Gemini image model (`settings.image_model`) directly via `google-genai`, downscales/compresses the result to WebP (Pillow), and stores it via `TripBackgroundRepository`. Guarded by an in-process `_in_flight` set plus the repository's `try_begin` lock so concurrent turns can't double-generate; disabled entirely with `BACKGROUND_IMAGE_ENABLED=false`.
* **System Prompt:** [system_prompt.md](../backend/app/agent/prompts/system_prompt.md) — dynamic; injects the current **date** only (day-level granularity to keep the KV-cache prefix stable). Includes directives for seasonality, multi-modal routing (sequence ground legs after flights with realistic transfer buffers), round-trip-by-default, stress scoring, preference gathering (via the interactive `ask_clarifying_question` tool), respecting explicit constraints / manual overrides (skip already-arranged pieces, zero their cost, plan only the rest), scenario comparison with targeted refinement, and a complete day-by-day plan.
* **Dependency Injection:** [dependency.py](../backend/app/agent/dependency.py) — `AgentDependencies` dataclass enclosing `prompt_service`, `user_preferences`, `trip_repository`, `profile_repository`, `flight_service`, `accommodation_service`, `research_service`, `trip_id`, `day_validation_retries`, and `party_size` (the largest `passengers`/`guests` count searched this run, used to backfill `Scenario.travelers` and default `search_accommodations`' `guests`).

---

## 4. Configuration & Observability
* **Configuration:** [config.py](../backend/app/config.py) — `pydantic-settings` `Settings` loaded from `backend/.env`. Secrets use `SecretStr` (auto-masked). Keys: `GOOGLE_API_KEY`, `LLM_MODEL`, `RESEARCH_MODEL` (research sub-agent), `EVAL_MODEL`/`EVAL_JUDGE_MODEL` (eval suite, see [evals.md](evals.md)), `IMAGE_MODEL`/`IMAGE_SCENE_MODEL`/`BACKGROUND_IMAGE_ENABLED` (trip vibe background), `KIWI_MCP_URL`, `SERPAPI_API_KEY`, `MCP_MODE` (live/mock), `MCP_LOG_FILE`, `LANGFUSE_*`, `DATABASE_URL`, `HOST`/`PORT`, `LOG_LEVEL`. Relevant values are exported to `os.environ` so MCP subprocesses and third-party SDKs (Gemini, Langfuse) pick them up.
* **Telemetry:** [telemetry.py](../backend/app/telemetry.py) — wires Langfuse v4 (OpenTelemetry) and calls `Agent.instrument_all()` so every PydanticAI agent run (main + research) exports spans. `stream_with_attributes` wraps the AG-UI streaming body so trace attributes (`session_id` = trip thread, tags) cover the lazily-executed run. No-op when Langfuse keys are absent.
* **Logging:** [logging_config.py](../backend/app/logging_config.py) — `configure_logging()` sets up consistent app logging at `LOG_LEVEL`.

---

## 5. Web Service Interface
* **FastAPI Entrypoint:** [main.py](../backend/app/main.py) — configures CORS (any localhost origin) and a `lifespan` that initializes telemetry, runs `init_db()`, and starts/stops the flights (Kiwi MCP reachability probe) and accommodations MCP clients (non-fatal if startup fails, since tools degrade gracefully), flushing telemetry on shutdown.
* **Endpoints** ([routes.py](../backend/app/api/routes.py)):
  * `GET /health` — health check.
  * `POST /api/copilotkit` — reconstructs effective `UserPreferences` (global profile baseline merged with conversation history), upserts the trip for the thread, kicks off the fire-and-forget trip background-image job (once, per thread), dispatches the PydanticAI run to the AG-UI stream (wrapped with Langfuse trace attributes), and persists messages on completion.
  * `GET/POST /api/trips`, `GET/DELETE /api/trips/{id}` — trip session management. `GET` returns both plain-text `messages` and the full `message_history`.
  * `PUT /api/trips/{id}/messages` — persists the full AG-UI message history for a trip (called by the client after each run so generative-UI cards survive a reload).
  * `GET /api/trips/{id}/background.img` — serves the trip's generated vibe image (404 until ready/if generation failed); the frontend loads it directly in an `<img>` and hides on error.
  * `POST /api/saved-scenarios`, `GET /api/saved-scenarios?trip_id=`, `GET/DELETE /api/saved-scenarios/{id}` — saved scenarios (the "Save this trip" action in the scenario-detail popup).
  * `GET/PUT /api/profile` — global user profile (preferences).

---

## 6. Frontend Layer
* **Structure:** Next.js (App Router) application in `frontend/`. [page.js](../frontend/app/page.js) composes [app-header.js](../frontend/app/components/app-header.js), [trip-sidebar.js](../frontend/app/components/trip-sidebar.js), the CopilotKit `CopilotChat`, and the right-hand map split-panel ([map/trip-panel.js](../frontend/app/components/map/trip-panel.js)), all wrapped in the `MapStateProvider`. The CopilotKit provider + agent endpoint are configured in [copilotkit-provider.js](../frontend/app/copilotkit-provider.js) and [lib/config.js](../frontend/app/lib/config.js).
* **Responsive Layout (Phase 10):** desktop (`lg`+) keeps the 3-pane split; below `lg` the chat is full-width and the trip sidebar becomes an off-canvas drawer toggled by a header hamburger ([app-header.js](../frontend/app/components/app-header.js), now a client component with `showMenu`/`onMenuClick`). The settings and scenario-detail modals render as mobile bottom-sheets.
* **State Hooks:** [use-active-trip.js](../frontend/app/hooks/use-active-trip.js) (thread id sync, new/resume trip, message-history rehydration) and [use-trip-tools.js](../frontend/app/hooks/use-trip-tools.js) (registers the `useRenderTool` generative-UI renderers plus the `useHumanInTheLoop` `ask_clarifying_question` tool).
* **Sidebar:** [trip-sidebar.js](../frontend/app/components/trip-sidebar.js) has two tabs — **Trips** (resume/new/delete) and **Saved** ([saved-list.js](../frontend/app/components/saved-list.js), the bookmarked scenarios, opening the shared scenario detail modal).
* **Global Settings (Phase 10):** a gear button in [app-header.js](../frontend/app/components/app-header.js) opens [settings-modal.js](../frontend/app/components/settings-modal.js) — a portal modal that edits the global `UserPreferences` (home city, direct-flights toggle, transit-mode chips, hotel-class select, vibe-tag input, currency) via `GET/PUT /api/profile` in [lib/trips-api.js](../frontend/app/lib/trips-api.js).
* **Generative-UI Tool Cards:** in `frontend/app/components/tool-cards/` — `preferences-card`, `clarify-card` (the human-in-the-loop `ask_clarifying_question` card), `cheapest-dates-card`, `flights-card`, `accommodations-card`, `research-card`, `ground-transport-card`, and `scenario-comparison-card`. Loading states render an animated [search-progress.js](../frontend/app/components/search-progress.js) pill (Phase 9). Between tool calls, [chat-status.js](../frontend/app/components/chat-status.js) replaces CopilotKit's default loading dot (the chat's `messageView.cursor` slot) with a tool-specific status label driven by the AG-UI run lifecycle. Shared helpers live in [lib/format.js](../frontend/app/lib/format.js); REST calls in [lib/trips-api.js](../frontend/app/lib/trips-api.js).
* **Scenario Detail Modal:** `ScenarioComparisonCard` renders 2-3 cards with a "View details" action opening `ScenarioDetailModal` — a full popup with price, stress gauge, cost breakdown, stress factors, a per-direction travel timeline (with layover/overnight/tight-connection chips and Google Flights / booking links), accommodation list, an **expandable day-by-day itinerary**, reasoning, a "Save this trip" action, and a "View on map" action.
* **Trip Vibe Background:** [trip-backdrop.js](../frontend/app/components/trip-backdrop.js) — a reusable `<img>` pointed at `GET /api/trips/{id}/background.img` that starts hidden and only fades in on a successful load (stays hidden on a 404, e.g. not generated yet), so it's self-healing with no polling. Used behind the trip-sidebar row text ([trip-sidebar.js](../frontend/app/components/trip-sidebar.js), fading left-to-right) and behind the scenario-detail modal header ([scenario-detail-modal.js](../frontend/app/components/tool-cards/scenario-detail-modal.js), fading top-to-bottom).
* **Interactive Map (Phase 8):** a persistent split-panel ([map/trip-panel.js](../frontend/app/components/map/trip-panel.js)) shows an itinerary summary above an interactive Google Map ([map/trip-map.js](../frontend/app/components/map/trip-map.js), built on `@vis.gl/react-google-maps`). It plots numbered transit stops + accommodation markers and mode-colored polylines (geodesic for flights), auto-fitting bounds. Endpoint coordinates are geocoded client-side ([lib/geocode.js](../frontend/app/lib/geocode.js): Google Geocoder, `localStorage`-cached, IATA→airport disambiguation). The active route flows through a shared `MapState` store ([map/map-context.js](../frontend/app/components/map/map-context.js)) fed by the scenario cards (auto-select best-value + per-card "View on map"). Per-mode glyphs/colors are shared via [lib/transport.js](../frontend/app/lib/transport.js). Requires `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` (browser key); degrades to a placeholder when unset.
* **Implementation Status:** CopilotKit React SDK v2 chat with streamed reasoning/tool events (styled reasoning bubble, animated search-progress, error cards + run-failure toast — Phase 9), a two-tab trip/saved sidebar, eight generative-UI tool renderers plus a human-in-the-loop clarifying-question tool, a global-profile settings modal, a full scenario detail modal, an interactive Google Map split-panel, and a responsive mobile pass (Phase 10). Leaflet/react-leaflet remain installed as an optional no-key map fallback.
* **Testing (Phase 10):** backend `pytest` (domain, DI, persistence, agent, and REST routes via `TestClient` + `app.dependency_overrides` against an isolated SQLite DB); frontend **Vitest** unit tests ([tests/unit/](../frontend/tests/unit)) and **Playwright** e2e specs ([tests/e2e/](../frontend/tests/e2e): api, persistence, saved-scenarios, settings). These test *code*; a separate **agent-behavior eval suite** (`backend/evals/`, see [evals.md](evals.md)) tests the real LLM's behavior against a golden dataset.
