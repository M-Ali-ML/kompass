import os
import logging
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
        logger.info(f"Initialized MCPMathServiceAdapter with server path: {self.server_path}")

    async def add(self, a: int, b: int) -> int:
        logger.info(f"Calling MCP calculate_sum tool with: a={a}, b={b}")
        server_params = StdioServerParameters(
            command="uv",
            args=["run", self.server_path],
            env=os.environ.copy()
        )
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool("calculate_sum", arguments={"a": a, "b": b})
                
                if not result.content:
                    raise RuntimeError("No content returned from MCP server")
                
                if getattr(result, "isError", False):
                    raise RuntimeError(f"MCP server error: {result.content}")
                
                text_content = result.content[0].text
                logger.info(f"MCP calculate_sum response: {text_content}")
                return int(text_content.strip())
