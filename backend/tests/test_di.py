import pytest
from app.agent.dependency import get_agent_dependencies, AgentDependencies
from app.ports.prompt_service import PromptServicePort

def test_dependency_injection_resolution():
    deps = get_agent_dependencies()
    assert isinstance(deps, AgentDependencies)
    assert isinstance(deps.prompt_service, PromptServicePort)
