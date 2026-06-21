# Kompass App: System Architecture Document

## 1. Architectural Pattern: Hexagonal Architecture (Ports and Adapters)

To ensure the core travel planning logic remains independent of external APIs and user interfaces, the backend will strictly follow a **Hexagonal Architecture**.

* **Core Domain:** The central travel architect logic, defined by strict schemas, which calculates stress scores, route logic, and total trip budgets.
* **Primary Driving Adapters (Input):** The frontend interfaces and AGUI event listeners that send user prompts to the backend.
* **Secondary Driven Adapters (Output):** The MCP servers connecting to external travel APIs, and the SQLite repositories handling database operations.

## 2. Frontend Layer (User Experience & State)

The frontend is designed to be highly reactive, visually rendering the agent's thought process and outputs without requiring traditional polling.

* **CopilotKit:** Used as the primary framework for managing the chat interface and seamlessly syncing the frontend React state with the backend agent's state.
* **AGUI Protocol:** A lightweight, event-driven protocol used to stream state updates, human-in-the-loop (HITL) breakpoints, and tool calls directly from the agent to the UI over a shared event bus.
* **Generative UI:** Used to render complex, structured data directly in the chat or main panel instead of plain text. This includes the `<SearchProgress />` indicator and the side-by-side **Scenario Comparison Matrix**.
* **Google Maps API:** Integrated dynamically on the frontend. The map state is bound to the agent's state via CopilotKit, allowing the map to plot origin, destination, and transit legs in real-time as the agent plans.

## 3. Agent Harness & Intelligence Layer (The Brain)

The intelligence layer focuses on strict data structure, reliability, and observability.

* **PydanticAI:** Acts as the core agent framework. Because the Generative UI (like the comparison table) requires exact data structures, PydanticAI is used to enforce strict JSON schema outputs and type-safe tool parameters. Its `RunContext` handles dependency injection for securely passing session data.
* **Langfuse Telemetry:** The observability platform used to trace the agent's execution steps. It traces every LLM call, tool invocation, and retrieval step, allowing us to debug context rot, monitor token costs, and track exactly how the agent formulated a specific itinerary.

## 4. Integration & External Data Layer (MCP)

Instead of building bespoke REST API wrappers for every travel provider, the app uses standard protocols to connect the agent to the outside world.

* **Model Context Protocol (MCP):** The standardized architecture for connecting our PydanticAI agent to external data.
* **MCP Servers:** We will build or run isolated MCP servers for specific tasks:
  * *Flights MCP Server:* Connects to Google Flights/Skyscanner to fetch live prices and schedules.
  * *Accommodations MCP Server:* Checks live hotel availability.
  * *Geospatial MCP Server:* Provides distance and transit routing data if needed beyond the frontend map display.

## 5. Persistence & Memory Layer

* **SQLite:** Chosen as the lightweight, local database for the MVP. It is fast, requires zero configuration, and acts as the persistent store for our Hexagonal Architecture's repository adapters.
* **What it Stores:**
  * *Session/Trip Memory:* Storing the chat history and the generated scenario data to allow users to leave and resume planning later.
  * *User Preferences:* Basic persistence of the user's "global profile" (e.g., preference for direct flights or specific hotel chains).

## 6. Request Lifecycle (Data Flow Example)

1. **Input:** User types "Find me a 10-day trip to Greece in Sept" into the CopilotKit chat.
2. **Streaming:** The AGUI protocol emits a `<SearchProgress />` state to the frontend.
3. **Agent Action:** The PydanticAI agent processes the prompt and identifies it needs live prices.
4. **Tool Execution:** The agent communicates via MCP to the *Flights MCP Server* to get the data.
5. **Telemetry:** Langfuse logs the execution time, token cost, and intermediate steps of the tool call.
6. **Formatting:** PydanticAI formats the final data into a strict, validated schema representing the Scenario Comparison Matrix.
7. **Persistence:** The new trip scenarios are saved into SQLite.
8. **Output:** AGUI streams the structured data back to CopilotKit, which dynamically renders the Comparison Table and updates the Google Map markers.
