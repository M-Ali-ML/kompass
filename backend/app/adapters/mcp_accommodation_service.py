import json
import logging
import os
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.domain.accommodations import AccommodationOption
from app.ports.accommodation_service import AccommodationServicePort

logger = logging.getLogger("kompass.mcp_accommodation_service")


class MCPAccommodationServiceAdapter(AccommodationServicePort):
    """Talks to the standalone Accommodations MCP server over a persistent stdio session.

    Follows the same lifecycle pattern as the Flights MCP adapter: a single
    long-lived subprocess started on app startup and torn down on shutdown.
    """

    def __init__(self, server_path: str | None = None):
        if not server_path:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            server_path = os.path.join(
                current_dir, "..", "mcp_servers", "accommodations_server.py"
            )
        self.server_path = os.path.abspath(server_path)
        self.exit_stack: AsyncExitStack | None = None
        self.session: ClientSession | None = None
        logger.info(
            f"Initialized MCPAccommodationServiceAdapter with server path: {self.server_path}"
        )

    async def start(self) -> None:
        if self.session is not None:
            logger.info("Accommodations MCP client already started.")
            return

        logger.info("Starting persistent Accommodations MCP client subprocess...")
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
            logger.info("Accommodations MCP client initialized successfully.")
        except Exception:
            logger.exception("Failed to start persistent Accommodations MCP client")
            await self.exit_stack.aclose()
            self.exit_stack = None
            self.session = None
            raise

    async def stop(self) -> None:
        if self.exit_stack:
            logger.info("Stopping persistent Accommodations MCP client subprocess...")
            await self.exit_stack.aclose()
            self.exit_stack = None
            self.session = None
            logger.info("Accommodations MCP client stopped cleanly.")

    async def _call(self, tool_name: str, arguments: dict) -> dict:
        if self.session is None:
            logger.warning("Accommodations MCP client not started. Automatically starting...")
            await self.start()

        logger.info(f"Calling Accommodations MCP tool '{tool_name}' with: {arguments}")
        result = await self.session.call_tool(tool_name, arguments=arguments)

        if getattr(result, "isError", False):
            raise RuntimeError(f"Accommodations MCP server error: {result.content}")

        # Prefer structured content; fall back to parsing the text block as JSON.
        structured = getattr(result, "structuredContent", None)
        if isinstance(structured, dict):
            return structured
        if not result.content:
            raise RuntimeError("No content returned from Accommodations MCP server")
        return json.loads(result.content[0].text)

    async def search_accommodations(
        self,
        destination: str,
        *,
        check_in_date: str,
        check_out_date: str,
        guests: int = 2,
        max_price: int | None = None,
        min_rating: float | None = None,
        currency: str = "EUR",
    ) -> list[AccommodationOption]:
        arguments = {
            "destination": destination,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "guests": guests,
            "currency": currency,
        }
        if max_price is not None:
            arguments["max_price"] = max_price
        if min_rating is not None:
            arguments["min_rating"] = min_rating

        payload = await self._call("search_accommodations", arguments)
        return [AccommodationOption(**opt) for opt in payload.get("options", [])]


# Singleton instance started/stopped by the FastAPI lifespan.
accommodation_service = MCPAccommodationServiceAdapter()
