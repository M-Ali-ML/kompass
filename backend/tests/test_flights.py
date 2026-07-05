from datetime import datetime

import pytest
from unittest.mock import AsyncMock, MagicMock

from pydantic_ai import RunContext

import app.agent.research_agent as research_mod
from app.agent.agent import _month_to_range, find_cheapest_dates, search_flights, search_web
from app.agent.dependency import AgentDependencies
from app.adapters import mcp_flight_service
from app.adapters.mcp_flight_service import (
    KiwiMCPFlightServiceAdapter,
    KiwiTransportError,
    _describe_exception,
    _extract_items,
)
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


# --- Transport-failure vs. genuine-empty distinction ---------------------------

def test_describe_exception_unwraps_exception_groups():
    group = ExceptionGroup("unhandled errors in a TaskGroup", [ConnectionError("boom")])
    assert _describe_exception(group) == "ConnectionError: boom"


def test_describe_exception_recurses_nested_groups():
    inner = ExceptionGroup("inner", [TimeoutError("slow")])
    outer = ExceptionGroup("outer", [inner])
    assert _describe_exception(outer) == "TimeoutError: slow"


def test_describe_exception_plain_exception():
    assert _describe_exception(ValueError("bad")) == "ValueError: bad"


@pytest.mark.asyncio
async def test_search_raises_transport_error_after_retry_exhausted(monkeypatch):
    """A connection failure on both attempts must raise KiwiTransportError, not
    silently degrade to [] — that's what made a dead Kiwi connection look
    identical to "no flights on this route" (see mcp_flight_service.py docstring).
    """
    adapter = KiwiMCPFlightServiceAdapter(url="http://test")
    monkeypatch.setattr(mcp_flight_service.asyncio, "sleep", AsyncMock())

    async def fake_wait_for(coro, timeout):
        coro.close()
        raise ExceptionGroup("unhandled errors in a TaskGroup", [ConnectionError("dead socket")])

    monkeypatch.setattr(mcp_flight_service.asyncio, "wait_for", fake_wait_for)

    with pytest.raises(KiwiTransportError, match="ConnectionError: dead socket"):
        await adapter._search({"flyFrom": "BER", "flyTo": "ATH"})


@pytest.mark.asyncio
async def test_search_raises_transport_error_on_is_error_result(monkeypatch):
    adapter = KiwiMCPFlightServiceAdapter(url="http://test")

    async def fake_wait_for(coro, timeout):
        coro.close()
        return _Result(text="Error searching flights: rate limited", is_error=True)

    monkeypatch.setattr(mcp_flight_service.asyncio, "wait_for", fake_wait_for)

    with pytest.raises(KiwiTransportError):
        await adapter._search({"flyFrom": "BER", "flyTo": "ATH"})


@pytest.mark.asyncio
async def test_search_flights_tool_flags_data_source_error(monkeypatch):
    class FlakyFlightService(FlightServicePort):
        async def search_flights(self, *args, **kwargs):
            raise KiwiTransportError("ConnectionError: dead socket")

        async def find_cheapest_dates(self, *args, **kwargs):
            raise KiwiTransportError("ConnectionError: dead socket")

    deps = AgentDependencies(
        prompt_service=MagicMock(spec=PromptServicePort),
        flight_service=FlakyFlightService(),
    )
    out = await search_flights(_ctx(deps), "BER", "ATH", "2026-09-10")
    assert out["options"] == []
    assert out["estimated"] is False
    assert out["data_source_error"] is True


@pytest.mark.asyncio
async def test_find_cheapest_dates_tool_flags_data_source_error():
    class FlakyFlightService(FlightServicePort):
        async def search_flights(self, *args, **kwargs):
            raise KiwiTransportError("boom")

        async def find_cheapest_dates(self, *args, **kwargs):
            raise KiwiTransportError("boom")

    deps = AgentDependencies(
        prompt_service=MagicMock(spec=PromptServicePort),
        flight_service=FlakyFlightService(),
    )
    out = await find_cheapest_dates(_ctx(deps), "BER", "ATH", "2026-09")
    assert out["options"] == []
    assert out["data_source_error"] is True


# --- Kiwi adapter: search_flights ---------------------------------------------

def _segment(frm, to, from_city, to_city, carrier="FR"):
    return {
        "from": frm, "to": to, "fromCity": from_city, "toCity": to_city,
        "departureTime": "2026-09-10T09:00:00", "arrivalTime": "2026-09-10T11:00:00",
        "durationSeconds": 7200, "carrier": carrier, "flightNumber": f"{carrier}123",
        "cabinClass": "Economy",
    }


def _kiwi_item(*, dep_local, arr_local, price, layover_cities, deep="https://kiwi.com/u/X",
               dur=11700, carriers=None):
    """Build a new-schema Kiwi itinerary (outbound leg only, one-way).

    ``layover_cities`` is a list of intermediate city names; the outbound leg is
    given one more segment than there are layovers. ``carriers`` optionally sets
    the per-segment carrier IATA codes (defaults to a single 'FR' throughout).
    """
    route = ["BER"] + [c[:3].upper() for c in layover_cities] + ["ATH"]
    cities = list(layover_cities) + ["Athens"]
    seg_carriers = carriers or ["FR"] * len(cities)
    segments = []
    prev_code, prev_city = "BER", "Berlin"
    for city, carrier in zip(cities, seg_carriers):
        code = "ATH" if city == "Athens" else city[:3].upper()
        segments.append(_segment(prev_code, code, prev_city, city, carrier))
        prev_code, prev_city = code, city
    return {
        "id": "abc_0|def_0",
        "price": price,
        "priceFormatted": f"{price} EUR",
        "totalDurationSeconds": dur,
        "bookingUrl": deep,
        "outbound": {
            "from": "BER", "to": "ATH",
            "departureTime": dep_local, "arrivalTime": arr_local,
            "durationSeconds": dur, "stops": len(layover_cities),
            "route": route, "cabinClass": "Economy", "segments": segments,
        },
        "inbound": None,
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
                price=140, layover_cities=["Munich"], deep=".../BBB", dur=20700,
                carriers=["LH", "A3"],  # multi-carrier self-transfer
            ),
            _kiwi_item(
                dep_local="2026-09-10T07:00:00", arr_local="2026-09-10T10:15:00",
                price=165, layover_cities=[], deep=".../AAA", dur=11700,
                carriers=["FR"],  # single-carrier direct
            ),
        ]

    adapter._search = fake_search
    options = await adapter.search_flights(
        "ber", "ath", "2026-09-10", passengers=2, currency="EUR"
    )

    # Outgoing Kiwi args: upper-cased IATA, dd/mm/yyyy date, flat adults + currency.
    args = captured["args"]
    assert args["flyFrom"] == "BER" and args["flyTo"] == "ATH"
    assert args["departureDate"] == "10/09/2026"
    assert args["adults"] == 2
    assert args["currency"] == "EUR"

    # Cheapest-first; airline carries the real operating carrier IATA code(s).
    assert [o.price for o in options] == [140.0, 165.0]
    cheapest = options[0]
    assert isinstance(cheapest, FlightOption)
    assert cheapest.stops == 1
    assert cheapest.airline == "LH / A3"  # slash-joined multi-carrier
    assert cheapest.booking_link == ".../BBB"
    assert cheapest.duration_minutes == 345
    assert cheapest.departure_time == "2026-09-10T09:00:00"  # ISO, millis stripped
    assert options[1].airline == "FR"  # single carrier


@pytest.mark.asyncio
async def test_search_flights_filters_max_stops():
    adapter = KiwiMCPFlightServiceAdapter(url="http://test")

    async def fake_search(arguments):
        return [
            _kiwi_item(dep_local="2026-09-10T09:00:00", arr_local="2026-09-10T14:45:00",
                       price=140, layover_cities=["Munich"]),
            _kiwi_item(dep_local="2026-09-10T07:00:00", arr_local="2026-09-10T10:15:00",
                       price=165, layover_cities=[]),
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
                       price=165, layover_cities=[]),
            _kiwi_item(dep_local="2026-09-10T21:00:00", arr_local="2026-09-11T00:15:00",
                       price=120, layover_cities=[]),
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
            {"outbound": {"departureTime": d.isoformat() + "T08:00:00"},
             "inbound": {"departureTime": d.isoformat() + "T18:00:00"},
             "price": 100 + len(calls) * 10, "currency": "USD"},
            {"outbound": {"departureTime": "2026-09-20T09:00:00"},
             "inbound": {"departureTime": "2026-09-27T19:00:00"},
             "price": 300 - len(calls) * 10, "currency": "USD"},
        ]

    adapter._search = fake_search
    options = await adapter.find_cheapest_dates(
        "BER", "ATH", date_from="2026-09-01", date_to="2026-09-30",
        duration_days=7, currency="USD",
    )

    # Month sampled in ~7-day steps, bounded by _DATE_SAMPLES.
    assert len(calls) == 5
    # Round-trip args carry a flex-ranged return date.
    assert calls[0]["departureDateFlexDays"] == 3
    assert calls[0]["returnDateFlexDays"] == 3
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
            {"outbound": {"departureTime": "2026-08-30T08:00:00"}, "price": 50},
            {"outbound": {"departureTime": "2026-09-05T08:00:00"}, "price": 90},
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
async def test_search_web_tool_delegates_with_currency():
    from app.ports.research_service import ResearchServicePort

    captured = {}

    class FakeResearchService(ResearchServicePort):
        async def research(self, query: str) -> str:
            captured["query"] = query
            return "BER→ATH ~120–160 USD, Aegean operates direct flights."

    deps = AgentDependencies(
        prompt_service=MagicMock(spec=PromptServicePort),
        user_preferences=UserPreferences(currency="USD"),
        research_service=FakeResearchService(),
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
