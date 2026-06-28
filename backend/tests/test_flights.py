from datetime import datetime

import pytest
from unittest.mock import MagicMock

from pydantic_ai import RunContext

import app.agent.agent as agent_mod
import app.agent.research_agent as research_mod
from app.agent.agent import _month_to_range, find_cheapest_dates, search_flights, search_web
from app.agent.dependency import AgentDependencies
from app.adapters import mcp_flight_service
from app.adapters.mcp_flight_service import KiwiMCPFlightServiceAdapter, _extract_items
from app.domain import FlightDateOption, FlightOption, UserPreferences
from app.ports.flight_service import FlightServicePort
from app.ports.prompt_service import PromptServicePort


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


# --- Kiwi result extraction ---------------------------------------------------

class _Text:
    def __init__(self, text):
        self.text = text


class _Result:
    def __init__(self, *, text=None, structured=None, is_error=False):
        self.isError = is_error
        self.structuredContent = structured
        self.content = [_Text(text)] if text is not None else []


def test_extract_items_parses_json_text_array():
    items = _extract_items(_Result(text='[{"price": 100}, {"price": 200}]'))
    assert [it["price"] for it in items] == [100, 200]


def test_extract_items_returns_empty_on_error_string():
    # Kiwi surfaces some failures as a plain (non-JSON) message — treat as no data.
    assert _extract_items(_Result(text="Error searching flights: boom")) == []
    assert _extract_items(_Result()) == []


# --- Kiwi adapter: search_flights ---------------------------------------------

def _kiwi_item(*, dep_local, arr_local, price, layovers, deep="https://on.kiwi.com/X", dur=11700):
    return {
        "flyFrom": "BER",
        "flyTo": "ATH",
        "cityFrom": "Berlin",
        "cityTo": "Athens",
        "departure": {"utc": dep_local + "Z", "local": dep_local + ".000"},
        "arrival": {"utc": arr_local + "Z", "local": arr_local + ".000"},
        "totalDurationInSeconds": dur,
        "price": price,
        "currency": "EUR",
        "deepLink": deep,
        "layovers": layovers,
    }


@pytest.mark.asyncio
async def test_search_flights_maps_args_and_options():
    adapter = KiwiMCPFlightServiceAdapter(url="http://test")
    captured = {}

    async def fake_search(arguments):
        captured["args"] = arguments
        return [
            _kiwi_item(
                dep_local="2026-09-10T09:00:00", arr_local="2026-09-10T14:45:00",
                price=140, layovers=[{"at": "MUC", "city": "Munich"}], deep=".../BBB", dur=20700,
            ),
            _kiwi_item(
                dep_local="2026-09-10T07:00:00", arr_local="2026-09-10T10:15:00",
                price=165, layovers=[], deep=".../AAA", dur=11700,
            ),
        ]

    adapter._search = fake_search
    options = await adapter.search_flights(
        "ber", "ath", "2026-09-10", passengers=2, currency="EUR"
    )

    # Outgoing Kiwi args: upper-cased IATA, dd/mm/yyyy date, adults, currency, price sort.
    args = captured["args"]
    assert args["flyFrom"] == "BER" and args["flyTo"] == "ATH"
    assert args["departureDate"] == "10/09/2026"
    assert args["passengers"] == {"adults": 2}
    assert args["curr"] == "EUR"
    assert args["sort"] == "price"

    # Cheapest-first; routing label stands in for the (absent) carrier name.
    assert [o.price for o in options] == [140.0, 165.0]
    cheapest = options[0]
    assert isinstance(cheapest, FlightOption)
    assert cheapest.stops == 1
    assert cheapest.airline == "via Munich"
    assert cheapest.booking_link == ".../BBB"
    assert cheapest.duration_minutes == 345
    assert cheapest.departure_time == "2026-09-10T09:00:00"  # ISO, millis stripped
    assert options[1].airline == "Direct"


@pytest.mark.asyncio
async def test_search_flights_filters_max_stops():
    adapter = KiwiMCPFlightServiceAdapter(url="http://test")

    async def fake_search(arguments):
        return [
            _kiwi_item(dep_local="2026-09-10T09:00:00", arr_local="2026-09-10T14:45:00",
                       price=140, layovers=[{"at": "MUC", "city": "Munich"}]),
            _kiwi_item(dep_local="2026-09-10T07:00:00", arr_local="2026-09-10T10:15:00",
                       price=165, layovers=[]),
        ]

    adapter._search = fake_search
    options = await adapter.search_flights("BER", "ATH", "2026-09-10", max_stops=0)
    assert len(options) == 1
    assert options[0].stops == 0


@pytest.mark.asyncio
async def test_search_flights_filters_preferred_time():
    adapter = KiwiMCPFlightServiceAdapter(url="http://test")

    async def fake_search(arguments):
        return [
            _kiwi_item(dep_local="2026-09-10T07:00:00", arr_local="2026-09-10T10:15:00",
                       price=165, layovers=[]),
            _kiwi_item(dep_local="2026-09-10T21:00:00", arr_local="2026-09-11T00:15:00",
                       price=120, layovers=[]),
        ]

    adapter._search = fake_search
    options = await adapter.search_flights("BER", "ATH", "2026-09-10", preferred_time="6-9")
    assert [o.departure_time for o in options] == ["2026-09-10T07:00:00"]


@pytest.mark.asyncio
async def test_search_flights_invalid_date_degrades():
    adapter = KiwiMCPFlightServiceAdapter(url="http://test")

    async def boom(arguments):  # pragma: no cover - must not be reached
        raise AssertionError("invalid date must short-circuit before any network call")

    adapter._search = boom
    assert await adapter.search_flights("BER", "ATH", "not-a-date") == []


@pytest.mark.asyncio
async def test_search_flights_empty_result_degrades():
    adapter = KiwiMCPFlightServiceAdapter(url="http://test")

    async def fake_search(arguments):
        return []

    adapter._search = fake_search
    assert await adapter.search_flights("BER", "ATH", "2026-09-10") == []


# --- Kiwi adapter: find_cheapest_dates (concurrent flex-window sampling) -------

@pytest.mark.asyncio
async def test_find_cheapest_dates_samples_and_aggregates(monkeypatch):
    monkeypatch.setattr(mcp_flight_service, "_DATE_SAMPLES", 5)
    adapter = KiwiMCPFlightServiceAdapter(url="http://test")
    calls = []

    async def fake_search(arguments):
        calls.append(arguments)
        d = datetime.strptime(arguments["departureDate"], "%d/%m/%Y").date()
        # One option on the sample's own date, plus a shared off-sample date whose
        # price drops on each call so cheapest-per-date dedupe is observable.
        return [
            {"departure": {"local": d.isoformat() + "T08:00:00.000"},
             "price": 100 + len(calls) * 10, "currency": "USD", "layovers": []},
            {"departure": {"local": "2026-09-20T09:00:00.000"},
             "price": 300 - len(calls) * 10, "currency": "USD", "layovers": []},
        ]

    adapter._search = fake_search
    options = await adapter.find_cheapest_dates(
        "BER", "ATH", date_from="2026-09-01", date_to="2026-09-30",
        duration_days=7, currency="USD",
    )

    # Month sampled in ~7-day steps, bounded by _DATE_SAMPLES.
    assert len(calls) == 5
    # Round-trip args carry a flex-ranged return date.
    assert calls[0]["departureDateFlexRange"] == 3
    assert calls[0]["returnDateFlexRange"] == 3
    assert "returnDate" in calls[0]

    assert all(isinstance(o, FlightDateOption) for o in options)
    # Cheapest-first ranking.
    assert [o.price for o in options] == sorted(o.price for o in options)
    # The shared date collapses to its minimum across the 5 calls (300 - 5*10).
    shared = next(o for o in options if o.departure_date == "2026-09-20")
    assert shared.price == 250.0
    # Round-trip → a return date is derived.
    assert shared.return_date is not None
    assert shared.currency == "USD"


@pytest.mark.asyncio
async def test_find_cheapest_dates_filters_out_of_range_dates():
    adapter = KiwiMCPFlightServiceAdapter(url="http://test")

    async def fake_search(arguments):
        # Flex can return dates just outside the window; those must be dropped.
        return [
            {"departure": {"local": "2026-08-30T08:00:00.000"}, "price": 50, "layovers": []},
            {"departure": {"local": "2026-09-05T08:00:00.000"}, "price": 90, "layovers": []},
        ]

    adapter._search = fake_search
    options = await adapter.find_cheapest_dates(
        "BER", "ATH", date_from="2026-09-01", date_to="2026-09-30", currency="EUR"
    )
    dates = {o.departure_date for o in options}
    assert "2026-08-30" not in dates
    assert "2026-09-05" in dates


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
                airline="Direct",
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
    # booking_link is surfaced in the tool payload for the frontend card.
    assert "booking_link" in out["options"][0]
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
