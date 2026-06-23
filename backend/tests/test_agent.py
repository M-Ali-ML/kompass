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
                    "activities": ["Arrive and check in", "Evening walk in Plaka"],
                    "description": "Welcome to Athens!"
                }
            ]
        },
        "total_cost": 950.0,
        "stress_score": 1,
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
    assert result.output.total_cost == 950.0
    assert result.output.stress_score == 1
