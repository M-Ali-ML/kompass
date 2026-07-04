import pytest
from unittest.mock import MagicMock
from pydantic_ai.models.test import TestModel
from app.agent.agent import kompass_agent
from app.agent.dependency import AgentDependencies
from app.ports.prompt_service import PromptServicePort
from app.domain import Scenario

@pytest.fixture
def agent_deps():
    mock_prompt_service = MagicMock(spec=PromptServicePort)
    mock_prompt_service.get_prompt.return_value = "You are a travel planning assistant. Current Time: {current_time}"
    return AgentDependencies(prompt_service=mock_prompt_service)

@pytest.mark.asyncio
async def test_agent_conversational_response(agent_deps):
    # The agent's final output is always plain text (output_type=str); plans are
    # delivered via the generate_scenarios tool, not as structured output.
    test_model = TestModel(custom_output_text="Where would you like to travel in Greece?")

    result = await kompass_agent.run(
        "Plan me a trip to Greece.",
        deps=agent_deps,
        model=test_model
    )

    assert result.output == "Where would you like to travel in Greece?"
    assert isinstance(result.output, str)

@pytest.mark.asyncio
async def test_gather_preferences_tool(agent_deps):
    from app.agent.agent import gather_preferences
    from pydantic_ai import RunContext
    from app.domain import UserPreferences
    
    # We can invoke the tool directly using the function
    ctx = RunContext(
        deps=agent_deps,
        model=MagicMock(),
        usage=MagicMock(),
        prompt="test prompt"
    )
    
    prefs = UserPreferences(
        direct_flights_only=True,
        vibe_tags=["foodie", "relaxation"]
    )
    
    res = await gather_preferences(ctx, prefs)
    assert "Successfully gathered user preferences" in res
    assert agent_deps.user_preferences.direct_flights_only is True
    assert "foodie" in agent_deps.user_preferences.vibe_tags


def _make_scenario(label: str, transport: float, accom: float, claimed_total: float) -> Scenario:
    return Scenario(
        label=label,
        comparison_label=label,
        start_date="2026-09-04",
        end_date="2026-09-11",
        itinerary={"legs": [], "accommodations": [], "days": []},
        cost_breakdown={
            "transportation": transport,
            "accommodation": accom,
            # Intentionally wrong so the tool must normalize it.
            "grand_total": claimed_total,
        },
        stress_score=2,
        stress_factors={
            "layover_count": 1,
            "overnight_travel": False,
            "tight_connection": False,
            "total_travel_hours": 6.0,
        },
        highlights=["1 layover"],
        reasoning_summary="A balanced option.",
    )


def _day(n: int, title: str | None = None) -> dict:
    """A minimal but distinct DaySummary dict for building day-by-day plans."""
    return {
        "day_number": n,
        "title": title if title is not None else f"Day {n} title",
        "description": f"Day {n} plan",
        "schedule": [
            {"period": "Morning", "activity": f"Activity {n}"},
        ],
    }


def _make_scenario_with_days(label: str, days: list[dict], travelers: int = 1) -> Scenario:
    """A 3-night scenario (Sep 4 → Sep 7) carrying an explicit day list."""
    return Scenario(
        label=label,
        comparison_label=label,
        start_date="2026-09-04",
        end_date="2026-09-07",
        travelers=travelers,
        itinerary={"legs": [], "accommodations": [], "days": days},
        cost_breakdown={"transportation": 100.0, "accommodation": 300.0, "grand_total": 0.0},
        stress_score=2,
        stress_factors={
            "layover_count": 0,
            "overnight_travel": False,
            "tight_connection": False,
            "total_travel_hours": 4.0,
        },
        highlights=["Test"],
        reasoning_summary="A balanced option.",
    )


@pytest.mark.asyncio
async def test_generate_scenarios_rejects_duplicate_filler_days(agent_deps):
    from app.agent.agent import generate_scenarios
    from pydantic_ai import RunContext

    ctx = RunContext(deps=agent_deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    # 3-night trips with the full day COUNT, but padded with identical filler
    # days (day 3 repeats day 2) — the model's way of hitting a day count.
    dup_days = [_day(1), _day(2), {**_day(3), "title": _day(2)["title"],
                                   "description": _day(2)["description"],
                                   "schedule": _day(2)["schedule"]}]
    scenarios = [
        _make_scenario_with_days("Early September", dup_days),
        _make_scenario_with_days("Late August", dup_days),
    ]

    payload = await generate_scenarios(ctx, "Santorini", scenarios)

    # Padded/placeholder days are rejected with a corrective message.
    assert payload["scenarios"] == []
    assert "placeholder" in payload["error"].lower() or "distinct" in payload["error"].lower()
    assert agent_deps.day_validation_retries == 1


@pytest.mark.asyncio
async def test_generate_scenarios_tolerates_off_by_one_day(agent_deps):
    from app.agent.agent import generate_scenarios
    from pydantic_ai import RunContext

    ctx = RunContext(deps=agent_deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    # 4-day inclusive window (Sep 4 → Sep 7) with 3 distinct days — one short of
    # the span. The ±1 tolerance should let it render rather than forcing a
    # regeneration.
    days = [_day(1), _day(2), _day(3)]
    payload = await generate_scenarios(
        ctx, "Santorini", [_make_scenario_with_days("Almost there", days)]
    )

    assert "error" not in payload
    assert len(payload["scenarios"]) == 1
    assert agent_deps.day_validation_retries == 0


@pytest.mark.asyncio
async def test_generate_scenarios_backfills_travelers_and_titles(agent_deps):
    from app.agent.agent import generate_scenarios
    from pydantic_ai import RunContext

    # The party size searched this run; the model left travelers at the default.
    agent_deps.party_size = 2
    ctx = RunContext(deps=agent_deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    # Complete, distinct day plans (so the day guard passes), but day 1 has no
    # title and the scenario's travelers field is the default 1.
    days = [_day(1, title=None), _day(2), _day(3)]
    scenarios = [
        _make_scenario_with_days("Early September", days, travelers=1),
        _make_scenario_with_days("Late August", days, travelers=1),
    ]

    payload = await generate_scenarios(ctx, "Santorini", scenarios)

    assert len(payload["scenarios"]) == 2
    # travelers is backfilled from the searched party size for per-person fares.
    assert all(s["travelers"] == 2 for s in payload["scenarios"])
    # The missing day-1 title is backfilled (derived from the description).
    day1 = payload["scenarios"][0]["itinerary"]["days"][0]
    assert day1["title"] and day1["title"].strip()


@pytest.mark.asyncio
async def test_search_ground_transport_builds_query_and_threads_currency(agent_deps):
    from app.agent.agent import search_ground_transport
    from app.ports.research_service import ResearchServicePort
    from pydantic_ai import RunContext
    from app.domain import UserPreferences

    agent_deps.user_preferences = UserPreferences(currency="GBP")

    captured = {}

    class FakeResearchService(ResearchServicePort):
        async def research(self, query: str) -> str:
            captured["query"] = query
            return "Blue Star Ferries departs Piraeus ~07:25, arrives Milos ~14:00, ~45 GBP."

    agent_deps.research_service = FakeResearchService()
    ctx = RunContext(deps=agent_deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    result = await search_ground_transport(
        ctx, "Piraeus", "Milos", "2026-09-12", modes="ferry"
    )

    assert "Blue Star Ferries" in result
    # The query is grounded in the requested route/date, focused on the modes,
    # and carries the traveler's preferred currency through to the research agent.
    assert "Piraeus" in captured["query"]
    assert "Milos" in captured["query"]
    assert "2026-09-12" in captured["query"]
    assert "ferry" in captured["query"]
    assert "GBP" in captured["query"]


@pytest.mark.asyncio
async def test_generate_scenarios_normalizes_totals_and_payload(agent_deps):
    from app.agent.agent import generate_scenarios
    from pydantic_ai import RunContext
    from app.domain import UserPreferences

    agent_deps.user_preferences = UserPreferences(currency="USD")
    # Isolate normalization from the day-plan guard (covered separately) by
    # exhausting its retry budget.
    agent_deps.day_validation_retries = 2
    ctx = RunContext(deps=agent_deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    scenarios = [
        _make_scenario("Early September", 340.0, 900.0, claimed_total=0.0),
        _make_scenario("Late August", 480.0, 1200.0, claimed_total=999.0),
    ]

    payload = await generate_scenarios(ctx, "Santorini", scenarios, estimated=True)

    assert payload["destination"] == "Santorini"
    assert payload["currency"] == "USD"
    assert payload["estimated"] is True
    assert len(payload["scenarios"]) == 2
    # Grand totals are recomputed from their parts regardless of the input value.
    assert payload["scenarios"][0]["cost_breakdown"]["grand_total"] == 1240.0
    assert payload["scenarios"][1]["cost_breakdown"]["grand_total"] == 1680.0
    # Dates serialize as ISO strings for the frontend.
    assert payload["scenarios"][0]["start_date"] == "2026-09-04"


@pytest.mark.asyncio
async def test_generate_scenarios_normalizes_subtotals_from_line_items(agent_deps):
    from app.agent.agent import generate_scenarios
    from pydantic_ai import RunContext

    # Skip the day-plan guard so we isolate cost normalization.
    agent_deps.day_validation_retries = 2
    ctx = RunContext(deps=agent_deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    # Itemized legs (100 + 250 = 350) and stays (300 + 180 = 480) that DON'T
    # match the model's stated subtotals — arithmetic must never be trusted from
    # the model. The line items (tool-sourced) are the source of truth.
    scenario = Scenario(
        label="Island hop",
        comparison_label="Island hop",
        start_date="2026-09-04",
        end_date="2026-09-07",
        itinerary={
            "legs": [
                {
                    "mode": "flight",
                    "origin": "BER",
                    "destination": "ATH",
                    "departure_time": "2026-09-04T09:00:00+02:00",
                    "arrival_time": "2026-09-04T12:00:00+03:00",
                    "carrier": "Aegean",
                    "cost": 100.0,
                },
                {
                    "mode": "ferry",
                    "origin": "Piraeus",
                    "destination": "Milos",
                    "departure_time": "2026-09-04T15:00:00+03:00",
                    "arrival_time": "2026-09-04T18:30:00+03:00",
                    "carrier": "Blue Star Ferries",
                    "cost": 250.0,
                },
            ],
            "accommodations": [
                {
                    "name": "Athens Central",
                    "location": "Athens",
                    "check_in": "2026-09-04T15:00:00+03:00",
                    "check_out": "2026-09-05T11:00:00+03:00",
                    "cost": 300.0,
                },
                {
                    "name": "Milos Sea Rooms",
                    "location": "Milos",
                    "check_in": "2026-09-05T15:00:00+03:00",
                    "check_out": "2026-09-07T11:00:00+03:00",
                    "cost": 180.0,
                },
            ],
            "days": [],
        },
        # Deliberately wrong subtotals; the tool must overwrite them.
        cost_breakdown={"transportation": 600.0, "accommodation": 959.0, "grand_total": 0.0},
        stress_score=3,
        stress_factors={
            "layover_count": 1,
            "overnight_travel": False,
            "tight_connection": False,
            "total_travel_hours": 8.0,
        },
        highlights=["Ferry hop"],
        reasoning_summary="Island hopping.",
    )

    payload = await generate_scenarios(ctx, "Milos", [scenario])

    cb = payload["scenarios"][0]["cost_breakdown"]
    # Subtotals are re-derived from the itemized line items, not the model's math.
    assert cb["transportation"] == 350.0
    assert cb["accommodation"] == 480.0
    assert cb["grand_total"] == 830.0


@pytest.mark.asyncio
async def test_generate_scenarios_renders_single_scenario(agent_deps):
    from app.agent.agent import generate_scenarios
    from pydantic_ai import RunContext

    # Skip the day-plan guard (covered separately) so we isolate single-scenario
    # rendering.
    agent_deps.day_validation_retries = 2
    ctx = RunContext(deps=agent_deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    payload = await generate_scenarios(
        ctx, "Santorini", [_make_scenario("Only one", 300.0, 700.0, 1000.0)]
    )

    # A single definitive plan renders as one card (no longer rejected) so the
    # agent never falls back to narrating the plan as text.
    assert "error" not in payload
    assert len(payload["scenarios"]) == 1
    assert payload["scenarios"][0]["cost_breakdown"]["grand_total"] == 1000.0


@pytest.mark.asyncio
async def test_generate_scenarios_rejects_empty(agent_deps):
    from app.agent.agent import generate_scenarios
    from pydantic_ai import RunContext

    ctx = RunContext(deps=agent_deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    payload = await generate_scenarios(ctx, "Santorini", [])

    assert payload["scenarios"] == []
    assert "error" in payload


@pytest.mark.asyncio
async def test_generate_scenarios_rejects_incomplete_day_plan(agent_deps):
    from app.agent.agent import generate_scenarios
    from pydantic_ai import RunContext

    ctx = RunContext(deps=agent_deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    # Two valid scenarios but each spans a 7-night trip with no day-by-day plan.
    scenarios = [
        _make_scenario("Early September", 340.0, 900.0, 1240.0),
        _make_scenario("Late August", 480.0, 1200.0, 1680.0),
    ]

    payload = await generate_scenarios(ctx, "Santorini", scenarios)

    # The incomplete plan is rejected with a corrective message...
    assert payload["scenarios"] == []
    assert "error" in payload
    assert "day" in payload["error"].lower()
    assert agent_deps.day_validation_retries == 1

    # ...the guard fires at most twice per run (one correction for "too few
    # days", one for "padded/duplicate days"), then stands aside...
    payload2 = await generate_scenarios(ctx, "Santorini", scenarios)
    assert payload2["scenarios"] == []
    assert agent_deps.day_validation_retries == 2

    # ...so a third call proceeds and renders, preventing an infinite correction
    # loop even if the model can't comply.
    payload3 = await generate_scenarios(ctx, "Santorini", scenarios)
    assert len(payload3["scenarios"]) == 2

