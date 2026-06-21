from abc import ABC, abstractmethod

class SearchServicePort(ABC):
    @abstractmethod
    async def search_web(self, query: str) -> str:
        """Search the web for general queries (e.g., booking.com links, activity info)."""
        pass
