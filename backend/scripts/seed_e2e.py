"""Seed deterministic data for the frontend Playwright E2E suite.

Run with the same DATABASE_URL the test backend uses, e.g.:

    DATABASE_URL="sqlite+aiosqlite:////tmp/kompass_e2e_test.db" \
        .venv/bin/python scripts/seed_e2e.py

It resets the trips/messages/profile tables and inserts a known fixture so the
UI tests can assert against stable trip titles and conversation contents
without invoking the LLM.
"""
import asyncio

from sqlalchemy import delete

from app.db import SessionLocal, init_db
from app.adapters.sqlite_trip_repository import SqliteTripRepository
from app.adapters.sqlite_user_profile_repository import SqliteUserProfileRepository
from app.domain import UserPreferences
from app.domain.models import Message, Trip
from app.domain.models.profile import UserProfile
from app.domain.models.saved_scenario import SavedScenario

# Fixture data shared with the E2E specs. Keep titles and assistant lines
# unique and stable — the tests assert on these exact strings.
GREECE_TRIP_ID = "e2e-greece"
JAPAN_TRIP_ID = "e2e-japan"

GREECE_TITLE = "recommend a trip to greece in august"
JAPAN_TITLE = "two weeks in japan"

GREECE_ASSISTANT = "Greece in August is hot. Consider Athens then a ferry to Naxos."
JAPAN_ASSISTANT = "Two weeks in Japan: Tokyo, Kyoto, and Osaka with a JR Pass."


async def _reset() -> None:
    async with SessionLocal() as session:
        await session.execute(delete(Message))
        await session.execute(delete(Trip))
        await session.execute(delete(UserProfile))
        # Saved scenarios aren't part of the fixture, but clearing them keeps the
        # Saved-tab E2E spec deterministic across reruns (it creates its own).
        await session.execute(delete(SavedScenario))
        await session.commit()


async def main() -> None:
    await init_db()
    await _reset()

    trips = SqliteTripRepository(SessionLocal)
    profiles = SqliteUserProfileRepository(SessionLocal)

    # Insert japan first so greece ends up most-recently-updated (top of list).
    await trips.upsert_trip(JAPAN_TRIP_ID, JAPAN_TITLE)
    await trips.replace_messages(
        JAPAN_TRIP_ID,
        [
            {"role": "user", "content": JAPAN_TITLE},
            {"role": "assistant", "content": JAPAN_ASSISTANT},
        ],
    )

    await trips.upsert_trip(GREECE_TRIP_ID, GREECE_TITLE)
    await trips.replace_messages(
        GREECE_TRIP_ID,
        [
            {"role": "user", "content": GREECE_TITLE},
            {"role": "assistant", "content": GREECE_ASSISTANT},
        ],
    )

    await profiles.save_preferences(
        UserPreferences(direct_flights_only=True, vibe_tags=["foodie"])
    )

    print("E2E seed complete: greece + japan trips, profile preferences set.")


if __name__ == "__main__":
    asyncio.run(main())
