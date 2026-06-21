import pytest
from pydantic_ai import RunContext
from pydantic_ai.models.test import TestModel
from app.agent.agent import kompass_agent, check_flights, check_stays, web_search, run_kompass_agent, handle_chat_session
from app.agent.dependency import AgentDependencies
from app.domain.models import ScenarioMatrix, ItineraryScenario
from app.ports.flight_service import FlightServicePort
from app.ports.stay_service import StayServicePort
from app.ports.search_service import SearchServicePort
from app.ports.repository import TripRepositoryPort
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def mock_dependencies():
    deps = MagicMock(spec=AgentDependencies)
    deps.flight_service = MagicMock(spec=FlightServicePort)
    deps.stay_service = MagicMock(spec=StayServicePort)
    deps.search_service = MagicMock(spec=SearchServicePort)
    deps.repository = MagicMock(spec=TripRepositoryPort)
    deps.session_id = "test_session_id"
    return deps

@pytest.mark.asyncio
async def test_check_flights_tool(mock_dependencies):
    # Setup mock return value
    mock_flight = MagicMock()
    mock_flight.airline = "Mock Air"
    mock_flight.price_usd = 299.0
    mock_dependencies.flight_service.search_flights = AsyncMock(return_value=[mock_flight])
    
    ctx = RunContext(
        agent=kompass_agent,
        deps=mock_dependencies,
        model=TestModel(),
        usage=None,
        prompt="Test Prompt"
    )
    
    result = await check_flights(ctx, "NYC", "LAX", "2026-07-01")
    assert "Mock Air" in result
    assert "$299" in result
    mock_dependencies.flight_service.search_flights.assert_called_once_with("NYC", "LAX", "2026-07-01")

@pytest.mark.asyncio
async def test_check_stays_tool(mock_dependencies):
    mock_stay = MagicMock()
    mock_stay.name = "Cozy Inn"
    mock_stay.total_price_usd = 450.0
    mock_dependencies.stay_service.search_stays = AsyncMock(return_value=[mock_stay])
    
    ctx = RunContext(
        agent=kompass_agent,
        deps=mock_dependencies,
        model=TestModel(),
        usage=None,
        prompt="Test Prompt"
    )
    
    result = await check_stays(ctx, "Ubud", "2026-07-01", "2026-07-05")
    assert "Cozy Inn" in result
    assert "$450" in result
    mock_dependencies.stay_service.search_stays.assert_called_once_with("Ubud", "2026-07-01", "2026-07-05")

@pytest.mark.asyncio
async def test_web_search_tool(mock_dependencies):
    mock_dependencies.search_service.search_web = AsyncMock(return_value="search results snippet")
    
    ctx = RunContext(
        agent=kompass_agent,
        deps=mock_dependencies,
        model=TestModel(),
        usage=None,
        prompt="Test Prompt"
    )
    
    result = await web_search(ctx, "best cafes Ubud")
    assert result == "search results snippet"
    mock_dependencies.search_service.search_web.assert_called_once_with("best cafes Ubud")

@pytest.mark.asyncio
async def test_agent_structured_response(mock_dependencies):
    # Set up a mock custom response for TestModel to return a valid ScenarioMatrix
    expected_matrix = ScenarioMatrix(
        scenarios=[
            ItineraryScenario(
                scenario_id="sc1",
                title="Mock Plan",
                summary="Summary text",
                transportation_subtotal_usd=100.0,
                accommodation_subtotal_usd=200.0,
                grand_total_usd=300.0,
                stress_score=2,
                flights=[],
                stays=[],
                itinerary=[]
            )
        ],
        active_constraints=["$500 budget"]
    )
    
    # In PydanticAI, we can pass custom model responses via TestModel:
    test_model = TestModel(custom_output_args=expected_matrix)
    
    result = await kompass_agent.run(
        "Generate a trip plan for NYC",
        deps=mock_dependencies,
        model=test_model
    )
    
    assert isinstance(result.output, ScenarioMatrix)
    assert len(result.output.scenarios) == 1
    assert result.output.scenarios[0].title == "Mock Plan"
    assert result.output.active_constraints == ["$500 budget"]


@pytest.mark.asyncio
async def test_run_kompass_agent(mock_dependencies):
    expected_matrix = ScenarioMatrix(
        scenarios=[
            ItineraryScenario(
                scenario_id="sc1",
                title="Mock Plan",
                summary="Summary text",
                transportation_subtotal_usd=100.0,
                accommodation_subtotal_usd=200.0,
                grand_total_usd=300.0,
                stress_score=2,
                flights=[],
                stays=[],
                itinerary=[]
            )
        ],
        active_constraints=["$500 budget"]
    )
    
    test_model = TestModel(custom_output_args=expected_matrix)
    
    output = await run_kompass_agent(
        "Generate a trip plan for NYC",
        deps=mock_dependencies,
        model=test_model
    )
    
    assert isinstance(output, ScenarioMatrix)
    assert len(output.scenarios) == 1
    assert output.scenarios[0].title == "Mock Plan"
    assert output.active_constraints == ["$500 budget"]


@pytest.mark.asyncio
@patch("app.agent.agent.get_agent_dependencies")
async def test_handle_chat_session(mock_get_deps, mock_dependencies):
    mock_get_deps.return_value = mock_dependencies
    mock_dependencies.repository.append_message = AsyncMock()
    mock_dependencies.repository.save_scenario_matrix = AsyncMock()
    
    expected_matrix = ScenarioMatrix(
        scenarios=[
            ItineraryScenario(
                scenario_id="sc1",
                title="Mock Plan",
                summary="Summary text",
                transportation_subtotal_usd=100.0,
                accommodation_subtotal_usd=200.0,
                grand_total_usd=300.0,
                stress_score=2,
                flights=[],
                stays=[],
                itinerary=[]
            )
        ],
        active_constraints=["$500 budget"]
    )
    
    test_model = TestModel(custom_output_args=expected_matrix)
    
    output = await handle_chat_session(
        session_id="test_session_id",
        user_prompt="Generate a trip plan for NYC",
        model=test_model
    )
    
    assert isinstance(output, ScenarioMatrix)
    assert len(output.scenarios) == 1
    assert output.scenarios[0].title == "Mock Plan"
    
    mock_get_deps.assert_called_once_with("test_session_id")
    mock_dependencies.repository.append_message.assert_any_call("test_session_id", "user", "Generate a trip plan for NYC")
    mock_dependencies.repository.save_scenario_matrix.assert_called_once_with("test_session_id", expected_matrix)
    mock_dependencies.repository.append_message.assert_any_call("test_session_id", "agent", expected_matrix.model_dump_json())
