from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.models import ScenarioMatrix, UserPreferenceProfile

class TripRepositoryPort(ABC):
    @abstractmethod
    async def get_user_profile(self, user_id: str) -> Optional[UserPreferenceProfile]:
        pass

    @abstractmethod
    async def save_user_profile(self, profile: UserPreferenceProfile) -> None:
        pass

    @abstractmethod
    async def save_scenario_matrix(self, session_id: str, matrix: ScenarioMatrix) -> None:
        pass

    @abstractmethod
    async def get_scenario_matrix(self, session_id: str) -> Optional[ScenarioMatrix]:
        pass

    @abstractmethod
    async def append_message(self, session_id: str, role: str, content: str) -> None:
        pass

    @abstractmethod
    async def get_messages(self, session_id: str) -> List[dict]:
        pass
