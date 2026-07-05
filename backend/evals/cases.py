"""Golden dataset for the Kompass agent.

30 cases spanning seven diagnostic categories (tool selection, constraint
adherence, anti-fabrication, manual override, party propagation, itinerary
quality, human-in-the-loop). Most prompts are self-contained ("decide sensibly,
no clarifications") so a single headless turn completes without the HITL card;
the dedicated HITL cases deliberately withhold info so the agent must ask, and
the multi-turn cases (`followups`) exercise refinement flows.

Cases assert behavior (tools, constraints, structure) with deterministic
evaluators, plus a few soft criteria (recommendation quality, vibe match)
scored by a Flash LLM judge — never exact prices/dates/hotels, so the suite
measures the model without overfitting to one plan or to live data.
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
    # ============================ Phase 3 additions ============================
    # ------------------------------------------------------------------ tool selection
    Case(
        name="hotel_only_scope_limits_tools",
        inputs=CaseInputs(
            prompt=(
                "My transport is already sorted. Just find me a hotel in Athens for "
                "2 people, 2026-09-10 to 2026-09-14, and give me a day-by-day plan. "
                "One plan; decide sensibly, no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.TOOL_SELECTION,
            notes="Lodging-only ask → no flight tooling at all.",
            required_tools=["search_accommodations", "generate_scenarios"],
            forbidden_tools=["search_flights", "find_cheapest_dates"],
        ),
    ),
    Case(
        name="train_route_uses_ground_transport",
        inputs=CaseInputs(
            prompt=(
                "Plan a 4-day trip from Berlin to Prague for 2 people, 2026-10-05 to "
                "2026-10-09. I want to take the TRAIN between the two cities, not fly. "
                "One plan; decide sensibly, no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.TOOL_SELECTION,
            notes="Explicit rail preference → ground-transport tool, no flights.",
            required_tools=["search_ground_transport", "generate_scenarios"],
            forbidden_tools=["search_flights", "find_cheapest_dates"],
            min_ground_legs=1,
        ),
    ),
    # -------------------------------------------------------------- constraint adherence
    Case(
        name="currency_preference_respected",
        inputs=CaseInputs(
            prompt=(
                "Plan a 5-day trip from Berlin to Athens for 2 people in September "
                "2026. One definitive plan; decide sensibly, no clarifications."
            ),
            preferences={"currency": "USD"},
        ),
        metadata=CaseMeta(
            category=Category.CONSTRAINT_ADHERENCE,
            notes="Saved currency USD must thread to searches and the payload.",
            required_tools=["generate_scenarios"],
            expect_currency="USD",
        ),
    ),
    Case(
        name="infeasible_budget_no_fabrication",
        inputs=CaseInputs(
            prompt=(
                "Plan a 5-day trip from Berlin to Athens for 2 people in September "
                "2026. My absolute hard cap is 150 EUR for the ENTIRE trip including "
                "flights and hotel. Decide sensibly, no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.CONSTRAINT_ADHERENCE,
            notes="Budget is impossible → must not fabricate an over-budget 'fit'.",
            budget_cap=150.0,
            budget_infeasible=True,
        ),
    ),
    Case(
        name="direct_only_on_synthetic_route",
        inputs=CaseInputs(
            prompt=(
                "Plan a long weekend from Hamburg (HAM) to Palma de Mallorca (PMI) "
                "for 2 people, 2026-09-18 to 2026-09-21. One plan; decide sensibly, "
                "no clarifications."
            ),
            preferences={"direct_flights_only": True},
        ),
        metadata=CaseMeta(
            category=Category.CONSTRAINT_ADHERENCE,
            notes="Direct-only must hold on an off-catalog (synthetic) route too.",
            required_tools=["search_flights", "generate_scenarios"],
            direct_only=True,
        ),
    ),
    # -------------------------------------------------------------- anti-fabrication
    Case(
        name="ferry_leg_flagged_estimated",
        inputs=CaseInputs(
            prompt=(
                "Plan a 4-day trip from Athens to the island of Milos and back for "
                "2 people in September 2026. There are no flights — get there by "
                "ferry both ways and book a hotel on Milos. One plan; decide "
                "sensibly, no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.ANTI_FABRICATION,
            notes="Ferry prices come from research → flag estimated, don't invent.",
            required_tools=["search_ground_transport", "generate_scenarios"],
            expect_estimated=True,
            expect_islands=["milos"],
            min_ground_legs=1,
        ),
    ),
    # -------------------------------------------------------------- party propagation
    Case(
        name="solo_traveler_propagation",
        inputs=CaseInputs(
            prompt=(
                "Plan a 4-day solo trip from Berlin to Lisbon for just me, 2026-10-10 "
                "to 2026-10-14. One plan; decide sensibly, no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.PARTY_PROPAGATION,
            notes="Solo → passengers/guests = 1 everywhere.",
            required_tools=["search_flights", "search_accommodations", "generate_scenarios"],
            party_size=1,
        ),
    ),
    Case(
        name="group_of_six_propagation",
        inputs=CaseInputs(
            prompt=(
                "Plan a 5-day trip from Berlin to Athens for a group of 6 friends in "
                "September 2026. One plan; decide sensibly, no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.PARTY_PROPAGATION,
            notes="Large party → passengers/guests = 6 (lodging needs 3 rooms).",
            required_tools=["search_flights", "search_accommodations", "generate_scenarios"],
            party_size=6,
        ),
    ),
    # -------------------------------------------------------------- itinerary quality
    Case(
        name="single_island_santorini_ferry",
        inputs=CaseInputs(
            prompt=(
                "Plan a 6-day trip from Berlin to Santorini for 2 people in September "
                "2026: fly into Athens, take the ferry to Santorini, and book hotels "
                "in both. One definitive plan; decide sensibly, no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.ITINERARY_QUALITY,
            notes="Fly + ferry hop with a hotel in each stop.",
            required_tools=[
                "search_flights",
                "search_ground_transport",
                "search_accommodations",
                "generate_scenarios",
            ],
            expect_islands=["athens", "santorini"],
            min_ground_legs=1,
        ),
    ),
    Case(
        name="multi_city_rail_europe",
        inputs=CaseInputs(
            prompt=(
                "Plan a 7-day trip from Berlin for 2 people in October 2026 visiting "
                "Prague and then Vienna BY TRAIN, with a hotel in each city. One "
                "definitive plan; decide sensibly, no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.ITINERARY_QUALITY,
            notes="Multi-city rail chain: a train per hop, a hotel per city.",
            required_tools=[
                "search_ground_transport",
                "search_accommodations",
                "generate_scenarios",
            ],
            expect_islands=["prague", "vienna"],
            min_ground_legs=2,
        ),
    ),
    Case(
        name="two_option_recommendation_quality",
        inputs=CaseInputs(
            prompt=(
                "Plan a 5-day trip from Berlin to Athens for 2 people in September "
                "2026. Give me TWO options — a budget one and a comfort one — and "
                "tell me which you'd pick. Decide sensibly, no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.ITINERARY_QUALITY,
            notes="Two options + a judged, concise recommendation in the reply.",
            required_tools=["generate_scenarios"],
            min_scenarios=2,
            judge_recommendation=True,
        ),
    ),
    Case(
        name="vibe_relaxed_foodie",
        inputs=CaseInputs(
            prompt=(
                "Plan a relaxed 5-day FOODIE trip from Berlin to Lisbon for 2 people, "
                "2026-10-10 to 2026-10-14 — lots of great food, markets, wine and "
                "leisurely meals, nothing too strenuous. One plan; decide sensibly, "
                "no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.ITINERARY_QUALITY,
            notes="Judge: days center on food/markets/wine, low intensity.",
            required_tools=["generate_scenarios"],
            judge_vibe="relaxed foodie (food markets, wine, leisurely dining, minimal strenuous activity)",
            judge_recommendation=True,
        ),
    ),
    Case(
        name="vibe_adventure_hiking",
        inputs=CaseInputs(
            prompt=(
                "Plan an adventurous 6-day HIKING trip from Berlin to Athens for "
                "2 people in September 2026 — trails, outdoor activities and nature, "
                "active days. One plan; decide sensibly, no clarifications."
            ),
        ),
        metadata=CaseMeta(
            category=Category.ITINERARY_QUALITY,
            notes="Judge: days center on hikes/outdoor/nature activity.",
            required_tools=["generate_scenarios"],
            judge_vibe="adventure hiking (trails, outdoor activity, nature, active days)",
        ),
    ),
    # -------------------------------------------------------------- multi-turn refinement
    Case(
        name="refine_add_cheaper_option",
        inputs=CaseInputs(
            prompt=(
                "Plan a 5-day trip from Berlin to Athens for 2 people in September "
                "2026. Give me ONE plan to start. Decide sensibly, no clarifications."
            ),
            followups=[
                "Nice — now add a second, cheaper option so I can compare the two "
                "side by side."
            ],
        ),
        metadata=CaseMeta(
            category=Category.ITINERARY_QUALITY,
            notes="Refinement: second turn must yield a 2-way comparison.",
            required_tools=["generate_scenarios"],
            min_scenarios=2,
            expect_travelers=2,
        ),
    ),
    Case(
        name="refine_change_party_size",
        inputs=CaseInputs(
            prompt=(
                "Plan a 4-day trip from Berlin to Lisbon for 2 people, 2026-10-10 to "
                "2026-10-14. One plan; decide sensibly, no clarifications."
            ),
            followups=[
                "Actually, make it for 4 people instead — same dates and city."
            ],
        ),
        metadata=CaseMeta(
            category=Category.PARTY_PROPAGATION,
            notes="Refinement carries context; final plan is for 4 travelers.",
            required_tools=["generate_scenarios"],
            expect_travelers=4,
        ),
    ),
    # -------------------------------------------------------------- human-in-the-loop
    Case(
        name="missing_origin_asks_clarification",
        inputs=CaseInputs(
            prompt=(
                "Plan a 5-day trip to Athens for 2 people in September 2026."
            ),
            clarifying_answer="I'm flying from Berlin.",
        ),
        metadata=CaseMeta(
            category=Category.HUMAN_IN_THE_LOOP,
            notes="No origin city → must ask before it can price flights.",
            expect_clarification=True,
        ),
    ),
    Case(
        name="missing_dates_asks_clarification",
        inputs=CaseInputs(
            prompt=(
                "Plan a trip from Berlin to Lisbon for 2 people."
            ),
            clarifying_answer="Five days in mid-October 2026.",
        ),
        metadata=CaseMeta(
            category=Category.HUMAN_IN_THE_LOOP,
            notes="No dates or duration → must ask rather than guess a window.",
            expect_clarification=True,
        ),
    ),
    Case(
        name="complete_prompt_needs_no_clarification",
        inputs=CaseInputs(
            prompt=(
                "Plan a 4-day trip from Berlin to Lisbon for 2 people, 2026-10-10 to "
                "2026-10-14, mid-range budget around 1200 EUR, daytime flights only. "
                "Give me one definitive plan."
            ),
        ),
        metadata=CaseMeta(
            category=Category.HUMAN_IN_THE_LOOP,
            notes="Fully specified → proceed without asking anything.",
            required_tools=["generate_scenarios"],
            forbid_clarification=True,
        ),
    ),
]


def build_dataset() -> Dataset:
    """The golden dataset with all deterministic evaluators attached."""
    return Dataset(name="kompass-golden", cases=_CASES, evaluators=list(ALL_EVALUATORS))


CASES = _CASES
