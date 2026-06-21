import os
import logging
from dotenv import load_dotenv
load_dotenv()

from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model
from pydantic_ai.usage import UsageLimits
from app.domain.models import ScenarioMatrix
from app.agent.dependency import AgentDependencies, get_agent_dependencies

logger = logging.getLogger("kompass.agent")

# Load the LLM model from the environment variable (default: google:gemini-2.5-flash)
llm_model = os.getenv("LLM_MODEL", "google:gemini-2.5-flash")

# Define the PydanticAI Agent
kompass_agent = Agent(
    llm_model,
    deps_type=AgentDependencies,
    output_type=ScenarioMatrix,
    system_prompt=(
        "You are Kompass, an autonomous AI travel architect. "
        "Your personality is bold, fun, energetic, and precise (Joyful Pop vibe). "
        "You generate fully integrated, logically optimized travel itineraries and scenarios. "
        "Use the tools provided to check flights, stays, and general web information before responding. "
        "Do not call tools repeatedly in a loop. Perform at most 1 web search, 1 flight check, and 1 stay check. "
        "If the search results returned by the tools are high-level or generic mock data, treat them as sufficient and do not try to search again to refine them. "
        "Proceed directly to outputting the final ScenarioMatrix comparing at least 2 itinerary plans."
    )
)

@kompass_agent.tool
async def check_flights(ctx: RunContext[AgentDependencies], origin: str, destination: str, date: str) -> str:
    """Use this tool to find live flight pricing and schedules."""
    logger.info(f"check_flights tool called: origin={origin}, destination={destination}, date={date}")
    flights = await ctx.deps.flight_service.search_flights(origin, destination, date)
    result = f"Found {len(flights)} flights. Top flight: {flights[0].airline} ${flights[0].price_usd}" if flights else "No flights found."
    logger.info(f"check_flights result: {result}")
    return result

@kompass_agent.tool
async def check_stays(ctx: RunContext[AgentDependencies], location: str, check_in: str, check_out: str) -> str:
    """Use this tool to find accommodations and hotel pricing."""
    logger.info(f"check_stays tool called: location={location}, check_in={check_in}, check_out={check_out}")
    stays = await ctx.deps.stay_service.search_stays(location, check_in, check_out)
    result = f"Found {len(stays)} stays. Top stay: {stays[0].name} ${stays[0].total_price_usd}" if stays else "No stays found."
    logger.info(f"check_stays result: {result}")
    return result

@kompass_agent.tool
async def web_search(ctx: RunContext[AgentDependencies], query: str) -> str:
    """Use this tool to search the web for attractions, general knowledge, or booking links."""
    logger.info(f"web_search tool called: query={query}")
    result = await ctx.deps.search_service.search_web(query)
    logger.info(f"web_search result: {result[:100]}...")
    return result

async def run_kompass_agent(
    user_prompt: str,
    deps: AgentDependencies,
    model: Model | str | None = None
) -> ScenarioMatrix:
    """Run the Kompass travel agent with a limit on LLM requests and tool calls to prevent loops."""
    result = await kompass_agent.run(
        user_prompt,
        deps=deps,
        usage_limits=UsageLimits(request_limit=3, tool_calls_limit=5),
        model=model
    )
    return result.output


async def handle_chat_session(
    session_id: str,
    user_prompt: str,
    model: Model | str | None = None
) -> ScenarioMatrix:
    """
    Orchestrate a chat session:
    1. Get agent dependencies for the session.
    2. Save user message.
    3. Run agent.
    4. Save generated scenario matrix.
    5. Save agent response message.
    6. Return the scenario matrix.
    """
    deps = get_agent_dependencies(session_id)
    await deps.repository.append_message(session_id, "user", user_prompt)
    
    scenario_matrix = await run_kompass_agent(user_prompt, deps=deps, model=model)
    
    await deps.repository.save_scenario_matrix(session_id, scenario_matrix)
    await deps.repository.append_message(session_id, "agent", scenario_matrix.model_dump_json())
    
    return scenario_matrix
