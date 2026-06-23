import os
from dataclasses import dataclass
from app.ports.prompt_service import PromptServicePort
from app.adapters.file_prompt_service import FilePromptService

@dataclass
class AgentDependencies:
    """Dependencies for the Kompass travel agent."""
    prompt_service: PromptServicePort

def get_agent_dependencies() -> AgentDependencies:
    # Resolve the absolute path of backend/app/agent/prompts
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompts_dir = os.path.join(current_dir, "prompts")
    
    return AgentDependencies(
        prompt_service=FilePromptService(prompts_dir)
    )
