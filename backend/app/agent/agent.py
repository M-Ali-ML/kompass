import os
from dotenv import load_dotenv
load_dotenv()

from pydantic_ai import Agent, RunContext
from app.domain.models import ScenarioMatrix
from app.agent.dependency import AgentDependencies

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
        "Return a precise ScenarioMatrix comparing at least 2 itinerary plans."
    )
)

@kompass_agent.tool
async def check_flights(ctx: RunContext[AgentDependencies], origin: str, destination: str, date: str) -> str:
    """Use this tool to find live flight pricing and schedules."""
    flights = await ctx.deps.flight_service.search_flights(origin, destination, date)
    return f"Found {len(flights)} flights. Top flight: {flights[0].airline} ${flights[0].price_usd}" if flights else "No flights found."

@kompass_agent.tool
async def check_stays(ctx: RunContext[AgentDependencies], location: str, check_in: str, check_out: str) -> str:
    """Use this tool to find accommodations and hotel pricing."""
    stays = await ctx.deps.stay_service.search_stays(location, check_in, check_out)
    return f"Found {len(stays)} stays. Top stay: {stays[0].name} ${stays[0].total_price_usd}" if stays else "No stays found."

@kompass_agent.tool
async def web_search(ctx: RunContext[AgentDependencies], query: str) -> str:
    """Use this tool to search the web for attractions, general knowledge, or booking links."""
    return await ctx.deps.search_service.search_web(query)
