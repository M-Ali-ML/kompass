# Kompass App: System Architecture (Post-Building)

This document details the *implemented* system architecture of the Kompass travel planning application.

---

## 1. Architectural Overview
The system consists of a Python FastAPI backend and a Next.js frontend, utilizing an SQLite database for persistence.

```
       +---------------------------------------+
       |           Next.js Frontend            |
       |  (Boilerplate NextJS; no CopilotKit/  |
       |     AGUI integrated in UI yet)        |
       +-------------------+-------------------+
                           | HTTP / JSON
                           v
       +-------------------+-------------------+
       |            FastAPI Web App            |
       |       (backend/app/main.py)           |
       +-------------------+-------------------+
                           |
                           v
       +-------------------+-------------------+
       |            PydanticAI Agent           |
       |      (backend/app/agent/agent.py)     |
       +-------+--------------+-------------+--+
               |              |             |
               v (Port)       v (Port)      v (Port)
       +---------------+ +------------+ +------------+
       |   Repository  | |   Flights  | |    Stays   |
       +---------------+ +------------+ +------------+
               |              |             |
               v (Adapter)    v (Adapter)   v (Adapter)
       +---------------+ +------------+ +------------+
       | SQLite DB     | | Mock       | | Mock       |
       | (kompass.db)  | | Service    | | Service    |
       +---------------+ +------------+ +------------+
```

---

## 2. Backend Layer (Hexagonal Architecture)
The backend strictly follows a **Hexagonal Architecture (Ports & Adapters)** pattern to separate the core business logic (agent & models) from infrastructure details (SQLite database & API mocks).

### A. Core Domain Models
Located in [models.py](file:///Users/aly/repos/kompass/backend/app/domain/models.py):
* `FlightDetail`: Details about specific flight offers.
* `StayDetail`: Details about accommodation offers.
* `ActivityDetail`: Individual daily activities.
* `ItineraryDay`: Bundles a list of activities for a single day.
* `ItineraryScenario`: Represents a single structured travel plan comparison variant (subtotals, totals, stress score, flights, stays, itinerary).
* `ScenarioMatrix`: A list of generated scenarios and active constraints returned by the agent.
* `UserPreferenceProfile`: Holds a user's preferences, budget thresholds, and other global constraints.

### B. Ports (Interfaces)
Located in `backend/app/ports/`:
* [repository.py](file:///Users/aly/repos/kompass/backend/app/ports/repository.py): `TripRepositoryPort` defining profiles, scenario matrices, and message persistence.
* [flight_service.py](file:///Users/aly/repos/kompass/backend/app/ports/flight_service.py): `FlightServicePort` defining flight searching.
* [stay_service.py](file:///Users/aly/repos/kompass/backend/app/ports/stay_service.py): `StayServicePort` defining stay searching.
* [search_service.py](file:///Users/aly/repos/kompass/backend/app/ports/search_service.py): `SearchServicePort` defining generic web search capabilities.

### C. Adapters (Implementations)
Located in `backend/app/adapters/`:
* [db_sqlite.py](file:///Users/aly/repos/kompass/backend/app/adapters/db_sqlite.py): `SQLiteTripRepository` - stores data locally in a `kompass.db` file.
* [fli_flights.py](file:///Users/aly/repos/kompass/backend/app/adapters/fli_flights.py): `FliFlightService` - simulates network delays and returns randomized mock flight data.
* [openbnb_stays.py](file:///Users/aly/repos/kompass/backend/app/adapters/openbnb_stays.py): `AirbnbStayService` - simulates network delays and returns randomized mock stay data.
* [search_brave.py](file:///Users/aly/repos/kompass/backend/app/adapters/search_brave.py): `BraveSearchService` - simulates web search returns.

---

## 3. PydanticAI Agent Layer
The agent framework is managed via PydanticAI.

* **Agent Definition:** [agent.py](file:///Users/aly/repos/kompass/backend/app/agent/agent.py) instantiates `kompass_agent` using model `'gemini-1.5-flash'` with structured output enforcement for `ScenarioMatrix`.
* **Agent Tools:**
  * `check_flights`: Calls the flight service adapter.
  * `check_stays`: Calls the stays service adapter.
  * `web_search`: Calls the brave search service adapter.
* **Dependency Injection:** [dependency.py](file:///Users/aly/repos/kompass/backend/app/agent/dependency.py) defines `AgentDependencies` dataclass and the `get_agent_dependencies(session_id)` helper function.

---

## 4. Web Service Interface
* **FastAPI Entrypoint:** [main.py](file:///Users/aly/repos/kompass/backend/app/main.py) running on FastAPI.
* **Endpoints:**
  * `GET /health`: Health-check endpoint.
  * `POST /api/chat`: Accepts user prompt and `session_id`, loads user profile and dependencies, appends message to the SQLite database, runs the `kompass_agent` to generate a `ScenarioMatrix`, saves the results in SQLite, and returns a JSON response.

---

## 5. Frontend Layer
* **Structure:** Next.js application located in `/Users/aly/repos/kompass/frontend`.
* **Implementation Status:** Standard Next.js boilerplate from `create-next-app` using Tailwind CSS. 
* *Note:* CopilotKit, AGUI Protocol streams, Map rendering, and Candy theme components are not yet integrated into the UI code.
