"""Tests for the trip vibe background image generator.

The cheap Gemini scene + image calls are mocked so these stay offline; we only
exercise the orchestration logic: the ready path, the no-destination skip, the
error path, and the run-once dedupe guard.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.agent.image_agent as image_agent
from app.agent.image_agent import BackgroundScene, generate_trip_background
from app.adapters.sqlite_trip_background_repository import SqliteTripBackgroundRepository
from app.db import Base
from app.domain.user_preferences import UserPreferences


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


@pytest.fixture(autouse=True)
def _reset_in_flight():
    image_agent._in_flight.clear()
    yield
    image_agent._in_flight.clear()


def _mock_scene(monkeypatch, *, destination):
    async def _fake_describe(conversation_text, preferences):
        if destination is None:
            return BackgroundScene(destination=None, scene_prompt="n/a")
        return BackgroundScene(destination=destination, scene_prompt="a vivid scene")

    monkeypatch.setattr(image_agent, "_describe_scene", _fake_describe)


@pytest.mark.asyncio
async def test_ready_path_stores_image(session_factory, monkeypatch):
    monkeypatch.setattr(image_agent, "SessionLocal", session_factory)
    monkeypatch.setattr(image_agent.settings, "background_image_enabled", True)
    _mock_scene(monkeypatch, destination="Santorini")

    async def _fake_generate(prompt):
        return (b"IMG_BYTES", "image/webp")

    monkeypatch.setattr(image_agent, "_generate_image", _fake_generate)

    await generate_trip_background("trip-1", "Plan Santorini", UserPreferences())

    repo = SqliteTripBackgroundRepository(session_factory)
    row = await repo.get("trip-1")
    assert row is not None
    assert row.status == "ready"
    assert row.image == b"IMG_BYTES"
    assert row.mime == "image/webp"
    assert row.destination == "Santorini"


@pytest.mark.asyncio
async def test_no_destination_skips_and_leaves_no_row(session_factory, monkeypatch):
    monkeypatch.setattr(image_agent, "SessionLocal", session_factory)
    monkeypatch.setattr(image_agent.settings, "background_image_enabled", True)
    _mock_scene(monkeypatch, destination=None)

    called = False

    async def _fake_generate(prompt):
        nonlocal called
        called = True
        return (b"X", "image/webp")

    monkeypatch.setattr(image_agent, "_generate_image", _fake_generate)

    await generate_trip_background("trip-2", "Somewhere warm?", UserPreferences())

    # No destination yet -> no lock row, so a later turn can retry, and the
    # expensive image call is never made.
    repo = SqliteTripBackgroundRepository(session_factory)
    assert await repo.get("trip-2") is None
    assert called is False


@pytest.mark.asyncio
async def test_error_path_marks_row_error(session_factory, monkeypatch):
    monkeypatch.setattr(image_agent, "SessionLocal", session_factory)
    monkeypatch.setattr(image_agent.settings, "background_image_enabled", True)
    _mock_scene(monkeypatch, destination="Kyoto")

    async def _boom(prompt):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(image_agent, "_generate_image", _boom)

    await generate_trip_background("trip-3", "Plan Kyoto", UserPreferences())

    repo = SqliteTripBackgroundRepository(session_factory)
    row = await repo.get("trip-3")
    assert row is not None
    assert row.status == "error"
    assert row.image is None


@pytest.mark.asyncio
async def test_runs_once_when_row_exists(session_factory, monkeypatch):
    monkeypatch.setattr(image_agent, "SessionLocal", session_factory)
    monkeypatch.setattr(image_agent.settings, "background_image_enabled", True)
    _mock_scene(monkeypatch, destination="Lisbon")

    calls = 0

    async def _count(prompt):
        nonlocal calls
        calls += 1
        return (b"IMG", "image/webp")

    monkeypatch.setattr(image_agent, "_generate_image", _count)

    await generate_trip_background("trip-4", "Plan Lisbon", UserPreferences())
    # Second (non-forced) invocation should short-circuit on the existing row.
    await generate_trip_background("trip-4", "Plan Lisbon again", UserPreferences())

    assert calls == 1


@pytest.mark.asyncio
async def test_disabled_flag_is_noop(session_factory, monkeypatch):
    monkeypatch.setattr(image_agent, "SessionLocal", session_factory)
    monkeypatch.setattr(image_agent.settings, "background_image_enabled", False)
    _mock_scene(monkeypatch, destination="Oslo")

    await generate_trip_background("trip-5", "Plan Oslo", UserPreferences())

    repo = SqliteTripBackgroundRepository(session_factory)
    assert await repo.get("trip-5") is None
