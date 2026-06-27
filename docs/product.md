# Kompass App: Product & Feature Status (Post-Building)

This document tracks the actual implementation status of product features outlined in the PRD as of Phase 10.

---

## 1. Feature Status Summary
The application has completed **Phases 1–10**: a multi-turn conversational travel agent (Phase 1–2) with SQLite persistence and a global user profile (Phase 3), live flight data via a flights MCP server plus a grounded web-search sub-agent (Phase 4), side-by-side scenario comparison with stress scoring and a full scenario detail modal incl. day-by-day plans (Phase 5), live accommodation data via an accommodations MCP server (Phase 6), multi-modal ground transport (train/bus/ferry) via grounded research with realistic connection sequencing (Phase 7), and an interactive Google Map split-panel that visualizes the active scenario's route with mode-colored legs and stop/stay markers (Phase 8). Phase 9 added streaming UX polish (animated search-progress pills, a styled reasoning bubble, candy skeletons, and graceful error cards/toasts). Phase 10 closed the "last 20%": an editable global-profile settings modal, an interactive human-in-the-loop clarifying-question card, prompt-driven manual overrides and targeted scenario refinement, a full responsive (mobile bottom-sheet / off-canvas drawer) pass, and an automated test suite (pytest, Vitest, Playwright). Agent runs are traced to Langfuse.

---

## 2. Feature Implementation Tracker

### A. Smart Date, Budget & Accommodation Optimization
* **Seasonality Awareness:** 🟢 Implemented (System prompt instructs seasonality reasoning; the agent injects the current date and can verify peaks via `search_web`).
* **Date Recommendations:** 🟢 Implemented (`find_cheapest_dates` tool + grounded `search_web` surface cheap date windows, rendered in the cheapest-dates card).
* **Live Price Integration:** 🟢 Implemented. Structured flight prices/dates come from the **SerpApi Google Flights** provider (flights MCP) and lodging from the **SerpApi Google Hotels** provider (accommodations MCP); the Gemini-grounded `search_web` sub-agent covers destination research and acts as the price fallback. Requires `SERPAPI_API_KEY`; degrades to `search_web` when absent (or runs deterministic mock data when `MCP_MODE=mock`).
* **Comprehensive Cost Tracking:** 🟢 Implemented (Domain `CostBreakdown` provides transportation/accommodation subtotals and a grand total; the scenario tool recomputes totals from parts; accommodation costs now come from live `search_accommodations` total rates).
* **Hotel Availability Checking:** 🟢 Implemented (Phase 6: `search_accommodations` returns live hotels/rentals with nightly + total rates, ratings, amenities, and booking links for the stay dates; `min_rating`/`max_price` honor quality/budget constraints).

### B. Intelligent Transportation Logistics
* **Multi-Modal Transport:** 🟢 Implemented (Phase 7: `TransportMode` enum + `Leg` model support flight/train/bus/ferry/car; `search_ground_transport` provides grounded train/bus/ferry routing for non-flight legs).
* **Convenience Filtering:** 🟢 Implemented (`direct_flights_only` and preferred transit modes are gathered and honored by the flight tools).
* **Detailed Route Sequencing:** 🟢 Implemented (Phase 7: system prompt sequences ground legs after flights, aligns onward `departure_time` to the prior `arrival_time` plus a realistic transfer buffer, and flags tight/overnight connections).
* **User Preference Gathering:** 🟢 Implemented (Agent gathers preferences via the interactive `ask_clarifying_question` human-in-the-loop card — one focused question with concrete options + free-text "Other" — then calls `gather_preferences`. Baseline preferences are also editable up front in the global settings modal).
* **Transit Synchronization:** 🟢 Implemented (Phase 7: connection-buffer alignment in the system prompt; tight/overnight connections surfaced in stress factors and timeline chips).

### C. Scenario Comparison & Scoring
* **Side-by-Side Scenario Generation:** 🟢 Implemented (Phase 5: `generate_scenarios` tool + `scenario-comparison-card.js` render 2-3 cards side-by-side with best-value / lowest-stress badges; input validation enforces 2-3 scenarios and a complete day-by-day plan).
* **Qualitative "Stress" Scoring:** 🟢 Implemented (1–5 `stress_score` backed by structured `StressFactors`, displayed as a 5-pip gauge with a label and highlight chips).

### D. Activity & Destination Discovery
* **Vibe-Based Recommendations:** 🟢 Implemented (Agent gathers vibe tags through clarifying questions).
* **Manual Overrides:** 🟢 Implemented (Phase 10: system-prompt directive 9 "Respecting Explicit Constraints" — when the traveler has already arranged a piece ("I already have flights"), the agent skips that data tool, zeroes its cost, plans only the rest, and honors scope-limiting + hard constraints).
* **Iterative Refinement:** 🟢 Implemented (Phase 10: the Scenario Comparison directive supports targeted refinement — refine one scenario by its `comparison_label` and re-call `generate_scenarios` once with the full set, others carried over unchanged).

### E. User Interface & Output Formats
* **Visual & Textual Summaries:** 🟢 Implemented (CopilotKit v2 conversational text + generative-UI cards for preferences, clarifying questions, flights, dates, accommodations, research, ground transport, and scenario comparison).
* **Detailed Views / Tables:** 🟢 Implemented (Phase 5: the scenario detail modal shows cost breakdown, stress factors, a per-direction travel timeline, accommodation list, and an expandable **day-by-day itinerary** with time-blocked schedules; Phase 10 adds a day count + Expand all/Collapse all control).
* **Interactive Clarifying Questions:** 🟢 Implemented (Phase 10: `ask_clarifying_question` is a frontend human-in-the-loop tool — the agent pauses the run on a card offering concrete option buttons plus an always-present "Other" free-text field, then resumes with the chosen answer; the answer rehydrates on resume).
* **Streaming UX Polish:** 🟢 Implemented (Phase 9: animated candy search-progress pills inside loading tool cards, a styled collapsible reasoning bubble from streamed `REASONING_*` events, shimmer scenario skeletons, and rose-tinted error cards + a dismissible run-failure toast).
* **Responsive Design:** 🟢 Implemented (Phase 10: desktop keeps the 3-pane split; below `lg` the chat is full-width, the trip sidebar becomes an off-canvas drawer via a header hamburger, and both the settings and scenario-detail modals become mobile bottom-sheets).

### F. Session Management & Memory
* **Iterative Workflow:** 🟢 Implemented (Agent runs each turn and appends to persisted history).
* **Trip-Specific Memory:** 🟢 Implemented (Phase 3: SQLite `Trip`/`Message` persistence; full AG-UI `message_history` is persisted so generative-UI cards rehydrate on resume; trips listed/resumed via the sidebar and REST endpoints).
* **Global User Profile:** 🟢 Implemented (Phase 3: singleton `UserProfile` persists preferences across trips, loaded as the baseline each run; Phase 10 adds an editable settings modal — gear button in the header — to view/edit home city, direct-flights toggle, transit modes, hotel class, vibe tags, and currency via `GET/PUT /api/profile`).
* **Saved Scenarios:** 🟢 Implemented (the "Save this trip" action persists a bookmarked scenario; the sidebar **Saved** tab lists and reopens them).

### G. Observability
* **Agent Tracing:** 🟢 Implemented (Langfuse v4 / OpenTelemetry traces every PydanticAI run — LLM requests, tool calls, inputs/outputs — grouped per trip thread via `session_id`; no-op when keys are absent).

### H. Quality & Testing
* **Automated Tests:** 🟢 Implemented (Phase 10: backend `pytest` covers domain, DI, persistence, agent, and REST routes — `/health`, `/api/profile`, `/api/trips`, `/api/saved-scenarios` — against an isolated SQLite DB via `app.dependency_overrides`; frontend **Vitest** unit tests cover the `lib/itinerary.js` helpers; **Playwright** e2e specs cover API, persistence, saved scenarios, and settings flows).
