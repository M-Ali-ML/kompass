"""Port interface for the global, cross-trip user profile."""
from abc import ABC, abstractmethod

from app.domain import UserPreferences


class UserProfileRepository(ABC):
    """Persistence boundary for learned traveler preferences."""

    @abstractmethod
    async def get_preferences(self) -> UserPreferences:
        """Return the stored global preferences (defaults if none saved yet)."""

    @abstractmethod
    async def save_preferences(self, preferences: UserPreferences) -> None:
        """Persist the global preferences, overwriting any prior value."""
