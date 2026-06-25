import calendar
import logging
from datetime import date, datetime
from typing import Union
from pydantic_ai import Agent, RunContext
from app.config import settings
from app.agent.dependency import AgentDependencies
from app.agent.research_agent import run_research
from app.domain import Scenario, UserPreferences

logger = logging.getLogger("kompass.agent")

_MONTH_NAMES = {name.lower(): num for num, name in enumerate(calendar.month_name) if name}
_MONTH_NAMES.update({name.lower(): num for num, name in enumerate(calendar.month_abbr) if name})


def _month_to_range(month: str) -> tuple[str, str]:
    """Convert a 'YYYY-MM', 'YYYY-MM-DD', or month name into a (date_from, date_to) pair.

    Month names without a year resolve to the next upcoming occurrence so that
    "September" asked in October targets next year.
    """
    raw = (month or "").strip()
    today = date.today()

    # Explicit ISO date → search from that day through end of its month.
    parts = raw.split("-")
    if len(parts) >= 3 and all(p.isdigit() for p in parts[:3]):
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        last = calendar.monthrange(y, m)[1]
        return date(y, m, d).isoformat(), date(y, m, last).isoformat()

    # YYYY-MM → the whole month.
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        y, m = int(parts[0]), int(parts[1])
    else:
        # Bare month name (optionally with a year).
        tokens = raw.lower().replace(",", " ").split()
        m = next((_MONTH_NAMES[t] for t in tokens if t in _MONTH_NAMES), today.month)
        year_token = next((int(t) for t in tokens if t.isdigit() and len(t) == 4), None)
        y = year_token if year_token else (today.year if m >= today.month else today.year + 1)

    m = max(1, min(12, m))
    last = calendar.monthrange(y, m)[1]
    return date(y, m, 1).isoformat(), date(y, m, last).isoformat()

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
async def gather_preferences(ctx: RunContext[AgentDependencies], preferences: UserPreferences) -> str:
    """Extract and register traveler preferences.
    
    Call this tool when the user specifies preferences like direct flights, vibe tags,
    hotel standards, or transport modes. Do not call this tool with empty parameters.
    """
    # Layer the freshly stated preferences on top of the existing baseline
    # (global profile + anything gathered earlier this conversation).
    merged = ctx.deps.user_preferences.merged_with(preferences)
    ctx.deps.user_preferences = merged
    logger.info(f"Gathered user preferences: {merged}")

    # Persist to the global profile so preferences carry across future trips.
    if ctx.deps.profile_repository is not None:
        try:
            await ctx.deps.profile_repository.save_preferences(merged)
        except Exception as e:
            logger.error(f"Failed to persist user profile: {e}")

    return f"Successfully gathered user preferences: {merged}"


@kompass_agent.tool
async def find_cheapest_dates(
    ctx: RunContext[AgentDependencies],
    origin: str,
    destination: str,
    month: str,
    duration_days: int | None = None,
) -> dict:
    """Find the cheapest travel-date windows for a route within a month.

    Use this when the traveler's dates are flexible (e.g. "cheapest dates to fly
    to Athens in September"). Prices reflect the traveler's preferred currency.

    Args:
        origin: Departure airport IATA code (e.g. 'BER').
        destination: Arrival airport IATA code (e.g. 'ATH').
        month: Target month as 'YYYY-MM' (preferred) or a month name.
        duration_days: Trip length for round-trip pricing; omit for one-way.
    """
    if ctx.deps.flight_service is None:
        return {"error": "Flight search is unavailable.", "options": []}

    currency = ctx.deps.user_preferences.currency
    date_from, date_to = _month_to_range(month)
    logger.info(
        f"find_cheapest_dates {origin}->{destination} {date_from}..{date_to} "
        f"duration={duration_days} currency={currency}"
    )
    options = await ctx.deps.flight_service.find_cheapest_dates(
        origin,
        destination,
        date_from=date_from,
        date_to=date_to,
        duration_days=duration_days,
        currency=currency,
    )
    estimated = bool(options) and all(o.estimated for o in options)
    return {
        "currency": currency,
        "estimated": estimated,
        "options": [o.model_dump() for o in options],
    }


@kompass_agent.tool
async def search_flights(
    ctx: RunContext[AgentDependencies],
    origin: str,
    destination: str,
    departure_date: str,
    passengers: int = 1,
    max_stops: int | None = None,
    preferred_time: str | None = None,
) -> dict:
    """Search live one-way flight options for a specific date.

    Use this once dates are known to attach real prices, times, and layover
    counts to an itinerary leg. Prices reflect the traveler's preferred currency.

    Args:
        origin: Departure airport IATA code (e.g. 'BER').
        destination: Arrival airport IATA code (e.g. 'ATH').
        departure_date: Outbound date in 'YYYY-MM-DD' format.
        passengers: Number of adult passengers.
        max_stops: Maximum stops (0 = direct only). Omit for no limit.
        preferred_time: Departure window as 'HH-HH' (e.g. '6-20'); optional.
    """
    if ctx.deps.flight_service is None:
        return {"error": "Flight search is unavailable.", "options": []}

    prefs = ctx.deps.user_preferences
    currency = prefs.currency
    # Honor a strict direct-flights preference unless the caller is more specific.
    if max_stops is None and prefs.direct_flights_only:
        max_stops = 0
    logger.info(
        f"search_flights {origin}->{destination} {departure_date} pax={passengers} "
        f"max_stops={max_stops} currency={currency}"
    )
    options = await ctx.deps.flight_service.search_flights(
        origin,
        destination,
        departure_date,
        passengers=passengers,
        max_stops=max_stops,
        preferred_time=preferred_time,
        currency=currency,
    )
    estimated = bool(options) and all(o.estimated for o in options)
    return {
        "currency": currency,
        "estimated": estimated,
        "options": [o.model_dump() for o in options],
    }


@kompass_agent.tool
async def search_web(ctx: RunContext[AgentDependencies], query: str) -> str:
    """Search the live web (Google) for current, real-world travel information.

    This is the most reliable source of live data. Use it for:
    - Flight price ranges, example carriers, and good dates for a route.
    - Accommodation options (hotels/areas, nightly prices, ratings).
    - Destination knowledge: best time to visit, weather, neighborhoods, visas, events.

    Prefer this when you need real prices or facts. The returned text is
    grounded in web results — extract concrete numbers from it into your plan,
    and tell the traveler figures are approximate.

    Args:
        query: A focused natural-language search query (include dates, origin/
            destination cities, and any constraints).
    """
    currency = ctx.deps.user_preferences.currency
    full_query = f"{query}\n\n(Report any prices in {currency}.)"
    logger.info(f"search_web query: {full_query!r}")
    return await run_research(full_query)


@kompass_agent.tool
async def generate_scenarios(
    ctx: RunContext[AgentDependencies],
    destination: str,
    scenarios: list[Scenario],
    estimated: bool = False,
) -> dict:
    """Present 2-3 fully-formed travel scenarios for side-by-side comparison.

    Build each `Scenario` yourself first — research real prices and dates with
    `search_web` / `find_cheapest_dates` / `search_flights`, assemble the
    itineraries, compute each `cost_breakdown`, and assess each `stress_score`
    from its `stress_factors`. Then call this tool **once** with the complete
    list to render a comparison view. Provide 2 or 3 scenarios that differ on
    date window, price, and/or stress so the traveler has a meaningful choice.

    Args:
        destination: The destination being compared (e.g. 'Santorini').
        scenarios: The complete list of 2-3 `Scenario` objects to compare.
        estimated: True if any prices are approximate because live data was
            unavailable (surfaces an "≈ approx" badge to the traveler).
    """
    # The comparison view is only meaningful with at least two options. Reject a
    # single scenario with a corrective message so the agent re-calls once with
    # the full set rather than rendering a lone card.
    if len(scenarios) < 2:
        logger.warning(
            f"generate_scenarios called with {len(scenarios)} scenario(s); requesting 2-3."
        )
        return {
            "error": (
                f"generate_scenarios needs 2-3 distinct scenarios for a side-by-side "
                f"comparison, but you provided {len(scenarios)}. Re-call this tool ONCE "
                "with 2 or 3 scenarios that differ on date window, price, and/or stress."
            ),
            "scenarios": [],
        }

    currency = ctx.deps.user_preferences.currency
    # Keep the displayed math self-consistent: the grand total is always the
    # sum of its parts, regardless of what the model put in the field.
    for s in scenarios:
        cb = s.cost_breakdown
        cb.grand_total = round(cb.transportation + cb.accommodation, 2)
    logger.info(
        f"generate_scenarios destination={destination!r} count={len(scenarios)} "
        f"currency={currency} estimated={estimated}"
    )
    return {
        "destination": destination,
        "currency": currency,
        "estimated": estimated,
        "scenarios": [s.model_dump(mode="json") for s in scenarios],
    }


@kompass_agent.system_prompt(dynamic=True)
def get_system_prompt(ctx: RunContext[AgentDependencies]) -> str:
    """Dynamically loads system prompt from the injected service and formats current context."""
    logger.info("Generating dynamic system prompt for agent run.")
    raw_prompt = ctx.deps.prompt_service.get_prompt("system_prompt")
    # Inject the current date only (not a per-second timestamp). A timestamp
    # precise to the second changes on every turn and lives near the front of
    # the prompt, which would invalidate the LLM KV-cache for the whole prefix
    # on each request (see Manus "Design Around the KV-Cache"). Day-level
    # granularity is all the agent needs for seasonality/date reasoning while
    # keeping the prefix stable across a conversation.
    current_date_str = datetime.now().astimezone().strftime("%Y-%m-%d")
    logger.info(f"Injected current date context: {current_date_str}")
    logger.info(f"Active user preferences in run dependencies: {ctx.deps.user_preferences}")
    return raw_prompt.replace("{current_time}", current_date_str)


