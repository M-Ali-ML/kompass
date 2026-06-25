import pytest
import json
from typing import Any
from unittest.mock import MagicMock
from pydantic_ai.models.test import TestModel, _WrappedTextOutput
from pydantic_ai.models import ModelRequestParameters
from app.agent.agent import kompass_agent
from app.agent.dependency import AgentDependencies
from app.ports.prompt_service import PromptServicePort
from app.domain import Scenario

# Custom TestModel that allows plain text responses even when output_mode is 'tool'
# (which is the case when Agent output_type is Union[str, Scenario])
class UnionTestModel(TestModel):
    def _get_output(self, model_request_parameters: ModelRequestParameters) -> Any:
        if self.custom_output_text is not None:
            return _WrappedTextOutput(self.custom_output_text)
        return super()._get_output(model_request_parameters)

@pytest.fixture
def agent_deps():
    mock_prompt_service = MagicMock(spec=PromptServicePort)
    mock_prompt_service.get_prompt.return_value = "You are a travel planning assistant. Current Time: {current_time}"
    return AgentDependencies(prompt_service=mock_prompt_service)

@pytest.mark.asyncio
async def test_agent_conversational_response(agent_deps):
    # Set up UnionTestModel to return a conversational string
    test_model = UnionTestModel(custom_output_text="Where would you like to travel in Greece?")
    
    result = await kompass_agent.run(
        "Plan me a trip to Greece.",
        deps=agent_deps,
        model=test_model
    )
    
    assert result.output == "Where would you like to travel in Greece?"
    assert isinstance(result.output, str)

@pytest.mark.asyncio
async def test_agent_scenario_structured_response(agent_deps):
    # Mock Scenario dict matching the Pydantic schema
    mock_scenario_data = {
        "label": "Scenario A: Economy Greece Trip",
        "itinerary": {
            "legs": [
                {
                    "mode": "flight",
                    "origin": "BER",
                    "destination": "ATH",
                    "departure_time": "2026-09-10T10:00:00Z",
                    "arrival_time": "2026-09-10T12:30:00Z",
                    "carrier": "Ryanair FR123",
                    "cost": 150.0
                }
            ],
            "accommodations": [
                {
                    "name": "Athens Cozy Hotel",
                    "location": "Athens",
                    "check_in": "2026-09-10T14:00:00Z",
                    "check_out": "2026-09-20T11:00:00Z",
                    "cost": 800.0
                }
            ],
            "days": [
                {
                    "day_number": 1,
                    "title": "Arrival & Plaka Stroll",
                    "description": "Welcome to Athens!",
                    "schedule": [
                        {
                            "period": "Afternoon",
                            "activity": "Arrive and check in",
                            "location": "Athens",
                            "details": "Drop bags at the hotel and freshen up."
                        },
                        {
                            "period": "Evening",
                            "activity": "Evening walk in Plaka",
                            "location": "Plaka"
                        }
                    ]
                }
            ]
        },
        "comparison_label": "Early September",
        "start_date": "2026-09-10",
        "end_date": "2026-09-20",
        "cost_breakdown": {
            "transportation": 150.0,
            "accommodation": 800.0,
            "grand_total": 950.0,
        },
        "stress_score": 1,
        "stress_factors": {
            "layover_count": 0,
            "overnight_travel": False,
            "tight_connection": False,
            "total_travel_hours": 3.5,
        },
        "highlights": ["Direct flight", "Single hotel"],
        "reasoning_summary": "Direct flight and simple single accommodation makes this highly relaxed."
    }
    
    # We pass the data to custom_output_args so TestModel executes the output tool
    test_model = UnionTestModel(custom_output_args=mock_scenario_data)
    
    result = await kompass_agent.run(
        "Plan me a 10-day trip to Greece in September",
        deps=agent_deps,
        model=test_model
    )
    
    # Assert output is validated as a Scenario object
    assert isinstance(result.output, Scenario)
    assert result.output.label == "Scenario A: Economy Greece Trip"
    assert len(result.output.itinerary.legs) == 1
    assert result.output.itinerary.legs[0].origin == "BER"
    assert result.output.cost_breakdown.grand_total == 950.0
    assert result.output.stress_score == 1

@pytest.mark.asyncio
async def test_gather_preferences_tool(agent_deps):
    from app.agent.agent import gather_preferences
    from pydantic_ai import RunContext
    from app.domain import UserPreferences
    
    # We can invoke the tool directly using the function
    ctx = RunContext(
        deps=agent_deps,
        model=MagicMock(),
        usage=MagicMock(),
        prompt="test prompt"
    )
    
    prefs = UserPreferences(
        direct_flights_only=True,
        vibe_tags=["foodie", "relaxation"]
    )
    
    res = await gather_preferences(ctx, prefs)
    assert "Successfully gathered user preferences" in res
    assert agent_deps.user_preferences.direct_flights_only is True
    assert "foodie" in agent_deps.user_preferences.vibe_tags


def _make_scenario(label: str, transport: float, accom: float, claimed_total: float) -> Scenario:
    return Scenario(
        label=label,
        comparison_label=label,
        start_date="2026-09-04",
        end_date="2026-09-11",
        itinerary={"legs": [], "accommodations": [], "days": []},
        cost_breakdown={
            "transportation": transport,
            "accommodation": accom,
            # Intentionally wrong so the tool must normalize it.
            "grand_total": claimed_total,
        },
        stress_score=2,
        stress_factors={
            "layover_count": 1,
            "overnight_travel": False,
            "tight_connection": False,
            "total_travel_hours": 6.0,
        },
        highlights=["1 layover"],
        reasoning_summary="A balanced option.",
    )


@pytest.mark.asyncio
async def test_generate_scenarios_normalizes_totals_and_payload(agent_deps):
    from app.agent.agent import generate_scenarios
    from pydantic_ai import RunContext
    from app.domain import UserPreferences

    agent_deps.user_preferences = UserPreferences(currency="USD")
    # Isolate normalization from the day-completeness guard (covered separately).
    agent_deps.day_validation_retries = 1
    ctx = RunContext(deps=agent_deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    scenarios = [
        _make_scenario("Early September", 340.0, 900.0, claimed_total=0.0),
        _make_scenario("Late August", 480.0, 1200.0, claimed_total=999.0),
    ]

    payload = await generate_scenarios(ctx, "Santorini", scenarios, estimated=True)

    assert payload["destination"] == "Santorini"
    assert payload["currency"] == "USD"
    assert payload["estimated"] is True
    assert len(payload["scenarios"]) == 2
    # Grand totals are recomputed from their parts regardless of the input value.
    assert payload["scenarios"][0]["cost_breakdown"]["grand_total"] == 1240.0
    assert payload["scenarios"][1]["cost_breakdown"]["grand_total"] == 1680.0
    # Dates serialize as ISO strings for the frontend.
    assert payload["scenarios"][0]["start_date"] == "2026-09-04"


@pytest.mark.asyncio
async def test_generate_scenarios_rejects_single_scenario(agent_deps):
    from app.agent.agent import generate_scenarios
    from pydantic_ai import RunContext

    ctx = RunContext(deps=agent_deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    payload = await generate_scenarios(
        ctx, "Santorini", [_make_scenario("Only one", 300.0, 700.0, 1000.0)]
    )

    # A lone scenario is not a comparison: nothing renders and the agent is told
    # to re-call with 2-3.
    assert payload["scenarios"] == []
    assert "error" in payload
    assert "2-3" in payload["error"]


@pytest.mark.asyncio
async def test_generate_scenarios_rejects_incomplete_day_plan(agent_deps):
    from app.agent.agent import generate_scenarios
    from pydantic_ai import RunContext

    ctx = RunContext(deps=agent_deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    # Two valid scenarios but each spans a 7-night trip with no day-by-day plan.
    scenarios = [
        _make_scenario("Early September", 340.0, 900.0, 1240.0),
        _make_scenario("Late August", 480.0, 1200.0, 1680.0),
    ]

    payload = await generate_scenarios(ctx, "Santorini", scenarios)

    # The incomplete plan is rejected once with a corrective message...
    assert payload["scenarios"] == []
    assert "error" in payload
    assert "day" in payload["error"].lower()
    assert agent_deps.day_validation_retries == 1

    # ...but the guard only fires once per run, so a retry proceeds (and renders),
    # preventing an infinite correction loop even if the model can't comply.
    payload2 = await generate_scenarios(ctx, "Santorini", scenarios)
    assert len(payload2["scenarios"]) == 2

