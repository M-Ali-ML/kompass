"""HTTP route tests for the FastAPI layer.

These exercise the REST endpoints end-to-end (request → route handler → repository
→ SQLite) without touching the agent or the MCP subprocesses. Persistence ports
are overridden via ``app.dependency_overrides`` (the reason `app/api/dependencies.py`
exists) so each test runs against an isolated temp database.

The agent/MCP-driven ``/api/copilotkit`` endpoint is intentionally out of scope
here — it's covered by the agent/adapter unit tests.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.adapters.sqlite_saved_scenario_repository import SqliteSavedScenarioRepository
from app.adapters.sqlite_trip_repository import SqliteTripRepository
from app.adapters.sqlite_user_profile_repository import SqliteUserProfileRepository
from app.api.dependencies import (
    get_profile_repository,
    get_saved_scenario_repository,
    get_trip_repository,
)
from app.db import Base
from app.main import app


@pytest.fixture
def client(tmp_path):
    """A TestClient wired to isolated SQLite repositories.

    NullPool keeps every operation on a fresh connection so the schema (created
    here) and the per-request handlers (run on TestClient's own event loop) don't
    fight over a pooled connection bound to a closed loop. We deliberately do NOT
    enter TestClient as a context manager, so the app lifespan (which would start
    the flights/accommodations MCP subprocesses) never runs.
    """
    db_path = tmp_path / "routes_test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )

    async def _create_schema():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_schema())

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    app.dependency_overrides[get_trip_repository] = lambda: SqliteTripRepository(factory)
    app.dependency_overrides[get_profile_repository] = lambda: SqliteUserProfileRepository(factory)
    app.dependency_overrides[get_saved_scenario_repository] = (
        lambda: SqliteSavedScenarioRepository(factory)
    )

    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


# --- Health ------------------------------------------------------------------

def test_health_ok(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


# --- Profile -----------------------------------------------------------------

def test_get_profile_returns_defaults(client):
    res = client.get("/api/profile")
    assert res.status_code == 200
    body = res.json()
    assert body["direct_flights_only"] is False
    assert body["preferred_transit_modes"] == []
    assert body["hotel_class"] is None
    assert body["vibe_tags"] == []
    assert body["currency"] == "EUR"


def test_put_then_get_profile_round_trip(client):
    payload = {
        "direct_flights_only": True,
        "preferred_transit_modes": ["train", "ferry"],
        "hotel_class": "4-star",
        "vibe_tags": ["foodie", "relaxation"],
        "currency": "USD",
    }
    put = client.put("/api/profile", json=payload)
    assert put.status_code == 200
    assert put.json()["currency"] == "USD"

    got = client.get("/api/profile").json()
    assert got["direct_flights_only"] is True
    assert got["preferred_transit_modes"] == ["train", "ferry"]
    assert got["hotel_class"] == "4-star"
    assert got["vibe_tags"] == ["foodie", "relaxation"]
    assert got["currency"] == "USD"


def test_put_profile_applies_defaults_for_omitted_fields(client):
    # Empty body is valid — UserPreferences has defaults for every field.
    res = client.put("/api/profile", json={})
    assert res.status_code == 200
    assert res.json()["currency"] == "EUR"


# --- Trips -------------------------------------------------------------------

def test_trip_crud_flow(client):
    # Empty to start.
    assert client.get("/api/trips").json() == {"trips": []}

    created = client.post("/api/trips", json={"id": "thread-1", "title": "Trip to Greece"})
    assert created.status_code == 200
    assert created.json()["id"] == "thread-1"
    assert created.json()["title"] == "Trip to Greece"

    listed = client.get("/api/trips").json()["trips"]
    assert len(listed) == 1
    assert listed[0]["id"] == "thread-1"

    got = client.get("/api/trips/thread-1")
    assert got.status_code == 200
    body = got.json()
    assert body["title"] == "Trip to Greece"
    assert body["messages"] == []
    assert body["message_history"] == []

    deleted = client.delete("/api/trips/thread-1")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert client.get("/api/trips").json() == {"trips": []}


def test_create_trip_generates_id_when_omitted(client):
    created = client.post("/api/trips", json={"title": "Untitled"})
    assert created.status_code == 200
    assert created.json()["id"]  # a uuid was generated


def test_get_unknown_trip_returns_404(client):
    assert client.get("/api/trips/nope").status_code == 404


def test_save_message_history_round_trips_through_get(client):
    client.post("/api/trips", json={"id": "thread-x"})
    history = [
        {"id": "m1", "role": "user", "content": "Plan a trip to Egypt"},
        {"id": "m2", "role": "assistant", "content": "When are you going?"},
    ]
    res = client.put(
        "/api/trips/thread-x/messages",
        json={"messages": history, "title": "Plan a trip to Egypt"},
    )
    assert res.status_code == 200
    assert res.json()["count"] == 2

    got = client.get("/api/trips/thread-x").json()
    assert got["message_history"] == history
    assert got["title"] == "Plan a trip to Egypt"


# --- Saved scenarios ---------------------------------------------------------

def _sample_scenario():
    return {
        "label": "Express Flight & Coastal Hotel",
        "comparison_label": "Early September",
        "start_date": "2026-09-04",
        "end_date": "2026-09-11",
        "stress_score": 2,
        "cost_breakdown": {"transportation": 190, "accommodation": 1050, "grand_total": 1240},
        "itinerary": {"legs": [], "accommodations": [], "days": []},
    }


def test_saved_scenario_crud_and_trip_filter(client):
    assert client.get("/api/saved-scenarios").json() == {"saved": []}

    created = client.post(
        "/api/saved-scenarios",
        json={
            "scenario": _sample_scenario(),
            "trip_id": "thread-1",
            "destination": "Naples, Italy",
            "currency": "EUR",
        },
    )
    assert created.status_code == 200
    saved = created.json()
    assert saved["destination"] == "Naples, Italy"
    assert saved["grand_total"] == 1240
    assert saved["stress_score"] == 2
    saved_id = saved["id"]

    # Folded destination/currency are persisted into the scenario payload.
    assert saved["scenario"]["destination"] == "Naples, Italy"
    assert saved["scenario"]["currency"] == "EUR"

    # A second scenario on a different trip, to exercise the trip_id filter.
    client.post(
        "/api/saved-scenarios",
        json={"scenario": {"label": "Other"}, "trip_id": "thread-2", "destination": "Rome"},
    )

    assert len(client.get("/api/saved-scenarios").json()["saved"]) == 2
    only_t1 = client.get("/api/saved-scenarios?trip_id=thread-1").json()["saved"]
    assert len(only_t1) == 1
    assert only_t1[0]["destination"] == "Naples, Italy"

    got = client.get(f"/api/saved-scenarios/{saved_id}")
    assert got.status_code == 200
    assert got.json()["label"] == "Express Flight & Coastal Hotel"

    deleted = client.delete(f"/api/saved-scenarios/{saved_id}")
    assert deleted.status_code == 200
    assert client.get(f"/api/saved-scenarios/{saved_id}").status_code == 404


def test_get_unknown_saved_scenario_returns_404(client):
    assert client.get("/api/saved-scenarios/99999").status_code == 404
