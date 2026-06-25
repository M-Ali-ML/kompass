"""SQLite-backed implementation of the TripRepository port."""
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import Message, Trip
from app.ports.trip_repository import TripRepository

logger = logging.getLogger("kompass.repository.trip")


class SqliteTripRepository(TripRepository):
    """Async SQLAlchemy adapter persisting trips to the SQLite database."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def list_trips(self) -> list[Trip]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Trip).order_by(Trip.updated_at.desc())
            )
            return list(result.scalars().all())

    async def get_trip(self, trip_id: str) -> Trip | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Trip)
                .options(selectinload(Trip.messages))
                .where(Trip.id == trip_id)
            )
            return result.scalar_one_or_none()

    async def get_messages(self, trip_id: str) -> list[Message]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Message)
                .where(Message.trip_id == trip_id)
                .order_by(Message.id)
            )
            return list(result.scalars().all())

    async def create_trip(self, trip_id: str, title: str) -> Trip:
        async with self._session_factory() as session:
            trip = Trip(id=trip_id, title=title)
            session.add(trip)
            await session.commit()
            await session.refresh(trip)
            logger.info("Created trip %s ('%s')", trip_id, title)
            return trip

    async def upsert_trip(self, trip_id: str, title: str | None = None) -> Trip:
        async with self._session_factory() as session:
            trip = await session.get(Trip, trip_id)
            if trip is None:
                trip = Trip(id=trip_id, title=title or "New Trip")
                session.add(trip)
                await session.commit()
                await session.refresh(trip)
                logger.info("Upsert created trip %s ('%s')", trip_id, trip.title)
            return trip

    async def replace_messages(self, trip_id: str, messages: list[dict]) -> None:
        async with self._session_factory() as session:
            trip = await session.get(Trip, trip_id)
            if trip is None:
                logger.warning("replace_messages: trip %s not found", trip_id)
                return

            await session.execute(
                delete(Message).where(Message.trip_id == trip_id)
            )
            for item in messages:
                content = (item.get("content") or "").strip()
                role = item.get("role")
                if not content or role not in ("user", "assistant"):
                    continue
                session.add(Message(trip_id=trip_id, role=role, content=content))

            # Touch updated_at so the trip sorts to the top of the list.
            trip.updated_at = datetime.now(timezone.utc)
            await session.commit()
            logger.info("Synced %d messages for trip %s", len(messages), trip_id)

    async def save_message_history(
        self, trip_id: str, messages: list[dict], title: str | None = None
    ) -> None:
        async with self._session_factory() as session:
            trip = await session.get(Trip, trip_id)
            if trip is None:
                trip = Trip(id=trip_id, title=title or "New Trip")
                session.add(trip)
            elif title and trip.title in (None, "", "New Trip"):
                trip.title = title

            trip.message_history = messages
            trip.updated_at = datetime.now(timezone.utc)
            await session.commit()
            logger.info(
                "Stored %d-message history for trip %s", len(messages), trip_id
            )

    async def get_message_history(self, trip_id: str) -> list[dict]:
        async with self._session_factory() as session:
            trip = await session.get(Trip, trip_id)
            if trip is None or not trip.message_history:
                return []
            return list(trip.message_history)

    async def delete_trip(self, trip_id: str) -> None:
        async with self._session_factory() as session:
            trip = await session.get(Trip, trip_id)
            if trip is not None:
                await session.delete(trip)
                await session.commit()
                logger.info("Deleted trip %s", trip_id)
