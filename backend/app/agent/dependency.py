import os
from dataclasses import dataclass, field

from app.adapters.file_prompt_service import FilePromptService
from app.adapters.mcp_flight_service import flight_service
from app.adapters.sqlite_trip_repository import SqliteTripRepository
from app.adapters.sqlite_user_profile_repository import SqliteUserProfileRepository
from app.db import SessionLocal
from app.domain.user_preferences import UserPreferences
from app.ports.flight_service import FlightServicePort
from app.ports.prompt_service import PromptServicePort
from app.ports.trip_repository import TripRepository
from app.ports.user_profile_repository import UserProfileRepository


@dataclass
class AgentDependencies:
    """Dependencies for the Kompass travel agent."""
    prompt_service: PromptServicePort
    user_preferences: UserPreferences = field(default_factory=UserPreferences)
    trip_repository: TripRepository | None = None
    profile_repository: UserProfileRepository | None = None
    flight_service: FlightServicePort | None = None
    trip_id: str | None = None
    # Bounds how many times generate_scenarios may reject for an incomplete
    # day-by-day plan within a single run, so enforcement can't loop forever.
    day_validation_retries: int = 0


def get_agent_dependencies(
    user_preferences: UserPreferences | None = None,
    trip_id: str | None = None,
) -> AgentDependencies:
    # Resolve the absolute path of backend/app/agent/prompts
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompts_dir = os.path.join(current_dir, "prompts")

    return AgentDependencies(
        prompt_service=FilePromptService(prompts_dir),
        user_preferences=user_preferences or UserPreferences(),
        trip_repository=SqliteTripRepository(SessionLocal),
        profile_repository=SqliteUserProfileRepository(SessionLocal),
        flight_service=flight_service,
        trip_id=trip_id,
    )
