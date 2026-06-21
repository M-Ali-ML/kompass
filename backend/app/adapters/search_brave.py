from app.ports.search_service import SearchServicePort
import asyncio

class BraveSearchService(SearchServicePort):
    async def search_web(self, query: str) -> str:
        # Simulate network delay for MCP call
        await asyncio.sleep(1.0)
        # Return mock data for MVP
        return f"Mock search results for: {query}. Booking.com links and top attractions found."
