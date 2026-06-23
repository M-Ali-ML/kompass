import os
import logging
from contextlib import AsyncExitStack
from app.ports.math_service import MathServicePort
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("kompass.mcp_math_service")

class MCPMathServiceAdapter(MathServicePort):
    def __init__(self, server_path: str = None):
        if not server_path:
            # Locate relative to this file: app/adapters/../../app/mcp_server.py
            current_dir = os.path.dirname(os.path.abspath(__file__))
            server_path = os.path.join(current_dir, "..", "mcp_server.py")
        self.server_path = os.path.abspath(server_path)
        self.exit_stack = None
        self.session = None
        logger.info(f"Initialized MCPMathServiceAdapter with server path: {self.server_path}")

    async def start(self):
        if self.session is not None:
            logger.info("MCP client already started.")
            return

        logger.info("Starting persistent MCP client subprocess...")
        server_params = StdioServerParameters(
            command="uv",
            args=["run", self.server_path],
            env=os.environ.copy()
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
            logger.info("MCP client initialized successfully.")
        except Exception as e:
            logger.exception("Failed to start persistent MCP client")
            await self.exit_stack.aclose()
            self.exit_stack = None
            self.session = None
            raise e

    async def stop(self):
        if self.exit_stack:
            logger.info("Stopping persistent MCP client subprocess...")
            await self.exit_stack.aclose()
            self.exit_stack = None
            self.session = None
            logger.info("MCP client stopped cleanly.")

    async def add(self, a: int, b: int) -> int:
        if self.session is None:
            logger.warning("MCP client not started. Automatically starting...")
            await self.start()

        logger.info(f"Calling persistent MCP calculate_sum tool with: a={a}, b={b}")
        result = await self.session.call_tool("calculate_sum", arguments={"a": a, "b": b})
        
        if not result.content:
            raise RuntimeError("No content returned from MCP server")
        
        if getattr(result, "isError", False):
            raise RuntimeError(f"MCP server error: {result.content}")
        
        text_content = result.content[0].text
        logger.info(f"MCP calculate_sum response: {text_content}")
        return int(text_content.strip())

# Singleton instance of the adapter
mcp_service = MCPMathServiceAdapter()

