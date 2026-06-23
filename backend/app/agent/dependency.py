from dataclasses import dataclass
from app.ports.math_service import MathServicePort
from app.adapters.mcp_math_service import mcp_service

@dataclass
class AgentDependencies:
    math_service: MathServicePort

def get_agent_dependencies() -> AgentDependencies:
    return AgentDependencies(
        math_service=mcp_service
    )

