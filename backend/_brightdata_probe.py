"""Throwaway live probe of the Bright Data MCP (SSE). Delete after use.

Lists tools and looks for Booking.com / hotel structured-data tools.
"""

import asyncio
import json
import os

from mcp import ClientSession
from mcp.client.sse import sse_client

TOKEN = os.environ["BRIGHTDATA_TOKEN"]
URL = f"https://mcp.brightdata.com/sse?token={TOKEN}"


async def main():
    async with sse_client(URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"=== {len(tools.tools)} TOOLS ===")
            for t in tools.tools:
                name = t.name
                desc = (t.description or "").replace("\n", " ")[:90]
                print(f"- {name}: {desc}")

            print("\n=== HOTEL / BOOKING-RELATED TOOLS (schemas) ===")
            for t in tools.tools:
                blob = (t.name + " " + (t.description or "")).lower()
                if any(k in blob for k in ("booking", "hotel", "lodg", "accommod", "airbnb")):
                    print(f"\n## {t.name}")
                    print(json.dumps((t.inputSchema or {}).get("properties", {}), indent=2)[:1200])


if __name__ == "__main__":
    asyncio.run(main())
