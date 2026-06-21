from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.models import FlightDetail

class FlightServicePort(ABC):
    @abstractmethod
    async def search_flights(self, origin: str, destination: str, date: str, passengers: int = 1) -> List[FlightDetail]:
        """Search for flights based on parameters."""
        pass
