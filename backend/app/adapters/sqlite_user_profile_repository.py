"""SQLite-backed implementation of the UserProfileRepository port."""
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.domain import UserPreferences
from app.domain.models.profile import DEFAULT_PROFILE_ID, UserProfile
from app.ports.user_profile_repository import UserProfileRepository

logger = logging.getLogger("kompass.repository.profile")


class SqliteUserProfileRepository(UserProfileRepository):
    """Async SQLAlchemy adapter persisting the global user profile."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def get_preferences(self) -> UserPreferences:
        async with self._session_factory() as session:
            profile = await session.get(UserProfile, DEFAULT_PROFILE_ID)
            if profile is None or not profile.preferences:
                return UserPreferences()
            return UserPreferences.model_validate(profile.preferences)

    async def save_preferences(self, preferences: UserPreferences) -> None:
        async with self._session_factory() as session:
            profile = await session.get(UserProfile, DEFAULT_PROFILE_ID)
            data = preferences.model_dump()
            if profile is None:
                profile = UserProfile(id=DEFAULT_PROFILE_ID, preferences=data)
                session.add(profile)
            else:
                profile.preferences = data
            await session.commit()
            logger.info("Saved global user preferences: %s", data)
