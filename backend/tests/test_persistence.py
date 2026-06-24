import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import Base
from app.adapters.sqlite_trip_repository import SqliteTripRepository
from app.adapters.sqlite_user_profile_repository import SqliteUserProfileRepository
from app.domain import UserPreferences


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_trip_lifecycle_and_message_sync(session_factory):
    repo = SqliteTripRepository(session_factory)

    trip = await repo.upsert_trip("thread-1", "Trip to Greece")
    assert trip.id == "thread-1"
    assert trip.title == "Trip to Greece"

    # Upsert is idempotent — no duplicate, original title preserved.
    again = await repo.upsert_trip("thread-1", "Different title")
    assert again.title == "Trip to Greece"

    await repo.replace_messages(
        "thread-1",
        [
            {"role": "user", "content": "Plan a trip to Greece"},
            {"role": "assistant", "content": "Sure! When are you going?"},
            {"role": "system", "content": "ignored"},
            {"role": "user", "content": "   "},  # empty content dropped
        ],
    )

    loaded = await repo.get_trip("thread-1")
    assert loaded is not None
    assert [m.role for m in loaded.messages] == ["user", "assistant"]
    assert loaded.messages[0].content == "Plan a trip to Greece"

    # Replacing again fully overwrites prior messages.
    await repo.replace_messages(
        "thread-1", [{"role": "user", "content": "Actually, Italy"}]
    )
    msgs = await repo.get_messages("thread-1")
    assert len(msgs) == 1
    assert msgs[0].content == "Actually, Italy"

    trips = await repo.list_trips()
    assert len(trips) == 1

    await repo.delete_trip("thread-1")
    assert await repo.get_trip("thread-1") is None


@pytest.mark.asyncio
async def test_profile_persistence_and_merge(session_factory):
    repo = SqliteUserProfileRepository(session_factory)

    # Defaults when nothing stored yet.
    assert await repo.get_preferences() == UserPreferences()

    await repo.save_preferences(
        UserPreferences(direct_flights_only=True, vibe_tags=["foodie"])
    )
    stored = await repo.get_preferences()
    assert stored.direct_flights_only is True
    assert stored.vibe_tags == ["foodie"]

    # Conversation prefs layer on top of the stored baseline.
    merged = stored.merged_with(UserPreferences(hotel_class="5-star"))
    assert merged.direct_flights_only is True
    assert merged.vibe_tags == ["foodie"]
    assert merged.hotel_class == "5-star"


def test_extract_display_messages_flattens_turns():
    from pydantic_ai.messages import (
        ModelRequest,
        ModelResponse,
        SystemPromptPart,
        TextPart,
        UserPromptPart,
    )
    from app.api.routes import extract_display_messages

    history = [
        ModelRequest(parts=[
            SystemPromptPart(content="you are a travel agent"),
            UserPromptPart(content="Plan a trip to Greece"),
        ]),
        ModelResponse(parts=[TextPart(content="Sure! When?")]),
        ModelRequest(parts=[UserPromptPart(content="September")]),
        ModelResponse(parts=[TextPart(content="Great choice.")]),
    ]

    display = extract_display_messages(history)
    assert display == [
        {"role": "user", "content": "Plan a trip to Greece"},
        {"role": "assistant", "content": "Sure! When?"},
        {"role": "user", "content": "September"},
        {"role": "assistant", "content": "Great choice."},
    ]
