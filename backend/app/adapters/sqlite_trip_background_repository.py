"""SQLite-backed implementation of the TripBackgroundRepository port."""
import logging
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.models import TripBackground
from app.ports.trip_background_repository import TripBackgroundRepository

logger = logging.getLogger("kompass.repository.trip_background")


class SqliteTripBackgroundRepository(TripBackgroundRepository):
    """Async SQLAlchemy adapter persisting trip background images to SQLite."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def get(self, trip_id: str) -> TripBackground | None:
        async with self._session_factory() as session:
            return await session.get(TripBackground, trip_id)

    async def try_begin(self, trip_id: str) -> bool:
        # Insert a pending row; the PRIMARY KEY makes this atomic — a duplicate
        # insert raises IntegrityError, which we treat as "someone else owns it".
        async with self._session_factory() as session:
            existing = await session.get(TripBackground, trip_id)
            if existing is not None:
                return False
            session.add(TripBackground(trip_id=trip_id, status="pending"))
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return False
            logger.info("Claimed background generation for trip %s", trip_id)
            return True

    async def save_ready(
        self,
        trip_id: str,
        *,
        destination: str | None,
        scene_prompt: str | None,
        image: bytes,
        mime: str,
    ) -> None:
        async with self._session_factory() as session:
            row = await session.get(TripBackground, trip_id)
            if row is None:
                row = TripBackground(trip_id=trip_id)
                session.add(row)
            row.status = "ready"
            row.destination = destination
            row.scene_prompt = scene_prompt
            row.image = image
            row.mime = mime
            row.updated_at = datetime.now(timezone.utc)
            await session.commit()
            logger.info(
                "Stored ready background for trip %s (%d bytes, %s)",
                trip_id,
                len(image),
                mime,
            )

    async def set_status(self, trip_id: str, status: str) -> None:
        async with self._session_factory() as session:
            row = await session.get(TripBackground, trip_id)
            if row is None:
                row = TripBackground(trip_id=trip_id, status=status)
                session.add(row)
            else:
                row.status = status
            row.updated_at = datetime.now(timezone.utc)
            await session.commit()

    async def clear(self, trip_id: str) -> None:
        async with self._session_factory() as session:
            row = await session.get(TripBackground, trip_id)
            if row is not None:
                await session.delete(row)
                await session.commit()
