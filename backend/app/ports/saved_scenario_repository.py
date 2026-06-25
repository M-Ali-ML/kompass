"""Port interface for persisting and retrieving user-saved scenarios."""
from abc import ABC, abstractmethod

from app.domain.models import SavedScenario


class SavedScenarioRepository(ABC):
    """Persistence boundary for saved trip scenarios."""

    @abstractmethod
    async def save(self, *, scenario: dict, trip_id: str | None = None) -> SavedScenario:
        """Persist a scenario payload (optionally linked to a trip) and return the row."""

    @abstractmethod
    async def list_saved(self, trip_id: str | None = None) -> list[SavedScenario]:
        """Return saved scenarios, most recent first. Filter by trip when given."""

    @abstractmethod
    async def get(self, saved_id: int) -> SavedScenario | None:
        """Return a single saved scenario by id, or None."""

    @abstractmethod
    async def delete(self, saved_id: int) -> None:
        """Delete a saved scenario. No-op if it does not exist."""
