"""FastAPI dependency providers for the HTTP layer.

The route handlers depend on the persistence *ports* (the abstract repository
interfaces) and let FastAPI inject a concrete adapter via ``Depends``. This keeps
the driving adapter (the API) decoupled from the SQLite implementations — the
concrete wiring lives here, the single composition root for HTTP requests — and
makes every repository trivially overridable in tests through
``app.dependency_overrides``.
"""
from app.adapters.sqlite_saved_scenario_repository import SqliteSavedScenarioRepository
from app.adapters.sqlite_trip_background_repository import SqliteTripBackgroundRepository
from app.adapters.sqlite_trip_repository import SqliteTripRepository
from app.adapters.sqlite_user_profile_repository import SqliteUserProfileRepository
from app.db import SessionLocal
from app.ports.saved_scenario_repository import SavedScenarioRepository
from app.ports.trip_background_repository import TripBackgroundRepository
from app.ports.trip_repository import TripRepository
from app.ports.user_profile_repository import UserProfileRepository


def get_trip_repository() -> TripRepository:
    return SqliteTripRepository(SessionLocal)


def get_trip_background_repository() -> TripBackgroundRepository:
    return SqliteTripBackgroundRepository(SessionLocal)


def get_profile_repository() -> UserProfileRepository:
    return SqliteUserProfileRepository(SessionLocal)


def get_saved_scenario_repository() -> SavedScenarioRepository:
    return SqliteSavedScenarioRepository(SessionLocal)
