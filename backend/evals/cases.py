"""Golden dataset for the Kompass agent.

12 cases spanning six diagnostic categories. Prompts are deliberately
self-contained ("decide sensibly, no clarifications") so a single headless turn
can complete without the human-in-the-loop card — the scripted stub answers if
the model asks anyway.

Cases assert behavior (tools, constraints, structure), never exact
prices/dates/hotels, so the suite measures the model without overfitting to one
plan or to live data.
"""

from pydantic_evals import Case, Dataset

from evals.evaluators import ALL_EVALUATORS
from evals.schema import CaseInputs, CaseMeta, Category

_CASES: list[Case] = [
    # ------------------------------------------------------------------ tool selection
    Case(
        name="flexible_dates_uses_cheapest_dates",
        inputs=CaseInputs(
            prompt=(
                "I'm flexible on exact dates — find me the cheapest few days to fly "
                "from Berlin to Athens in September 2026 for 2 people, about a 5-day "
                "trip. Decide sensibly and give me a plan; no clarifications needed."
            ),
        ),
        metadata=CaseMeta(
            category=Category.TOOL_SELECTION,
            notes="Flexible dates should trigger find_cheapest_dates.",
            required_tools=["find_cheapest_dates", "generate_scenarios"],
        ),
    ),
    Case(
        name="known_dates_round_trip_two_flight_searches",
        inputs=CaseInputs(
            prompt=(
                "Plan a round trip from Berlin to Rome for 2 people, flying out "
                "2026-10-03 and back 2026-10-07. Attach real flight times both ways. "
                "One definitive plan; decide sensibly, no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.TOOL_SELECTION,
            notes="A round trip needs a one-way search_flights per direction.",
            required_tools=["search_flights", "generate_scenarios"],
            min_flight_searches=2,
        ),
    ),
    Case(
        name="destination_knowledge_uses_web_search",
        inputs=CaseInputs(
            prompt=(
                "When is the best time of year to visit the Greek islands, and plan me "
                "a 6-day trip from Berlin to Santorini for 2 people around that ideal "
                "window in 2026. One plan; decide sensibly, no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.TOOL_SELECTION,
            notes="Seasonality knowledge should come from grounded search_web.",
            required_tools=["search_web", "generate_scenarios"],
        ),
    ),
    # -------------------------------------------------------------- constraint adherence
    Case(
        name="budget_cap_respected",
        inputs=CaseInputs(
            prompt=(
                "Plan a 5-day trip from Berlin to Athens for 2 people in September "
                "2026. Hard budget: the whole trip must stay under 1500 EUR total. "
                "One definitive plan; decide sensibly, no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.CONSTRAINT_ADHERENCE,
            notes="Every scenario's grand_total must be <= 1500.",
            required_tools=["generate_scenarios"],
            budget_cap=1500.0,
        ),
    ),
    Case(
        name="direct_flights_only_preference",
        inputs=CaseInputs(
            prompt=(
                "Plan a long weekend from Berlin to Lisbon for 2 people, 2026-09-18 to "
                "2026-09-21. One definitive plan; decide sensibly, no clarifications."
            ),
            preferences={"direct_flights_only": True},
        ),
        metadata=CaseMeta(
            category=Category.CONSTRAINT_ADHERENCE,
            notes="Saved profile wants direct flights → max_stops=0 on every search.",
            required_tools=["search_flights", "generate_scenarios"],
            direct_only=True,
        ),
    ),
    Case(
        name="no_redeye_daytime_flights",
        inputs=CaseInputs(
            prompt=(
                "Plan a 5-day trip from Berlin to Athens for 2 people in September "
                "2026. I really dislike red-eye and overnight flights — daytime "
                "departures only, even if a bit pricier. One plan; decide sensibly, "
                "no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.CONSTRAINT_ADHERENCE,
            notes="BER->ATH cheapest are red-eyes; the plan must use daytime legs.",
            required_tools=["search_flights", "generate_scenarios"],
            no_redeye=True,
        ),
    ),
    Case(
        name="family_of_four_budget",
        inputs=CaseInputs(
            prompt=(
                "Plan a 5-day trip from Berlin to Athens for a family of 4 (2 adults, "
                "2 kids) in September 2026, keeping the total under 3500 EUR. One "
                "definitive plan; decide sensibly, no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.CONSTRAINT_ADHERENCE,
            notes="Party size must reach both flight and lodging searches.",
            required_tools=["search_flights", "search_accommodations", "generate_scenarios"],
            budget_cap=3500.0,
            party_size=4,
        ),
    ),
    # -------------------------------------------------------------- anti-fabrication
    Case(
        name="empty_route_falls_back_and_flags_estimated",
        inputs=CaseInputs(
            prompt=(
                "Plan a 5-day trip from Munich to Mykonos for 2 people in September "
                "2026 with real prices. One definitive plan; decide sensibly, no "
                "clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.ANTI_FABRICATION,
            notes="MUC->JMK returns no flights → must use search_web and flag estimated.",
            required_tools=["search_web", "generate_scenarios"],
            expect_estimated=True,
        ),
    ),
    # -------------------------------------------------------------- manual override
    Case(
        name="already_have_flights_zero_transport",
        inputs=CaseInputs(
            prompt=(
                "I've ALREADY booked and paid for my flights from Berlin to Rome "
                "(out 2026-10-03, back 2026-10-07, 2 people). Do not price or search "
                "flights — just plan the hotel and the day-by-day itinerary, and don't "
                "count flight cost in the budget. One plan; decide sensibly, no "
                "clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.MANUAL_OVERRIDE,
            notes="Flights are pre-arranged → skip flight tools, transportation = 0.",
            required_tools=["search_accommodations", "generate_scenarios"],
            forbidden_tools=["search_flights", "find_cheapest_dates"],
            transportation_zero=True,
        ),
    ),
    # -------------------------------------------------------------- party propagation
    Case(
        name="family_of_four_lodging_guests",
        inputs=CaseInputs(
            prompt=(
                "Plan a 4-night trip from Berlin to Lisbon for a family of 4 in "
                "October 2026 (2026-10-10 to 2026-10-14). Book lodging that fits all "
                "four of us. One plan; decide sensibly, no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.PARTY_PROPAGATION,
            notes="party_size=4 must reach passengers and guests.",
            required_tools=["search_flights", "search_accommodations", "generate_scenarios"],
            party_size=4,
        ),
    ),
    # -------------------------------------------------------------- itinerary quality
    Case(
        name="greek_island_hop_single_plan",
        inputs=CaseInputs(
            prompt=(
                "Plan a 12-day Greek-island-hopping trip from Berlin for 2 people in "
                "September 2026, visiting Athens plus the islands of Milos, Paros and "
                "Naxos. Take ferries between the islands and book a hotel on each "
                "island. Give me one definitive plan; decide sensibly, no "
                "clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.ITINERARY_QUALITY,
            notes="Golden-example shape: a ferry per hop and a hotel per island.",
            required_tools=[
                "search_flights",
                "search_ground_transport",
                "search_accommodations",
                "generate_scenarios",
            ],
            expect_islands=["milos", "paros", "naxos", "athens"],
            min_ground_legs=3,
        ),
    ),
    Case(
        name="greek_island_hop_two_windows",
        inputs=CaseInputs(
            prompt=(
                "Compare two date windows for a ~12-day Greek-island-hopping trip from "
                "Berlin for 2 people: late August/early September vs. mid/late "
                "September 2026, visiting Athens plus Milos, Paros and Naxos with "
                "ferries between islands and a hotel on each. Show me both options "
                "side by side; decide sensibly, no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.ITINERARY_QUALITY,
            notes="Two comparable island-hop scenarios (mirrors the golden example).",
            required_tools=[
                "search_flights",
                "search_ground_transport",
                "search_accommodations",
                "generate_scenarios",
            ],
            min_scenarios=2,
            expect_islands=["milos", "paros", "naxos"],
            min_ground_legs=3,
        ),
    ),
]


def build_dataset() -> Dataset:
    """The golden dataset with all deterministic evaluators attached."""
    return Dataset(name="kompass-golden", cases=_CASES, evaluators=list(ALL_EVALUATORS))


CASES = _CASES
