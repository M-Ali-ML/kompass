"""Port interface for persisting a trip's generated background image."""
from abc import ABC, abstractmethod

from app.domain.models import TripBackground


class TripBackgroundRepository(ABC):
    """Persistence boundary for per-trip vibe background images."""

    @abstractmethod
    async def get(self, trip_id: str) -> TripBackground | None:
        """Return the background row for a trip, or None if none exists."""

    @abstractmethod
    async def try_begin(self, trip_id: str) -> bool:
        """Atomically claim generation for a trip.

        Inserts a ``pending`` row and returns True if this caller won the claim.
        Returns False if a row already exists (another job is in flight or a
        result is already cached), so the caller should skip.
        """

    @abstractmethod
    async def save_ready(
        self,
        trip_id: str,
        *,
        destination: str | None,
        scene_prompt: str | None,
        image: bytes,
        mime: str,
    ) -> None:
        """Store the finished image bytes and mark the row ``ready`` (upsert)."""

    @abstractmethod
    async def set_status(self, trip_id: str, status: str) -> None:
        """Update the lifecycle status (e.g. to ``error``) for a trip."""

    @abstractmethod
    async def clear(self, trip_id: str) -> None:
        """Delete the background row for a trip. No-op if absent."""
