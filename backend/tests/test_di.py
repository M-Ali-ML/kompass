import pytest
from app.agent.dependency import get_agent_dependencies, AgentDependencies
from app.ports.math_service import MathServicePort

def test_dependency_injection_resolution():
    deps = get_agent_dependencies()
    
    assert isinstance(deps, AgentDependencies)
    assert isinstance(deps.math_service, MathServicePort)
