import pytest
import json
from typing import Any
from unittest.mock import MagicMock
from pydantic_ai.models.test import TestModel, _WrappedTextOutput
from pydantic_ai.models import ModelRequestParameters
from app.agent.agent import kompass_agent
from app.agent.dependency import AgentDependencies
from app.ports.prompt_service import PromptServicePort
from app.domain import Scenario

# Custom TestModel that allows plain text responses even when output_mode is 'tool'
# (which is the case when Agent output_type is Union[str, Scenario])
class UnionTestModel(TestModel):
    def _get_output(self, model_request_parameters: ModelRequestParameters) -> Any:
        if self.custom_output_text is not None:
            return _WrappedTextOutput(self.custom_output_text)
        return super()._get_output(model_request_parameters)

@pytest.fixture
def agent_deps():
    mock_prompt_service = MagicMock(spec=PromptServicePort)
    mock_prompt_service.get_prompt.return_value = "You are a travel planning assistant. Current Time: {current_time}"
    return AgentDependencies(prompt_service=mock_prompt_service)

@pytest.mark.asyncio
async def test_agent_conversational_response(agent_deps):
    # Set up UnionTestModel to return a conversational string
    test_model = UnionTestModel(custom_output_text="Where would you like to travel in Greece?")
    
    result = await kompass_agent.run(
        "Plan me a trip to Greece.",
        deps=agent_deps,
        model=test_model
    )
    
    assert result.output == "Where would you like to travel in Greece?"
    assert isinstance(result.output, str)

@pytest.mark.asyncio
async def test_agent_scenario_structured_response(agent_deps):
    # Mock Scenario dict matching the Pydantic schema
    mock_scenario_data = {
        "label": "Scenario A: Economy Greece Trip",
        "itinerary": {
            "legs": [
                {
                    "mode": "flight",
                    "origin": "BER",
                    "destination": "ATH",
                    "departure_time": "2026-09-10T10:00:00Z",
                    "arrival_time": "2026-09-10T12:30:00Z",
                    "carrier": "Ryanair FR123",
                    "cost": 150.0
                }
            ],
            "accommodations": [
                {
                    "name": "Athens Cozy Hotel",
                    "location": "Athens",
                    "check_in": "2026-09-10T14:00:00Z",
                    "check_out": "2026-09-20T11:00:00Z",
                    "cost": 800.0
                }
            ],
            "days": [
                {
                    "day_number": 1,
                    "title": "Arrival & Plaka Stroll",
                    "description": "Welcome to Athens!",
                    "schedule": [
                        {
                            "period": "Afternoon",
                            "activity": "Arrive and check in",
                            "location": "Athens",
                            "details": "Drop bags at the hotel and freshen up."
                        },
                        {
                            "period": "Evening",
                            "activity": "Evening walk in Plaka",
                            "location": "Plaka"
                        }
                    ]
                }
            ]
        },
        "comparison_label": "Early September",
        "start_date": "2026-09-10",
        "end_date": "2026-09-20",
        "cost_breakdown": {
            "transportation": 150.0,
            "accommodation": 800.0,
            "grand_total": 950.0,
        },
        "stress_score": 1,
        "stress_factors": {
            "layover_count": 0,
            "overnight_travel": False,
            "tight_connection": False,
            "total_travel_hours": 3.5,
        },
        "highlights": ["Direct flight", "Single hotel"],
        "reasoning_summary": "Direct flight and simple single accommodation makes this highly relaxed."
    }
    
    # We pass the data to custom_output_args so TestModel executes the output tool
    test_model = UnionTestModel(custom_output_args=mock_scenario_data)
    
    result = await kompass_agent.run(
        "Plan me a 10-day trip to Greece in September",
        deps=agent_deps,
        model=test_model
    )
    
    # Assert output is validated as a Scenario object
    assert isinstance(result.output, Scenario)
    assert result.output.label == "Scenario A: Economy Greece Trip"
    assert len(result.output.itinerary.legs) == 1
    assert result.output.itinerary.legs[0].origin == "BER"
    assert result.output.cost_breakdown.grand_total == 950.0
    assert result.output.stress_score == 1

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
async def test_search_ground_transport_builds_query_and_threads_currency(agent_deps, monkeypatch):
    from app.agent import agent as agent_module
    from app.agent.agent import search_ground_transport
    from pydantic_ai import RunContext
    from app.domain import UserPreferences

    agent_deps.user_preferences = UserPreferences(currency="GBP")
    ctx = RunContext(deps=agent_deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    captured = {}

    async def fake_run_research(query: str) -> str:
        captured["query"] = query
        return "Blue Star Ferries departs Piraeus ~07:25, arrives Milos ~14:00, ~45 GBP."

    monkeypatch.setattr(agent_module, "run_research", fake_run_research)

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
async def test_generate_scenarios_rejects_single_scenario(agent_deps):
    from app.agent.agent import generate_scenarios
    from pydantic_ai import RunContext

    ctx = RunContext(deps=agent_deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    payload = await generate_scenarios(
        ctx, "Santorini", [_make_scenario("Only one", 300.0, 700.0, 1000.0)]
    )

    # A lone scenario is not a comparison: nothing renders and the agent is told
    # to re-call with 2-3.
    assert payload["scenarios"] == []
    assert "error" in payload
    assert "2-3" in payload["error"]


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

