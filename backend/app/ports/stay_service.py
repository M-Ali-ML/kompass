from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.models import StayDetail

class StayServicePort(ABC):
    @abstractmethod
    async def search_stays(self, location: str, check_in: str, check_out: str, guests: int = 2) -> List[StayDetail]:
        """Search for accommodations based on parameters."""
        pass
