import logging
from datetime import datetime
from typing import Union
from pydantic_ai import Agent, RunContext
from app.config import settings
from app.agent.dependency import AgentDependencies
from app.domain import Scenario

logger = logging.getLogger("kompass.agent")

# Load the LLM model from settings
llm_model = settings.llm_model

# Define the PydanticAI Agent
kompass_agent = Agent(
    llm_model,
    deps_type=AgentDependencies,
    output_type=Union[str, Scenario],
    model_settings={'thinking': True},
)

@kompass_agent.system_prompt(dynamic=True)
def get_system_prompt(ctx: RunContext[AgentDependencies]) -> str:
    """Dynamically loads system prompt from the injected service and formats current context."""
    raw_prompt = ctx.deps.prompt_service.get_prompt("system_prompt")
    # Get current local timezone-aware timestamp
    current_time_str = datetime.now().astimezone().isoformat()
    return raw_prompt.replace("{current_time}", current_time_str)
