import logging
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from app.config import settings
from app.agent.dependency import AgentDependencies, get_agent_dependencies

logger = logging.getLogger("kompass.agent")

# Load the LLM model from settings
llm_model = settings.llm_model


# Define the PydanticAI Agent
kompass_agent = Agent(
    llm_model,
    deps_type=AgentDependencies,
    model_settings={'thinking': True},
    system_prompt=(
        "You are a precise mathematical assistant. "
        "Use the calculate_sum tool to add numbers whenever the user asks you to perform addition. "
        "Respond with a clear explanation of the result."
    )
)

@kompass_agent.tool
async def calculate_sum(ctx: RunContext[AgentDependencies], a: int, b: int) -> int:
    """Use this tool to calculate the sum of two integers, a and b."""
    logger.info(f"calculate_sum tool called: a={a}, b={b}")
    return await ctx.deps.math_service.add(a, b)
