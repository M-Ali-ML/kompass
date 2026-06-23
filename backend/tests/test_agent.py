import pytest
from pydantic_ai import RunContext
from pydantic_ai.models.test import TestModel
from app.agent.agent import kompass_agent, calculate_sum
from app.agent.dependency import AgentDependencies
from app.ports.math_service import MathServicePort
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_dependencies():
    deps = MagicMock(spec=AgentDependencies)
    deps.math_service = MagicMock(spec=MathServicePort)
    return deps

@pytest.mark.asyncio
async def test_calculate_sum_tool(mock_dependencies):
    mock_dependencies.math_service.add = AsyncMock(return_value=42)
    
    ctx = RunContext(
        agent=kompass_agent,
        deps=mock_dependencies,
        model=TestModel(),
        usage=None,
        prompt="Test Prompt"
    )
    
    result = await calculate_sum(ctx, 15, 27)
    assert result == 42
    mock_dependencies.math_service.add.assert_called_once_with(15, 27)

@pytest.mark.asyncio
async def test_agent_structured_response(mock_dependencies):
    # Set up custom response for TestModel to return mock text output
    test_model = TestModel(custom_output_text="The sum is 42")
    
    result = await kompass_agent.run(
        "What is 15 + 27?",
        deps=mock_dependencies,
        model=test_model
    )
    
    assert result.output == "The sum is 42"
