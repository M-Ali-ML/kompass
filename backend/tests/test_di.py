import pytest
from app.agent.dependency import get_agent_dependencies, AgentDependencies
from app.ports.repository import TripRepositoryPort
from app.ports.flight_service import FlightServicePort
from app.ports.stay_service import StayServicePort
from app.ports.search_service import SearchServicePort

def test_dependency_injection_resolution():
    session_id = "test_di_session"
    deps = get_agent_dependencies(session_id)
    
    assert isinstance(deps, AgentDependencies)
    assert deps.session_id == session_id
    
    # Check Ports compliance
    assert isinstance(deps.repository, TripRepositoryPort)
    assert isinstance(deps.flight_service, FlightServicePort)
    assert isinstance(deps.stay_service, StayServicePort)
    assert isinstance(deps.search_service, SearchServicePort)
