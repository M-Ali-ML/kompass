import pytest
from unittest.mock import MagicMock

from pydantic_ai import RunContext

import app.agent.agent as agent_mod
import app.agent.research_agent as research_mod
from app.agent.agent import _month_to_range, find_cheapest_dates, search_flights, search_web
from app.agent.dependency import AgentDependencies
from app.adapters.mcp_flight_service import MCPFlightServiceAdapter
from app.domain import FlightDateOption, FlightOption, UserPreferences
from app.ports.flight_service import FlightServicePort
from app.ports.prompt_service import PromptServicePort
from app.mcp_servers import flights_server


# --- Domain / preferences -----------------------------------------------------

def test_currency_defaults_to_eur():
    assert UserPreferences().currency == "EUR"


def test_currency_override_wins_when_non_default():
    baseline = UserPreferences(currency="USD")
    # An unspecified (default EUR) override must not clobber the stored currency.
    assert baseline.merged_with(UserPreferences()).currency == "USD"
    # An explicit non-default currency wins.
    assert baseline.merged_with(UserPreferences(currency="JPY")).currency == "JPY"


# --- Month → date-range conversion --------------------------------------------

def test_month_to_range_year_month():
    assert _month_to_range("2026-09") == ("2026-09-01", "2026-09-30")


def test_month_to_range_explicit_date():
    assert _month_to_range("2026-09-15") == ("2026-09-15", "2026-09-30")


def test_month_to_range_name_with_year():
    assert _month_to_range("September 2027") == ("2027-09-01", "2027-09-30")


# --- No API key → degrade to search_web (no fabricated data) -------------------

def test_search_flights_unavailable_without_api_key(monkeypatch):
    monkeypatch.setattr(flights_server, "_api_key", lambda: None)
    result = flights_server.search_flights("BER", "ATH", "2026-09-10", currency="EUR")
    assert result["options"] == []
    assert result["estimated"] is False
    assert result["available"] is False
    assert result["currency"] == "EUR"


def test_find_cheapest_dates_unavailable_without_api_key(monkeypatch):
    monkeypatch.setattr(flights_server, "_api_key", lambda: None)
    result = flights_server.find_cheapest_dates(
        "BER", "ATH", "2026-09-01", "2026-09-30", duration_days=7, currency="GBP"
    )
    assert result["options"] == []
    assert result["available"] is False
    assert result["currency"] == "GBP"


def test_synthetic_estimators_are_gone():
    # The misleading synthetic generators must no longer exist on the server.
    assert not hasattr(flights_server, "_synthetic_flights")
    assert not hasattr(flights_server, "_synthetic_cheapest_dates")


# --- SerpApi parsing (mocked HTTP) --------------------------------------------

_SERPAPI_FLIGHTS_FIXTURE = {
    "best_flights": [
        {
            "flights": [
                {
                    "departure_airport": {"id": "BER", "time": "2026-09-10 09:00"},
                    "arrival_airport": {"id": "MUC", "time": "2026-09-10 10:10"},
                    "airline": "Lufthansa",
                },
                {
                    "departure_airport": {"id": "MUC", "time": "2026-09-10 11:30"},
                    "arrival_airport": {"id": "ATH", "time": "2026-09-10 14:45"},
                    "airline": "Lufthansa",
                },
            ],
            "layovers": [{"duration": 80, "name": "Munich", "id": "MUC"}],
            "total_duration": 345,
            "price": 210,
        }
    ],
    "other_flights": [
        {
            "flights": [
                {
                    "departure_airport": {"id": "BER", "time": "2026-09-10 07:00"},
                    "arrival_airport": {"id": "ATH", "time": "2026-09-10 10:15"},
                    "airline": "Aegean Airlines",
                }
            ],
            "layovers": [],
            "total_duration": 195,
            "price": 165,
        }
    ],
    "price_insights": {"lowest_price": 165},
}


def test_search_flights_parses_serpapi(monkeypatch):
    monkeypatch.setattr(flights_server, "_api_key", lambda: "test-key")
    captured = {}

    def fake_search(params):
        captured["params"] = params
        return _SERPAPI_FLIGHTS_FIXTURE

    monkeypatch.setattr(flights_server, "_serpapi_search", fake_search)
    result = flights_server.search_flights(
        "ber", "ath", "2026-09-10", passengers=2, max_stops=0, preferred_time="6-20", currency="EUR"
    )

    assert result["available"] is True
    assert result["estimated"] is False
    # Request mapping: one-way, sorted by price, direct-only stops=1, adults, currency, times.
    assert captured["params"]["type"] == 2
    assert captured["params"]["stops"] == 1  # max_stops=0 -> nonstop only
    assert captured["params"]["adults"] == 2
    assert captured["params"]["currency"] == "EUR"
    assert captured["params"]["outbound_times"] == "6,20"
    # Cheapest first; multi-segment parsed with layover count + ISO times.
    opts = result["options"]
    assert [o["price"] for o in opts] == [165.0, 210.0]
    cheapest = FlightOption(**opts[0])
    assert cheapest.stops == 0 and cheapest.airline == "Aegean Airlines"
    multi = FlightOption(**opts[1])
    assert multi.stops == 1
    assert multi.departure_time == "2026-09-10T09:00:00"
    assert multi.arrival_time == "2026-09-10T14:45:00"


def test_find_cheapest_dates_parses_serpapi(monkeypatch):
    monkeypatch.setattr(flights_server, "_api_key", lambda: "test-key")
    monkeypatch.setattr(flights_server, "_DATE_SAMPLES", 3)
    calls = []

    def fake_search(params):
        calls.append(params["outbound_date"])
        # Vary price by day so ranking is observable.
        price = 100 + len(calls) * 10
        return {"best_flights": [{"price": price, "flights": []}], "price_insights": {}}

    monkeypatch.setattr(flights_server, "_serpapi_search", fake_search)
    result = flights_server.find_cheapest_dates(
        "BER", "ATH", "2026-09-01", "2026-09-30", duration_days=7, currency="USD"
    )

    assert result["available"] is True
    assert len(calls) == 3  # bounded by _DATE_SAMPLES
    parsed = FlightDateOption(**result["options"][0])
    assert parsed.return_date is not None  # round trip carries a return date
    assert parsed.currency == "USD"
    assert result["options"] == sorted(result["options"], key=lambda o: o["price"])


# --- Adapter parsing (no subprocess) ------------------------------------------

class _FakeResult:
    isError = False

    def __init__(self, structured):
        self.structuredContent = structured
        self.content = []


@pytest.mark.asyncio
async def test_adapter_parses_flight_options_into_domain():
    adapter = MCPFlightServiceAdapter()
    captured = {}

    async def fake_call_tool(name, arguments):
        captured["name"] = name
        captured["arguments"] = arguments
        return _FakeResult(
            {
                "currency": "EUR",
                "estimated": False,
                "options": [
                    {
                        "origin": "BER",
                        "destination": "ATH",
                        "departure_time": "2026-09-10T10:00:00",
                        "arrival_time": "2026-09-10T13:00:00",
                        "duration_minutes": 180,
                        "stops": 0,
                        "airline": "Aegean Airlines",
                        "price": 142.0,
                        "currency": "EUR",
                        "estimated": False,
                    }
                ],
            }
        )

    adapter.session = MagicMock()
    adapter.session.call_tool = fake_call_tool

    options = await adapter.search_flights(
        "BER", "ATH", "2026-09-10", passengers=2, max_stops=0, currency="EUR"
    )
    assert captured["name"] == "search_flights"
    assert captured["arguments"]["max_stops"] == 0
    assert captured["arguments"]["currency"] == "EUR"
    assert len(options) == 1
    assert isinstance(options[0], FlightOption)
    assert options[0].airline == "Aegean Airlines"
    assert options[0].price == 142.0


# --- Agent tools --------------------------------------------------------------

class _StubFlightService(FlightServicePort):
    def __init__(self):
        self.calls = []

    async def search_flights(self, origin, destination, departure_date, **kwargs):
        self.calls.append(("search_flights", origin, destination, departure_date, kwargs))
        return [
            FlightOption(
                origin=origin,
                destination=destination,
                departure_time=f"{departure_date}T09:00:00",
                arrival_time=f"{departure_date}T12:00:00",
                duration_minutes=180,
                stops=0,
                airline="TestAir",
                price=99.0,
                currency=kwargs.get("currency", "EUR"),
            )
        ]

    async def find_cheapest_dates(self, origin, destination, **kwargs):
        self.calls.append(("find_cheapest_dates", origin, destination, kwargs))
        return [
            FlightDateOption(
                departure_date=kwargs["date_from"],
                return_date=None,
                price=88.0,
                currency=kwargs.get("currency", "EUR"),
            )
        ]


def _ctx(deps):
    return RunContext(deps=deps, model=MagicMock(), usage=MagicMock(), prompt="test")


@pytest.mark.asyncio
async def test_find_cheapest_dates_tool_uses_pref_currency_and_month():
    stub = _StubFlightService()
    deps = AgentDependencies(
        prompt_service=MagicMock(spec=PromptServicePort),
        user_preferences=UserPreferences(currency="USD"),
        flight_service=stub,
    )
    out = await find_cheapest_dates(_ctx(deps), "BER", "ATH", "2026-09", duration_days=10)
    assert out["currency"] == "USD"
    assert len(out["options"]) == 1
    _, _, _, kwargs = stub.calls[0]
    assert kwargs["date_from"] == "2026-09-01"
    assert kwargs["date_to"] == "2026-09-30"
    assert kwargs["currency"] == "USD"


@pytest.mark.asyncio
async def test_search_flights_tool_applies_direct_flights_preference():
    stub = _StubFlightService()
    deps = AgentDependencies(
        prompt_service=MagicMock(spec=PromptServicePort),
        user_preferences=UserPreferences(direct_flights_only=True),
        flight_service=stub,
    )
    out = await search_flights(_ctx(deps), "BER", "ATH", "2026-09-10")
    assert out["options"][0]["price"] == 99.0
    _, _, _, _, kwargs = stub.calls[0]
    assert kwargs["max_stops"] == 0  # direct_flights_only forced max_stops=0


@pytest.mark.asyncio
async def test_flight_tools_handle_missing_service():
    deps = AgentDependencies(prompt_service=MagicMock(spec=PromptServicePort), flight_service=None)
    out = await search_flights(_ctx(deps), "BER", "ATH", "2026-09-10")
    assert out["options"] == []
    assert "error" in out


# --- Grounded web-search tool -------------------------------------------------

@pytest.mark.asyncio
async def test_search_web_tool_delegates_with_currency(monkeypatch):
    captured = {}

    async def fake_run_research(query):
        captured["query"] = query
        return "BER→ATH ~120–160 USD, Aegean operates direct flights."

    monkeypatch.setattr(agent_mod, "run_research", fake_run_research)
    deps = AgentDependencies(
        prompt_service=MagicMock(spec=PromptServicePort),
        user_preferences=UserPreferences(currency="USD"),
    )
    out = await search_web(_ctx(deps), "cheapest flights BER to ATH in September")
    assert "USD" in captured["query"]  # preferred currency threaded into the query
    assert "Aegean" in out


@pytest.mark.asyncio
async def test_run_research_soft_fails_on_error(monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("grounding unavailable")

    monkeypatch.setattr(research_mod.research_agent, "run", boom)
    out = await research_mod.run_research("anything")
    assert "unavailable" in out.lower()
