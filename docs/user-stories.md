# Kompass App: User Stories (Post-Building)

This document tracks the actual implementation status of user stories defined in the product specification as of Phase 7.

---

## 1. User Story Implementation Matrix

### A. Smart Date, Budget & Accommodation Optimization
* **User Story 1 (Seasonality):** As a flexible traveler, I want the app to identify the main, shoulder, and off-seasons for my destination, so that I can find dates that are less crowded and more budget-friendly.
  * **Status:** `[x]` Completed
  * *Notes:* The system prompt drives seasonality reasoning and the agent verifies crowd/weather peaks via the grounded `search_web` tool, surfacing them as scenario highlights (e.g. "Peak crowd"). No dedicated season-classification tool, but the behavior is functional end-to-end.
* **User Story 2 (Flight Date Recommendation):** As a budget-conscious traveler, I want to provide a broad timeframe (e.g., 10 to 15 days in September) and have the app recommend the exact best dates to fly based on live prices from Skyscanner or Google Flights.
  * **Status:** `[x]` Completed
  * *Notes:* `find_cheapest_dates` (flights MCP via **SerpApi Google Flights**) plus the grounded `search_web` fallback surface cheap date windows, rendered in [cheapest-dates-card.js](file:///Users/aly/repos/kompass/frontend/app/components/tool-cards/cheapest-dates-card.js).
* **User Story 3 (Comprehensive Budgeting):** As a thorough planner, I want the app to estimate and include accommodation costs alongside transportation costs, so that I can see accurate subtotals and a grand total for my entire trip.
  * **Status:** `[x]` Completed
  * *Notes:* `CostBreakdown` in [scenario.py](file:///Users/aly/repos/kompass/backend/app/domain/scenario.py) renders transportation/accommodation subtotals + grand total in the scenario cards. Both are now live: transportation from SerpApi Google Flights / ground-transport research, accommodation from live `search_accommodations` total rates (Phase 6).
* **User Story 4 (Hotel Availability):** As a traveler with specific tastes, I want the app to check the availability of my favorite or preferred hotels for different date windows, so that I don't book flights for dates when my ideal accommodation is sold out.
  * **Status:** `[x]` Completed
  * *Notes:* Phase 6 — `search_accommodations` (accommodations MCP via **SerpApi Google Hotels**) returns live hotels/rentals with nightly + total rates, ratings, amenities, and booking links for given stay dates. `min_rating`/`max_price` honor stated tastes/budget; results render in [accommodations-card.js](file:///Users/aly/repos/kompass/frontend/app/components/tool-cards/accommodations-card.js) and feed the scenario's accommodation cost.

---

### B. Intelligent Transportation Logistics
* **User Story 5 (Travel Parameters/Filtering):** As a traveler who values convenience, I want to set parameters for my travel (e.g., direct flights only, acceptable journey length, morning/night flights), so that I avoid inconvenient routes like flights with three layovers.
  * **Status:** `[x]` Completed
  * *Notes:* Extracted from conversation via the `gather_preferences` tool in [agent.py](file:///Users/aly/repos/kompass/backend/app/agent/agent.py) and stored in dependencies.
* **User Story 6 (Route Syncing & Detail):** As a trip planner, I want the app to automatically synchronize my connecting travel modes and provide specific routing notes (e.g., "Fly to Athens and take the first ferry out to Milos"), so that I have a foolproof logistical plan immediately after landing.
  * **Status:** `[x]` Completed
  * *Notes:* Phase 7 — `search_ground_transport` provides grounded train/bus/ferry routing (operators, times, duration, fare range) for the onward hop after a flight. The system prompt sequences ground legs after flights and aligns each onward `Leg.departure_time` to the prior `arrival_time` plus a realistic transfer buffer; tight/overnight connections surface in the scenario detail timeline.

---

### C. Scenario Comparison & Scoring
* **User Story 7 (Comparative Layout):** As an analytical planner, I want to view multiple travel scenarios side-by-side in a comparative table, so that I can easily weigh the differences in cost, travel flow, and duration.
  * **Status:** `[x]` Completed
  * *Notes:* Phase 5 — the `generate_scenarios` tool in [agent.py](file:///Users/aly/repos/kompass/backend/app/agent/agent.py) returns 2-3 `Scenario` objects rendered side-by-side by [scenario-comparison-card.js](file:///Users/aly/repos/kompass/frontend/app/components/tool-cards/scenario-comparison-card.js), with cost breakdown, stress gauge, and best-value / lowest-stress badges.
* **User Story 8 (Stress Scoring):** As a traveler who balances budget with comfort, I want the app to calculate an "overall stress level" or convenience score for each itinerary, taking into account flight times and difficult connections (like overnight ferries), so that I can make a holistic decision.
  * **Status:** `[x]` Completed
  * *Notes:* Structured itinerary models in [scenario.py](file:///Users/aly/repos/kompass/backend/app/domain/scenario.py) support `stress_score` (1-5), and system prompt instructs the agent on scoring heuristics.

---

### D. Activity & Destination Discovery
* **User Story 9 (Vibe questionnaire):** As an explorer unfamiliar with a new location, I want the app to ask me questions to determine the "vibe" I am looking for, so that it can provide tailored recommendations.
  * **Status:** `[x]` Completed
  * *Notes:* Implemented in system prompt instructions: the agent asks clarifying questions one by one and gathers vibe tags.
* **User Story 10 (Manual Overrides):** As an independent traveler, I want the ability to manually override activity suggestions or tell the app exactly what I plan to do, so that it focuses on logistical heavy-lifting rather than spoon-feeding me day-to-day sightseeing.
  * **Status:** `[x]` Completed
  * *Notes:* Controlled via conversational dialogue and custom constraint prompts in [system_prompt.md](file:///Users/aly/repos/kompass/backend/app/agent/prompts/system_prompt.md).

---

### E. User Interface & Output Formats
* **User Story 11 (Visual Summary):** As a user reviewing my trip, I want to see a high-level visual summary of the itinerary, so that I can quickly grasp the overall flow of my travel.
  * **Status:** `[x]` Completed
  * *Notes:* Scenario comparison cards provide an at-a-glance visual summary (price, stress, leg overview), and the scenario detail modal adds a per-direction travel timeline and expandable day-by-day plan. Phase 8 adds an interactive Google Map split-panel ([trip-panel.js](file:///Users/aly/repos/kompass/frontend/app/components/map/trip-panel.js) / [trip-map.js](file:///Users/aly/repos/kompass/frontend/app/components/map/trip-map.js)) that plots the active scenario's route with mode-colored legs and stop/stay markers, auto-fitting the viewport.
* **User Story 12 (Tabular Breakdowns):** As a detail-oriented planner, I want the option to view detailed text and tabular breakdowns of my itinerary, so that I can thoroughly understand the specific logistical details.
  * **Status:** `[x]` Completed
  * *Notes:* The "View details" scenario modal ([scenario-comparison-card.js](file:///Users/aly/repos/kompass/frontend/app/components/tool-cards/scenario-comparison-card.js)) shows a full breakdown: itemized costs, stress factors, a per-direction travel timeline (with layover/overnight/tight-connection chips and booking links), an accommodation list, and an expandable day-by-day itinerary with time-blocked schedules.

---

### F. Session Management & Memory
* **User Story 13 (Iterative Feedback):** As an iterative planner, I want to be able to provide feedback on the generated itinerary and have the app regenerate the response, so that I am not forced to rely on a single, perfect initial output.
  * **Status:** `[x]` Completed
  * *Notes:* Supported natively by CopilotKit stream loop in [routes.py](file:///Users/aly/repos/kompass/backend/app/api/routes.py).
* **User Story 14 (Session Persistence):** As a busy user, I want the app to save my specific trip conversations, so that I can leave the app and return another day to pick up exactly where I left off.
  * **Status:** `[x]` Completed
  * *Notes:* Phase 3 — `Trip`/`Message` persisted to SQLite via [sqlite_trip_repository.py](file:///Users/aly/repos/kompass/backend/app/adapters/sqlite_trip_repository.py); the full AG-UI `message_history` (incl. tool calls + results) is saved via `PUT /api/trips/{id}/messages` so generative-UI cards rehydrate on resume. Trips listed and resumed from the [trip-sidebar.js](file:///Users/aly/repos/kompass/frontend/app/components/trip-sidebar.js) via the `/api/trips` endpoints.
* **User Story 15 (Global Profile Persistence):** As a frequent user, I want the app to remember my baseline likes and dislikes globally, so that when I start a new trip conversation, it automatically applies my previous preferences.
  * **Status:** `[x]` Completed
  * *Notes:* Phase 3 — a singleton `UserProfile` ([sqlite_user_profile_repository.py](file:///Users/aly/repos/kompass/backend/app/adapters/sqlite_user_profile_repository.py)) persists preferences; the run loads it as the baseline and merges conversation preferences on top via `UserPreferences.merged_with()`.

---

### G. Autonomy & Manual Labor Reduction
* **User Story 16 (Autonomous Draft Itinerary):** As a traveler overwhelmed by manual planning, I want the app to act with a high degree of autonomy (8-9 out of 10) to generate a complete draft itinerary from a high-level prompt, so that I am saved the manual labor of cross-referencing multiple booking sites.
  * **Status:** `[x]` Completed
  * *Notes:* Enabled by `kompass_agent` text generation capability in [agent.py](file:///Users/aly/repos/kompass/backend/app/agent/agent.py).
