# Kompass App: System Architecture (Post-Building)

This document details the *implemented* system architecture of the Kompass travel planning application as of Phase 2.

---

## 1. Architectural Overview
The system consists of a Python FastAPI backend and a Next.js frontend, integrated using the AG-UI protocol and CopilotKit.

```
       +---------------------------------------+
       |           Next.js Frontend            |
       |  (CopilotKit Chat + gather_pref card  |
       |         + Tailwind CSS v4)            |
       +-------------------+-------------------+
                           | SSE Streaming (AG-UI Protocol)
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
       +-------------------+-------------------+
                           |
                           v
       +-------------------+-------------------+
       |          Prompt Service Port          |
       |   (app/ports/prompt_service.py)       |
       +-------------------+-------------------+
                           |
                           v
       +-------------------+-------------------+
       |       File Prompt Service Adapter     |
       | (app/adapters/file_prompt_service.py) |
       +---------------------------------------+
```

---

## 2. Backend Layer (Hexagonal Architecture)
The backend follows a **Hexagonal Architecture (Ports & Adapters)** pattern to separate the core business logic (agent & models) from infrastructure details (file prompt loading).

### A. Core Domain Models
Located in `backend/app/domain/`:
* [trip.py](file:///Users/aly/repos/kompass/backend/app/domain/trip.py) — `TripRequest` model (destination, dates, duration, budget, etc.).
* [user_preferences.py](file:///Users/aly/repos/kompass/backend/app/domain/user_preferences.py) — `UserPreferences` model (direct flights only, preferred transit modes, hotel standard, vibe tags).
* [itinerary.py](file:///Users/aly/repos/kompass/backend/app/domain/itinerary.py) — `Itinerary` model wrapping travel legs, accommodations, and day-by-day summaries.
* [scenario.py](file:///Users/aly/repos/kompass/backend/app/domain/scenario.py) — `Scenario` model (wraps an itinerary, estimated costs, and stress score).

### B. Ports (Interfaces)
Located in `backend/app/ports/`:
* [prompt_service.py](file:///Users/aly/repos/kompass/backend/app/ports/prompt_service.py) — `PromptServicePort` defining method to load prompt templates.

### C. Adapters (Implementations)
Located in `backend/app/adapters/`:
* [file_prompt_service.py](file:///Users/aly/repos/kompass/backend/app/adapters/file_prompt_service.py) — `FilePromptService` which loads system prompt templates from local markdown files.

---

## 3. PydanticAI Agent Layer
The agent framework is managed via PydanticAI.

* **Agent Definition:** [agent.py](file:///Users/aly/repos/kompass/backend/app/agent/agent.py) instantiates `kompass_agent` using model settings from config and structured output union `Union[str, Scenario]`.
* **Agent Tools:**
  * `gather_preferences`: Registered on the agent to extract and save traveler preferences (vibe, hotel class, direct flight requirement, and preferred transit modes) into the agent's run context dependencies.
* **Dependency Injection:** [dependency.py](file:///Users/aly/repos/kompass/backend/app/agent/dependency.py) defines `AgentDependencies` dataclass enclosing `prompt_service` and `user_preferences`.

---

## 4. Web Service Interface
* **FastAPI Entrypoint:** [main.py](file:///Users/aly/repos/kompass/backend/app/main.py) running on FastAPI.
* **Endpoints:**
  * `GET /health`: Health-check endpoint.
  * `POST /api/copilotkit`: [routes.py](file:///Users/aly/repos/kompass/backend/app/api/routes.py) - Reconstructs the traveler's active `UserPreferences` from the message history and dispatches the PydanticAI run to CopilotKit/AG-UI stream.

---

## 5. Frontend Layer
* **Structure:** Next.js application located in `frontend/`.
* **Implementation Status:** Uses CopilotKit React SDK v2 for chat interface and streams reasoning/tool events. Implements the custom `gather_preferences` Generative UI visual card rendering and dynamic chat labels.
