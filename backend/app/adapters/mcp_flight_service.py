import json
import logging
import os
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.domain.flights import FlightDateOption, FlightOption
from app.ports.flight_service import FlightServicePort

logger = logging.getLogger("kompass.mcp_flight_service")


class MCPFlightServiceAdapter(FlightServicePort):
    """Talks to the standalone Flights MCP server over a persistent stdio session.

    Follows the same lifecycle pattern as the former math MCP adapter: a single
    long-lived subprocess started on app startup and torn down on shutdown.
    """

    def __init__(self, server_path: str | None = None):
        if not server_path:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            server_path = os.path.join(current_dir, "..", "mcp_servers", "flights_server.py")
        self.server_path = os.path.abspath(server_path)
        self.exit_stack: AsyncExitStack | None = None
        self.session: ClientSession | None = None
        logger.info(f"Initialized MCPFlightServiceAdapter with server path: {self.server_path}")

    async def start(self) -> None:
        if self.session is not None:
            logger.info("Flights MCP client already started.")
            return

        logger.info("Starting persistent Flights MCP client subprocess...")
        server_params = StdioServerParameters(
            command="uv",
            args=["run", self.server_path],
            env=os.environ.copy(),
        )
        self.exit_stack = AsyncExitStack()
        try:
            read_stream, write_stream = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self.session.initialize()
            logger.info("Flights MCP client initialized successfully.")
        except Exception:
            logger.exception("Failed to start persistent Flights MCP client")
            await self.exit_stack.aclose()
            self.exit_stack = None
            self.session = None
            raise

    async def stop(self) -> None:
        if self.exit_stack:
            logger.info("Stopping persistent Flights MCP client subprocess...")
            await self.exit_stack.aclose()
            self.exit_stack = None
            self.session = None
            logger.info("Flights MCP client stopped cleanly.")

    async def _call(self, tool_name: str, arguments: dict) -> dict:
        if self.session is None:
            logger.warning("Flights MCP client not started. Automatically starting...")
            await self.start()

        logger.info(f"Calling Flights MCP tool '{tool_name}' with: {arguments}")
        result = await self.session.call_tool(tool_name, arguments=arguments)

        if getattr(result, "isError", False):
            raise RuntimeError(f"Flights MCP server error: {result.content}")

        # Prefer structured content; fall back to parsing the text block as JSON.
        structured = getattr(result, "structuredContent", None)
        if isinstance(structured, dict):
            return structured
        if not result.content:
            raise RuntimeError("No content returned from Flights MCP server")
        return json.loads(result.content[0].text)

    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        *,
        passengers: int = 1,
        max_stops: int | None = None,
        preferred_time: str | None = None,
        currency: str = "EUR",
    ) -> list[FlightOption]:
        arguments = {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "passengers": passengers,
            "currency": currency,
        }
        if max_stops is not None:
            arguments["max_stops"] = max_stops
        if preferred_time is not None:
            arguments["preferred_time"] = preferred_time

        payload = await self._call("search_flights", arguments)
        return [FlightOption(**opt) for opt in payload.get("options", [])]

    async def find_cheapest_dates(
        self,
        origin: str,
        destination: str,
        *,
        date_from: str,
        date_to: str,
        duration_days: int | None = None,
        currency: str = "EUR",
    ) -> list[FlightDateOption]:
        arguments = {
            "origin": origin,
            "destination": destination,
            "date_from": date_from,
            "date_to": date_to,
            "currency": currency,
        }
        if duration_days is not None:
            arguments["duration_days"] = duration_days

        payload = await self._call("find_cheapest_dates", arguments)
        return [FlightDateOption(**opt) for opt in payload.get("options", [])]


# Singleton instance started/stopped by the FastAPI lifespan.
flight_service = MCPFlightServiceAdapter()
