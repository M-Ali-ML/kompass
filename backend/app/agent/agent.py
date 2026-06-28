import asyncio
import calendar
import logging
from collections import Counter
from datetime import date, datetime
from pydantic_ai import Agent, RunContext
from app.config import settings
from app.agent.dependency import AgentDependencies
from app.agent.image_agent import generate_trip_background
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


def _day_fingerprint(day) -> tuple:
    """A content signature for a DaySummary used to detect padded/placeholder days.

    Two days that share the same title, description, and ordered (period, activity)
    schedule are treated as identical — the tell-tale sign of filler days the model
    emits to satisfy a day count (e.g. "Return to Berlin" repeated three times).
    """
    return (
        (day.title or "").strip().lower(),
        (day.description or "").strip().lower(),
        tuple((p.period.strip().lower(), p.activity.strip().lower()) for p in day.schedule),
    )

# Load the LLM model from settings
llm_model = settings.llm_model

# Define the PydanticAI Agent
# The agent's own final output is ALWAYS plain text: travel plans are delivered
# through the `generate_scenarios` tool (which renders the scenario cards) and
# every other reply is conversational text. Keeping `output_type=str` — rather
# than a `Union[str, Scenario]` — avoids registering a second `final_result`
# output tool that would re-ship the full nested Scenario JSON schema (~2k
# tokens) on every request for a structured-output path the app never renders.
# `retries={'tools': 2}` covers tool-output validation (e.g. generate_scenarios
# re-calls on an incomplete day plan).
kompass_agent = Agent(
    llm_model,
    deps_type=AgentDependencies,
    output_type=str,
    retries={'tools': 2},
    # Low temperature for more deterministic, instruction-following behavior —
    # in particular, reliably calling `ask_clarifying_question` for concrete
    # questions rather than drifting into plain-text prose. (Merged with the
    # per-request `timeout` set on dispatch.)
    #
    # `thinking: False` disables Gemini's reasoning phase (maps to
    # thinking_budget=0 on gemini-2.5-flash). On a large final-synthesis context
    # the model would otherwise spend the whole request budget "thinking" and
    # return an empty completion with no first token, stalling the run.
    model_settings={'temperature': 0.2, 'thinking': False},
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
    Each call returns ONE direction — for a round trip, call it twice (once for
    the outbound date, once for the return date) and add a Leg for each.

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
    # Remember the largest party size searched this run so generate_scenarios can
    # backfill Scenario.travelers if the model leaves it at the default.
    ctx.deps.party_size = max(ctx.deps.party_size or 1, passengers)
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
async def search_accommodations(
    ctx: RunContext[AgentDependencies],
    destination: str,
    check_in_date: str,
    check_out_date: str,
    guests: int = 2,
    max_price: int | None = None,
    min_rating: float | None = None,
) -> dict:
    """Search live lodging options (hotels, rentals) for a stay via Google Hotels.

    Use this once a destination and stay dates are known to attach real nightly
    and total rates, ratings, and amenities to a scenario's accommodation. Feed
    the chosen option's `total_rate` into `cost_breakdown.accommodation`. Prices
    reflect the traveler's preferred currency.

    Args:
        destination: City / area to stay in (e.g. 'Santorini', 'Athens city center').
        check_in_date: Check-in date in 'YYYY-MM-DD' format.
        check_out_date: Check-out date in 'YYYY-MM-DD' format.
        guests: Number of adult guests.
        max_price: Optional maximum nightly rate (in the traveler's currency) to cap results.
        min_rating: Optional minimum guest rating (e.g. 4.0) to filter results.
    """
    if ctx.deps.accommodation_service is None:
        return {"error": "Accommodation search is unavailable.", "options": []}

    currency = ctx.deps.user_preferences.currency
    logger.info(
        f"search_accommodations {destination!r} {check_in_date}..{check_out_date} "
        f"guests={guests} max_price={max_price} min_rating={min_rating} currency={currency}"
    )
    options = await ctx.deps.accommodation_service.search_accommodations(
        destination,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        guests=guests,
        max_price=max_price,
        min_rating=min_rating,
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
async def search_ground_transport(
    ctx: RunContext[AgentDependencies],
    origin: str,
    destination: str,
    date: str,
    modes: str | None = None,
) -> str:
    """Research ground-transport options (train, bus, ferry) for a route and date.

    Use this for any non-flight leg — e.g. the onward hop after a flight ("fly to
    Athens, then ferry to Milos"), or a rail/bus journey between cities. It is the
    ground-transport counterpart to `search_flights`: it returns grounded,
    real-world info (operators, typical departure/arrival times, journey duration,
    frequency, and a fare range) so you can build a realistic `Leg` with the correct
    `mode`. Times and prices are approximate — present them as such.

    For a connection after a flight, pass the same `date` as the flight arrival and
    then align the onward `Leg.departure_time` to the flight `arrival_time` plus a
    realistic transfer buffer.

    Args:
        origin: Departure city/port/station (e.g. 'Piraeus', 'Athens').
        destination: Arrival city/port/station (e.g. 'Milos').
        date: Travel date in 'YYYY-MM-DD' format.
        modes: Optional comma-separated modes to focus on (e.g. 'ferry', 'train,bus').
    """
    currency = ctx.deps.user_preferences.currency
    mode_clause = f" by {modes}" if modes else " by train, bus, or ferry"
    query = (
        f"Ground transport options{mode_clause} from {origin} to {destination} on {date}. "
        "List the main operators, typical departure and arrival times, journey duration, "
        "how frequently they run, and a one-way fare range. Note if any service is overnight "
        "or seasonal.\n\n"
        f"(Report any prices in {currency}.)"
    )
    logger.info(f"search_ground_transport query: {query!r}")
    return await run_research(query)


@kompass_agent.tool
async def generate_scenarios(
    ctx: RunContext[AgentDependencies],
    destination: str,
    scenarios: list[Scenario],
    estimated: bool = False,
) -> dict:
    """Render fully-formed travel scenarios as cards (1 single plan, or 2-3 to compare).

    Build each `Scenario` yourself first — research real prices and dates with
    `search_web` / `find_cheapest_dates` / `search_flights`, assemble the
    itineraries, compute each `cost_breakdown`, and assess each `stress_score`
    from its `stress_factors`. Then call this tool **once** with the complete
    list. Pass a single scenario to present one definitive plan (renders as one
    card), or 2-3 scenarios that differ on date window, price, and/or stress
    when the traveler is choosing between options. ALWAYS deliver the plan
    through this tool — never type the itinerary out as text.

    Args:
        destination: The destination being planned/compared (e.g. 'Santorini').
        scenarios: The complete list of 1-3 `Scenario` objects to render.
        estimated: True if any prices are approximate because live data was
            unavailable (surfaces an "≈ approx" badge to the traveler).
    """
    # At least one scenario is required to render anything. (A single scenario is
    # valid — it renders as one card; 2-3 render side-by-side for comparison.)
    if not scenarios:
        logger.warning("generate_scenarios called with no scenarios.")
        return {
            "error": (
                "generate_scenarios needs at least one fully-built Scenario to render. "
                "Build the plan and call this tool again — never present it as text."
            ),
            "scenarios": [],
        }

    # Enforce a genuine, full day-by-day plan. Two failure modes to catch:
    #   1. Too few days — the model collapses a long trip into a couple of
    #      "highlight" days (a 12-day trip with 8 entries).
    #   2. Padded days — to satisfy a day count the model repeats identical
    #      filler entries (e.g. "Return to Berlin" three times).
    # Both checks apply in every mode: each day needs its own entry (count) and
    # every entry must be DISTINCT (no padding). Detail (how rich each day's
    # schedule is) is scaled to scenario count in the system prompt — full plans
    # for a single scenario, lighter skeletons for a 2-3 way comparison — but a
    # skeleton day is thinner, NOT a duplicate: it still needs a distinct title
    # and description, so the padding guard stays strict here regardless of mode.
    # When we DO reject a comparison, the error coaches the model that skeletons
    # are fine as long as each day is distinct. Bounded by `day_validation_retries`
    # (two corrections at most: one per mode, then accept whatever comes back).
    if ctx.deps.day_validation_retries < 2:
        comparison_mode = len(scenarios) > 1
        problems = []
        for s in scenarios:
            label = s.comparison_label or s.label
            nights = (s.end_date - s.start_date).days
            have = len(s.itinerary.days)
            # Allow a ±1 tolerance so a days-vs-nights off-by-one (e.g. 8 entries
            # for a 9-night window) doesn't trigger a full regeneration; only
            # reject when the plan is materially short of the trip span.
            if nights >= 3 and have < nights - 1:
                problems.append(f"'{label}' has only {have}/{nights} days")
                continue
            counts = Counter(_day_fingerprint(d) for d in s.itinerary.days)
            dup_titles = sorted(
                {(fp[0] or "untitled") for fp, c in counts.items() if c > 1}
            )
            if dup_titles:
                problems.append(
                    f"'{label}' repeats identical placeholder days ({', '.join(dup_titles)})"
                )
        if problems:
            ctx.deps.day_validation_retries += 1
            detail = "; ".join(problems)
            logger.warning(f"generate_scenarios rejected — day plan issues: {detail}")
            skeleton_note = (
                " For a side-by-side comparison the days can be light skeletons "
                "(distinct title + one-line description, schedule short or empty), "
                "but each day still needs its own DISTINCT entry — no repeats."
                if comparison_mode
                else ""
            )
            return {
                "error": (
                    "Each scenario needs one DISTINCT DaySummary for EVERY day of the "
                    f"trip (start_date through end_date). Issues: {detail}. Re-call "
                    "generate_scenarios ONCE with a complete day-by-day plan — emit a "
                    "real, distinct entry for each day_number from 1 to the trip length "
                    "(no repeated/placeholder days). If the trip is shorter than the "
                    "date window implies, shorten start_date/end_date to match the "
                    f"actual trip length rather than padding with filler days.{skeleton_note}"
                ),
                "scenarios": [],
            }

    currency = ctx.deps.user_preferences.currency
    party = ctx.deps.party_size
    for s in scenarios:
        # Keep the displayed math self-consistent: the grand total is always the
        # sum of its parts, regardless of what the model put in the field.
        cb = s.cost_breakdown
        cb.grand_total = round(cb.transportation + cb.accommodation, 2)
        # Backfill the party size when the model left `travelers` at the default
        # (it often nests `travelers` on the itinerary, where it's dropped). This
        # keeps the UI's per-person fares correct.
        if party and party > 1 and s.travelers <= 1:
            s.travelers = party
        # Backfill any missing day titles so the UI always has a headline.
        for d in s.itinerary.days:
            if not (d.title or "").strip():
                desc = (d.description or "").strip()
                d.title = (desc[:48].rstrip(" .,;:") or f"Day {d.day_number}")
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


@kompass_agent.tool
async def set_background_image(ctx: RunContext[AgentDependencies], scene_description: str) -> str:
    """Regenerate the trip's "vibe" background image with a new scene.

    Call this ONLY when the user explicitly asks to change, refresh, or set the
    background/vibe image for the trip (e.g. "change the background to a sunset
    over the caldera"). Do NOT call it as part of normal planning — an image is
    generated automatically for every trip.

    Args:
        scene_description: A vivid, photographic scene to render. Describe place,
            mood, light and season. No text, letters, words, logos, or watermarks.
    """
    trip_id = ctx.deps.trip_id
    if not trip_id:
        return "I couldn't update the background image — there's no active trip yet."
    # Fire-and-forget so the chat reply isn't blocked by image rendering.
    asyncio.create_task(
        generate_trip_background(
            trip_id,
            scene_description,
            ctx.deps.user_preferences,
            force=True,
            override_scene=scene_description,
        )
    )
    logger.info(f"Regenerating background image for trip {trip_id}")
    return "Updating the trip's background image now — it'll refresh in a moment."


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


