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


# --- Synthetic fallback (offline, deterministic) ------------------------------

def test_synthetic_flights_shape_and_determinism():
    a = flights_server._synthetic_flights("BER", "ATH", "2026-09-10", 2, None, "EUR")
    b = flights_server._synthetic_flights("BER", "ATH", "2026-09-10", 2, None, "EUR")
    assert a == b  # deterministic
    assert len(a) >= 1
    opt = FlightOption(**a[0])  # validates against the domain schema
    assert opt.estimated is True
    assert opt.currency == "EUR"
    assert a == sorted(a, key=lambda o: o["price"])  # cheapest first


def test_synthetic_flights_direct_only():
    opts = flights_server._synthetic_flights("BER", "ATH", "2026-09-10", 1, 0, "EUR")
    assert all(o["stops"] == 0 for o in opts)


def test_synthetic_cheapest_dates_round_trip_returns_dates():
    opts = flights_server._synthetic_cheapest_dates(
        "BER", "ATH", "2026-09-01", "2026-09-30", 7, "GBP"
    )
    assert len(opts) >= 1
    parsed = FlightDateOption(**opts[0])
    assert parsed.return_date is not None
    assert parsed.currency == "GBP"
    assert opts == sorted(opts, key=lambda o: o["price"])


def test_search_flights_tool_falls_back_to_synthetic(monkeypatch):
    monkeypatch.setattr(flights_server, "_LIVE_BACKOFF_BASE", 0.0)

    def boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(flights_server, "_live_flights", boom)
    result = flights_server.search_flights("BER", "ATH", "2026-09-10", currency="EUR")
    assert result["estimated"] is True
    assert len(result["options"]) >= 1


def test_search_flights_tool_retries_transient_failures(monkeypatch):
    """A transient blip (empty/error) is retried; a later success yields real data."""
    monkeypatch.setattr(flights_server, "_LIVE_BACKOFF_BASE", 0.0)
    monkeypatch.setattr(flights_server, "_LIVE_MAX_ATTEMPTS", 4)
    calls = {"n": 0}

    real_option = {
        "origin": "BER",
        "destination": "ATH",
        "departure_time": "2026-09-10T09:00:00",
        "arrival_time": "2026-09-10T12:00:00",
        "duration_minutes": 180,
        "stops": 0,
        "airline": "Aegean Airlines",
        "price": 120.0,
        "currency": "EUR",
        "estimated": False,
    }

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient gRPC INTERNAL")
        if calls["n"] == 2:
            return []  # transient empty envelope
        return [real_option]

    monkeypatch.setattr(flights_server, "_live_flights", flaky)
    result = flights_server.search_flights("BER", "ATH", "2026-09-10", currency="EUR")
    assert result["estimated"] is False
    assert calls["n"] == 3
    assert result["options"][0]["airline"] == "Aegean Airlines"


def test_live_with_retries_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr(flights_server, "_LIVE_BACKOFF_BASE", 0.0)
    monkeypatch.setattr(flights_server, "_LIVE_MAX_ATTEMPTS", 3)
    attempts = {"n": 0}

    def always_empty():
        attempts["n"] += 1
        return []

    out = flights_server._live_with_retries(always_empty, "test")
    assert out == []
    assert attempts["n"] == 3


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
