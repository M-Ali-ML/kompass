import os
from dataclasses import dataclass, field
from app.ports.prompt_service import PromptServicePort
from app.adapters.file_prompt_service import FilePromptService
from app.domain.user_preferences import UserPreferences

@dataclass
class AgentDependencies:
    """Dependencies for the Kompass travel agent."""
    prompt_service: PromptServicePort
    user_preferences: UserPreferences = field(default_factory=UserPreferences)

def get_agent_dependencies(user_preferences: UserPreferences | None = None) -> AgentDependencies:
    # Resolve the absolute path of backend/app/agent/prompts
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompts_dir = os.path.join(current_dir, "prompts")
    
    return AgentDependencies(
        prompt_service=FilePromptService(prompts_dir),
        user_preferences=user_preferences or UserPreferences()
    )

