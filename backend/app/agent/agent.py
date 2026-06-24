import logging
from datetime import datetime
from typing import Union
from pydantic_ai import Agent, RunContext
from app.config import settings
from app.agent.dependency import AgentDependencies
from app.domain import Scenario, UserPreferences

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

@kompass_agent.tool
def gather_preferences(ctx: RunContext[AgentDependencies], preferences: UserPreferences) -> str:
    """Extract and register traveler preferences.
    
    Call this tool when the user specifies preferences like direct flights, vibe tags,
    hotel standards, or transport modes. Do not call this tool with empty parameters.
    """
    ctx.deps.user_preferences = preferences
    logger.info(f"Gathered user preferences: {preferences}")
    return f"Successfully gathered user preferences: {preferences}"

@kompass_agent.system_prompt(dynamic=True)
def get_system_prompt(ctx: RunContext[AgentDependencies]) -> str:
    """Dynamically loads system prompt from the injected service and formats current context."""
    logger.info("Generating dynamic system prompt for agent run.")
    raw_prompt = ctx.deps.prompt_service.get_prompt("system_prompt")
    # Get current local timezone-aware timestamp
    current_time_str = datetime.now().astimezone().isoformat()
    logger.info(f"Injected current time context: {current_time_str}")
    logger.info(f"Active user preferences in run dependencies: {ctx.deps.user_preferences}")
    return raw_prompt.replace("{current_time}", current_time_str)


