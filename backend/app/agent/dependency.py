from dataclasses import dataclass
from app.ports.repository import TripRepositoryPort
from app.ports.flight_service import FlightServicePort
from app.ports.stay_service import StayServicePort
from app.ports.search_service import SearchServicePort
from app.adapters.db_sqlite import SQLiteTripRepository
from app.adapters.fli_flights import FliFlightService
from app.adapters.openbnb_stays import AirbnbStayService
from app.adapters.search_brave import BraveSearchService

@dataclass
class AgentDependencies:
    repository: TripRepositoryPort
    flight_service: FlightServicePort
    stay_service: StayServicePort
    search_service: SearchServicePort
    session_id: str

def get_agent_dependencies(session_id: str) -> AgentDependencies:
    return AgentDependencies(
        repository=SQLiteTripRepository(),
        flight_service=FliFlightService(),
        stay_service=AirbnbStayService(),
        search_service=BraveSearchService(),
        session_id=session_id
    )
