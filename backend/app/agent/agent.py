import os
import logging
from dotenv import load_dotenv
load_dotenv()

from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model
from pydantic_ai.usage import UsageLimits
from app.agent.dependency import AgentDependencies, get_agent_dependencies

logger = logging.getLogger("kompass.agent")

# Load the LLM model from the environment variable (default: google:gemini-2.5-flash)
llm_model = os.getenv("LLM_MODEL", "google:gemini-2.5-flash")

# Define the PydanticAI Agent
kompass_agent = Agent(
    llm_model,
    deps_type=AgentDependencies,
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

async def run_kompass_agent(
    user_prompt: str,
    deps: AgentDependencies,
    model: Model | str | None = None
) -> str:
    """Run the Kompass agent with a limit on LLM requests and tool calls."""
    if os.getenv("LLM_MODEL") == "test":
        logger.info("Running in mock TEST model mode.")
        import re
        match = re.search(r"(\d+)\s*\+\s*(\d+)", user_prompt)
        if match:
            a, b = int(match.group(1)), int(match.group(2))
            res = await deps.math_service.add(a, b)
            return f"The sum of {a} and {b} is {res}."
        return "I can only help you add numbers."

    result = await kompass_agent.run(
        user_prompt,
        deps=deps,
        usage_limits=UsageLimits(request_limit=3, tool_calls_limit=5),
        model=model
    )
    return result.output

async def handle_chat_session(
    user_prompt: str,
    model: Model | str | None = None
) -> str:
    """Orchestrate a stateless chat session:
    1. Get agent dependencies.
    2. Run the agent.
    3. Return the response string.
    """
    deps = get_agent_dependencies()
    return await run_kompass_agent(user_prompt, deps=deps, model=model)
