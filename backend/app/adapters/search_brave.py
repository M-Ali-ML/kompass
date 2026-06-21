from app.ports.search_service import SearchServicePort
import asyncio

class BraveSearchService(SearchServicePort):
    async def search_web(self, query: str) -> str:
        # Simulate network delay for MCP call
        await asyncio.sleep(1.0)
        q = query.lower()
        if "ubud" in q or "bali" in q:
            return (
                "Ubud, Bali, Indonesia. Famous cultural hub. "
                "Top attractions: Sacred Monkey Forest Sanctuary, Tegalalang Rice Terraces, Tirta Empul Temple, Ubud Art Market. "
                "Recommended hotel stays: Ubud Jungle Resort, Potato Head Suites. "
                "Flights arrive at Denpasar DPS airport. Best time to visit: April to October."
            )
        elif "tokyo" in q or "japan" in q:
            return (
                "Tokyo, Japan. Modern metropolis. "
                "Top attractions: Shibuya Sky, teamLab Borderless, Harajuku, Akihabara. "
                "Recommended hotel stays: Shibuya Stream Excel Hotel Tokyu. "
                "Flights arrive at Haneda HND or Narita NRT airports."
            )
        # Default fallback
        return f"Mock search results for: {query}. Top attractions and stays found. Recommended stay: Cozy Inn. Flight route: origin to destination."
