# Kompass App: User Stories (Post-Building)

This document tracks the implementation status of user stories defined in the product specification.

---

## 1. User Story Implementation Matrix

### A. Smart Date, Budget & Accommodation Optimization
* **User Story 1 (Seasonality):** As a flexible traveler, I want the app to identify the main, shoulder, and off-seasons for my destination, so that I can find dates that are less crowded and more budget-friendly.
  * **Status:** `[ ]` Not Started
* **User Story 2 (Flight Date Recommendation):** As a budget-conscious traveler, I want to provide a broad timeframe (e.g., 10 to 15 days in September) and have the app recommend the exact best dates to fly based on live prices from Skyscanner or Google Flights.
  * **Status:** `[ ]` Not Started
* **User Story 3 (Comprehensive Budgeting):** As a thorough planner, I want the app to estimate and include accommodation costs alongside transportation costs, so that I can see accurate subtotals and a grand total for my entire trip.
  * **Status:** `[x]` Completed
  * *Notes:* Schema models [models.py](file:///Users/aly/repos/kompass/backend/app/domain/models.py) explicitly contain `transportation_subtotal_usd`, `accommodation_subtotal_usd`, and `grand_total_usd`.
* **User Story 4 (Hotel Availability):** As a traveler with specific tastes, I want the app to check the availability of my favorite or preferred hotels for different date windows, so that I don't book flights for dates when my ideal accommodation is sold out.
  * **Status:** `[x]` Completed
  * *Notes:* Mock stay service `AirbnbStayService` in [openbnb_stays.py](file:///Users/aly/repos/kompass/backend/app/adapters/openbnb_stays.py) searches stays, mapped to agent tool `check_stays`.

---

### B. Intelligent Transportation Logistics
* **User Story 5 (Travel Parameters/Filtering):** As a traveler who values convenience, I want to set parameters for my travel (e.g., direct flights only, acceptable journey length, morning/night flights), so that I avoid inconvenient routes like flights with three layovers.
  * **Status:** `[ ]` Not Started
* **User Story 6 (Route Syncing & Detail):** As a trip planner, I want the app to automatically synchronize my connecting travel modes and provide specific routing notes (e.g., "Fly to Athens and take the first ferry out to Milos"), so that I have a foolproof logistical plan immediately after landing.
  * **Status:** `[ ]` Not Started

---

### C. Scenario Comparison & Scoring
* **User Story 7 (Comparative Layout):** As an analytical planner, I want to view multiple travel scenarios side-by-side in a comparative table, so that I can easily weigh the differences in cost, travel flow, and duration.
  * **Status:** `[ ]` Not Started (Backend models support it, but UI implementation is pending)
* **User Story 8 (Stress Scoring):** As a traveler who balances budget with comfort, I want the app to calculate an "overall stress level" or convenience score for each itinerary, taking into account flight times and difficult connections (like overnight ferries), so that I can make a holistic decision.
  * **Status:** `[x]` Completed
  * *Notes:* Schema models [models.py](file:///Users/aly/repos/kompass/backend/app/domain/models.py) contain `stress_score` field validated from 1 to 5.

---

### D. Activity & Destination Discovery
* **User Story 9 (Vibe questionnaire):** As an explorer unfamiliar with a new location, I want the app to ask me questions to determine the "vibe" I am looking for, so that it can provide tailored recommendations.
  * **Status:** `[ ]` Not Started
* **User Story 10 (Manual Overrides):** As an independent traveler, I want the ability to manually override activity suggestions or tell the app exactly what I plan to do, so that it focuses on logistical heavy-lifting rather than spoon-feeding me day-to-day sightseeing.
  * **Status:** `[x]` Completed
  * *Notes:* Agent system prompt handles custom prompt constraints.

---

### E. User Interface & Output Formats
* **User Story 11 (Visual Summary):** As a user reviewing my trip, I want to see a high-level visual summary of the itinerary, so that I can quickly grasp the overall flow of my travel.
  * **Status:** `[ ]` Not Started
* **User Story 12 (Tabular Breakdowns):** As a detail-oriented planner, I want the option to view detailed text and tabular breakdowns of my itinerary, so that I can thoroughly understand the specific logistical details.
  * **Status:** `[ ]` Not Started

---

### F. Session Management & Memory
* **User Story 13 (Iterative Feedback):** As an iterative planner, I want to be able to provide feedback on the generated itinerary and have the app regenerate the response, so that I am not forced to rely on a single, perfect initial output.
  * **Status:** `[x]` Completed
  * *Notes:* FastAPI endpoint [main.py](file:///Users/aly/repos/kompass/backend/app/main.py) accepts ongoing chat messages.
* **User Story 14 (Session Persistence):** As a busy user, I want the app to save my specific trip conversations, so that I can leave the app and return another day to pick up exactly where I left off.
  * **Status:** `[x]` Completed
  * *Notes:* Implemented via `SQLiteTripRepository` [db_sqlite.py](file:///Users/aly/repos/kompass/backend/app/adapters/db_sqlite.py) which persists message history and scenarios by `session_id`.
* **User Story 15 (Global Profile Persistence):** As a frequent user, I want the app to remember my baseline likes and dislikes globally, so that when I start a new trip conversation, it automatically applies my previous preferences.
  * **Status:** `[x]` Completed
  * *Notes:* Implemented in SQLite database profiles table.

---

### G. Autonomy & Manual Labor Reduction
* **User Story 16 (Autonomous Draft Itinerary):** As a traveler overwhelmed by manual planning, I want the app to act with a high degree of autonomy (8-9 out of 10) to generate a complete draft itinerary from a high-level prompt, so that I am saved the manual labor of cross-referencing multiple booking sites.
  * **Status:** `[x]` Completed
  * *Notes:* Handled autonomously by `kompass_agent` using its tools [agent.py](file:///Users/aly/repos/kompass/backend/app/agent/agent.py).
