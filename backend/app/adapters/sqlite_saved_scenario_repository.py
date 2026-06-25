"""SQLite-backed implementation of the SavedScenarioRepository port."""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.models import SavedScenario
from app.ports.saved_scenario_repository import SavedScenarioRepository

logger = logging.getLogger("kompass.repository.saved_scenario")


def _as_str(value) -> str | None:
    return str(value) if value not in (None, "") else None


class SqliteSavedScenarioRepository(SavedScenarioRepository):
    """Async SQLAlchemy adapter persisting saved scenarios to SQLite."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def save(self, *, scenario: dict, trip_id: str | None = None) -> SavedScenario:
        scenario = scenario or {}
        cost = scenario.get("cost_breakdown") or {}
        row = SavedScenario(
            trip_id=trip_id,
            destination=scenario.get("destination"),
            label=scenario.get("label") or scenario.get("comparison_label") or "Saved scenario",
            comparison_label=scenario.get("comparison_label"),
            start_date=_as_str(scenario.get("start_date")),
            end_date=_as_str(scenario.get("end_date")),
            currency=scenario.get("currency") or "EUR",
            grand_total=cost.get("grand_total"),
            stress_score=scenario.get("stress_score"),
            scenario=scenario,
        )
        async with self._session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
            logger.info(
                "Saved scenario %s (trip=%s, dest=%s)", row.id, trip_id, row.destination
            )
            return row

    async def list_saved(self, trip_id: str | None = None) -> list[SavedScenario]:
        stmt = select(SavedScenario).order_by(SavedScenario.created_at.desc())
        if trip_id is not None:
            stmt = stmt.where(SavedScenario.trip_id == trip_id)
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get(self, saved_id: int) -> SavedScenario | None:
        async with self._session_factory() as session:
            return await session.get(SavedScenario, saved_id)

    async def delete(self, saved_id: int) -> None:
        async with self._session_factory() as session:
            row = await session.get(SavedScenario, saved_id)
            if row is not None:
                await session.delete(row)
                await session.commit()
                logger.info("Deleted saved scenario %s", saved_id)
