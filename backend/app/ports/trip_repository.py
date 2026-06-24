"""Port interface for persisting and retrieving trip conversations."""
from abc import ABC, abstractmethod

from app.domain.models import Message, Trip


class TripRepository(ABC):
    """Persistence boundary for trips and their conversation messages."""

    @abstractmethod
    async def list_trips(self) -> list[Trip]:
        """Return all trips, most recently updated first."""

    @abstractmethod
    async def get_trip(self, trip_id: str) -> Trip | None:
        """Return a single trip with its messages eagerly loaded, or None."""

    @abstractmethod
    async def get_messages(self, trip_id: str) -> list[Message]:
        """Return the ordered messages for a trip."""

    @abstractmethod
    async def create_trip(self, trip_id: str, title: str) -> Trip:
        """Create a new trip with the given id and title."""

    @abstractmethod
    async def upsert_trip(self, trip_id: str, title: str | None = None) -> Trip:
        """Return the existing trip, creating it (with title) if absent."""

    @abstractmethod
    async def replace_messages(
        self, trip_id: str, messages: list[dict]
    ) -> None:
        """Replace all stored messages for a trip with the provided list.

        Each item must be a dict with ``role`` and ``content`` keys. Used to
        keep the persisted conversation in sync with the latest agent run.
        """

    @abstractmethod
    async def delete_trip(self, trip_id: str) -> None:
        """Delete a trip and its messages. No-op if the trip does not exist."""
