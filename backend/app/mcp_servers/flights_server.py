"""Standalone Flights MCP server.

Exposes two tools over MCP stdio that the Kompass agent calls through the
``MCPFlightServiceAdapter``:

* ``search_flights``       — live flight options for a specific departure date
* ``find_cheapest_dates``  — ranked travel-date windows by price

Live data is sourced from Google Flights via the ``fli`` library (no API key
required). Because that endpoint is unofficial and network/rate-limit
dependent, every tool degrades gracefully to a deterministic *synthetic*
estimate so the agent — and the offline test suite — always get a usable
answer. Synthetic results are flagged with ``estimated: true``.

The Google Flights endpoint intermittently answers a valid request with an
HTTP 200 whose body is a gRPC ``INTERNAL`` error envelope instead of flight
rows (see punitarani/fli issue #200). ``fli`` 0.9.0 does not retry these (the
HTTP status is 200), so a single transient blip would otherwise force a
synthetic fallback. We therefore retry the live call a few times with backoff
before giving up — this is what keeps real data flowing most of the time.
"""

import hashlib
import logging
import os
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("kompass.flights_mcp")

mcp = FastMCP("FlightsServer")

# Retry tuning for the flaky live endpoint (overridable via env for ops).
_LIVE_MAX_ATTEMPTS = max(1, int(os.getenv("FLIGHTS_LIVE_MAX_ATTEMPTS", "4")))
_LIVE_BACKOFF_BASE = max(0.0, float(os.getenv("FLIGHTS_LIVE_BACKOFF_BASE", "0.4")))


def _live_with_retries(fetch: Callable[[], list[dict]], label: str) -> list[dict]:
    """Call a live fetch, retrying transient empty/error responses with backoff.

    Returns the first non-empty result, or ``[]`` once attempts are exhausted
    (the caller then falls back to a synthetic estimate). Genuinely empty
    routes simply cost a few cheap retries before the fallback.
    """
    last_error: Exception | None = None
    for attempt in range(1, _LIVE_MAX_ATTEMPTS + 1):
        try:
            options = fetch()
            if options:
                if attempt > 1:
                    logger.info(f"{label}: live data recovered on attempt {attempt}.")
                return options
            logger.info(f"{label}: empty live result (attempt {attempt}/{_LIVE_MAX_ATTEMPTS}).")
        except Exception as e:  # noqa: BLE001 - transient provider errors are expected
            last_error = e
            logger.info(
                f"{label}: live error on attempt {attempt}/{_LIVE_MAX_ATTEMPTS}: {e}"
            )
        if attempt < _LIVE_MAX_ATTEMPTS and _LIVE_BACKOFF_BASE:
            time.sleep(_LIVE_BACKOFF_BASE * (2 ** (attempt - 1)))
    if last_error is not None:
        logger.warning(f"{label}: exhausted live retries; last error: {last_error}")
    else:
        logger.warning(f"{label}: exhausted live retries with no results.")
    return []

# Airlines used for synthetic estimates, chosen deterministically per-route.
_SYNTHETIC_AIRLINES = [
    "Aegean Airlines",
    "Lufthansa",
    "Ryanair",
    "easyJet",
    "KLM",
    "Air France",
    "ITA Airways",
    "Wizz Air",
]


# --- Input mapping helpers ----------------------------------------------------

def _map_max_stops(max_stops: int | None):
    """Map an integer stop limit to the fli ``MaxStops`` enum."""
    from fli.models import MaxStops

    if max_stops is None:
        return MaxStops.ANY
    if max_stops <= 0:
        return MaxStops.NON_STOP
    if max_stops == 1:
        return MaxStops.ONE_STOP_OR_FEWER
    return MaxStops.TWO_OR_FEWER_STOPS


def _parse_time_window(preferred_time: str | None) -> tuple[int, int] | None:
    """Parse a 'HH-HH' departure window into (earliest_hour, latest_hour)."""
    if not preferred_time or "-" not in preferred_time:
        return None
    try:
        start_s, end_s = preferred_time.split("-", 1)
        start, end = int(start_s.strip()), int(end_s.strip())
    except ValueError:
        return None
    if 0 <= start < end <= 24:
        return start, min(end, 23)
    return None


def _airport(code: str):
    """Resolve a 3-letter IATA code to the fli ``Airport`` enum (raises if unknown)."""
    from fli.models import Airport

    return Airport[code.strip().upper()]


# --- Synthetic fallback -------------------------------------------------------

def _route_seed(*parts: str) -> int:
    raw = "|".join(parts).upper().encode()
    return int(hashlib.sha256(raw).hexdigest(), 16)


def _synthetic_flights(
    origin: str,
    destination: str,
    departure_date: str,
    passengers: int,
    max_stops: int | None,
    currency: str,
) -> list[dict]:
    """Deterministic, plausible flight options when live data is unavailable."""
    seed = _route_seed(origin, destination, departure_date)
    base_price = 80 + (seed % 320)  # 80..399 per passenger
    base_duration = 110 + (seed % 220)  # 110..329 minutes
    dep_day = _safe_date(departure_date) or date.today()

    options: list[dict] = []
    n = 3
    for i in range(n):
        stops = 0 if (max_stops == 0 or i == 0) else (i % ((max_stops or 2) + 1))
        dep_hour = 6 + ((seed >> (i + 1)) % 14)  # 6..19
        duration = base_duration + stops * 75 + i * 20
        dep_dt = datetime.combine(dep_day, datetime.min.time()).replace(hour=dep_hour)
        arr_dt = dep_dt + timedelta(minutes=duration)
        per_pax = base_price + stops * 35 - (i * 10)
        airline = _SYNTHETIC_AIRLINES[(seed + i) % len(_SYNTHETIC_AIRLINES)]
        options.append(
            {
                "origin": origin.upper(),
                "destination": destination.upper(),
                "departure_time": dep_dt.isoformat(),
                "arrival_time": arr_dt.isoformat(),
                "duration_minutes": duration,
                "stops": stops,
                "airline": airline,
                "price": round(float(max(per_pax, 35)) * max(passengers, 1), 2),
                "currency": currency,
                "estimated": True,
            }
        )
    options.sort(key=lambda o: o["price"])
    return options


def _synthetic_cheapest_dates(
    origin: str,
    destination: str,
    date_from: str,
    date_to: str,
    duration_days: int | None,
    currency: str,
) -> list[dict]:
    """Deterministic, plausible cheapest-date windows when live data is unavailable."""
    start = _safe_date(date_from) or date.today()
    end = _safe_date(date_to) or (start + timedelta(days=30))
    if end < start:
        end = start + timedelta(days=30)

    seed = _route_seed(origin, destination)
    base_price = 120 + (seed % 260)
    span = (end - start).days or 1
    step = max(span // 12, 1)

    options: list[dict] = []
    d = start
    while d <= end:
        wobble = ((_route_seed(origin, destination, d.isoformat()) % 140) - 70)
        price = round(float(max(base_price + wobble, 49)), 2)
        ret = (d + timedelta(days=duration_days)).isoformat() if duration_days else None
        options.append(
            {
                "departure_date": d.isoformat(),
                "return_date": ret,
                "price": price,
                "currency": currency,
                "estimated": True,
            }
        )
        d += timedelta(days=step)
    options.sort(key=lambda o: o["price"])
    return options[:10]


def _safe_date(value: str) -> date | None:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


# --- Live providers (fli / Google Flights) ------------------------------------

def _live_flights(
    origin: str,
    destination: str,
    departure_date: str,
    passengers: int,
    max_stops: int | None,
    preferred_time: str | None,
    currency: str,
) -> list[dict]:
    """Fetch live flight options from Google Flights via fli. May raise."""
    from fli.models import (
        FlightSearchFilters,
        FlightSegment,
        PassengerInfo,
        SeatType,
        SortBy,
        TimeRestrictions,
    )
    from fli.search import SearchFlights

    window = _parse_time_window(preferred_time)
    time_restrictions = (
        TimeRestrictions(earliest_departure=window[0], latest_departure=window[1])
        if window
        else None
    )
    segment = FlightSegment(
        departure_airport=[[_airport(origin), 0]],
        arrival_airport=[[_airport(destination), 0]],
        travel_date=departure_date,
        time_restrictions=time_restrictions,
    )
    filters = FlightSearchFilters(
        passenger_info=PassengerInfo(adults=max(passengers, 1)),
        flight_segments=[segment],
        stops=_map_max_stops(max_stops),
        seat_type=SeatType.ECONOMY,
        sort_by=SortBy.CHEAPEST,
    )
    results = SearchFlights().search(filters, top_n=5, currency=currency) or []

    options: list[dict] = []
    for result in results:
        # One-way searches yield FlightResult; guard against tuples just in case.
        if isinstance(result, tuple):
            result = result[0]
        legs = result.legs or []
        if not legs:
            continue
        first, last = legs[0], legs[-1]
        options.append(
            {
                "origin": first.departure_airport.name,
                "destination": last.arrival_airport.name,
                "departure_time": first.departure_datetime.isoformat(),
                "arrival_time": last.arrival_datetime.isoformat(),
                "duration_minutes": int(result.duration or 0),
                "stops": int(result.stops or 0),
                "airline": result.primary_airline_name
                or (result.primary_airline.value if result.primary_airline else "Unknown"),
                "price": round(float(result.price or 0.0), 2),
                "currency": result.currency or currency,
                "estimated": False,
            }
        )
    return options


def _live_cheapest_dates(
    origin: str,
    destination: str,
    date_from: str,
    date_to: str,
    duration_days: int | None,
    currency: str,
) -> list[dict]:
    """Fetch live cheapest-date windows from Google Flights via fli. May raise."""
    from fli.models import (
        FlightSegment,
        MaxStops,
        PassengerInfo,
        SeatType,
        TripType,
    )
    from fli.models.google_flights.dates import DateSearchFilters
    from fli.search import SearchDates

    dep, arr = _airport(origin), _airport(destination)
    segments = [
        FlightSegment(
            departure_airport=[[dep, 0]],
            arrival_airport=[[arr, 0]],
            travel_date=date_from,
        )
    ]
    # Round-trip date searches require an explicit return segment, otherwise fli
    # rejects the filter ("Round trip must have two flight segments").
    if duration_days:
        segments.append(
            FlightSegment(
                departure_airport=[[arr, 0]],
                arrival_airport=[[dep, 0]],
                travel_date=date_to,
            )
        )
    filters = DateSearchFilters(
        trip_type=TripType.ROUND_TRIP if duration_days else TripType.ONE_WAY,
        passenger_info=PassengerInfo(adults=1),
        flight_segments=segments,
        stops=MaxStops.ANY,
        seat_type=SeatType.ECONOMY,
        from_date=date_from,
        to_date=date_to,
        duration=duration_days,
    )
    results = SearchDates().search(filters, currency=currency) or []

    options: list[dict] = []
    for dp in results:
        dep = dp.date[0]
        ret = dp.date[1] if len(dp.date) > 1 else None
        options.append(
            {
                "departure_date": dep.date().isoformat(),
                "return_date": ret.date().isoformat() if ret else None,
                "price": round(float(dp.price or 0.0), 2),
                "currency": dp.currency or currency,
                "estimated": False,
            }
        )
    options.sort(key=lambda o: o["price"])
    return options


# --- MCP tools ----------------------------------------------------------------

@mcp.tool()
def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    passengers: int = 1,
    max_stops: int | None = None,
    preferred_time: str | None = None,
    currency: str = "EUR",
) -> dict:
    """Search one-way flight options for a specific date.

    Args:
        origin: Departure airport IATA code (e.g. 'BER').
        destination: Arrival airport IATA code (e.g. 'ATH').
        departure_date: Outbound date in YYYY-MM-DD format.
        passengers: Number of adult passengers.
        max_stops: Maximum stops (0 = direct only). Omit for no limit.
        preferred_time: Departure window as 'HH-HH' (e.g. '6-20').
        currency: ISO 4217 currency code for prices (defaults to EUR).

    Returns:
        dict with keys: options (list), currency (str), estimated (bool).
    """
    options = _live_with_retries(
        lambda: _live_flights(
            origin, destination, departure_date, passengers, max_stops, preferred_time, currency
        ),
        label=f"search_flights {origin}->{destination} {departure_date}",
    )
    if options:
        return {"options": options, "currency": currency, "estimated": False}

    logger.warning("Live flight search unavailable; using synthetic estimate.")
    options = _synthetic_flights(
        origin, destination, departure_date, passengers, max_stops, currency
    )
    return {"options": options, "currency": currency, "estimated": True}


@mcp.tool()
def find_cheapest_dates(
    origin: str,
    destination: str,
    date_from: str,
    date_to: str,
    duration_days: int | None = None,
    currency: str = "EUR",
) -> dict:
    """Find the cheapest travel-date windows within a date range.

    Args:
        origin: Departure airport IATA code.
        destination: Arrival airport IATA code.
        date_from: Start of search window (YYYY-MM-DD).
        date_to: End of search window (YYYY-MM-DD).
        duration_days: Trip length in days for round-trip pricing (omit for one-way).
        currency: ISO 4217 currency code for prices (defaults to EUR).

    Returns:
        dict with keys: options (list, cheapest first), currency (str), estimated (bool).
    """
    options = _live_with_retries(
        lambda: _live_cheapest_dates(
            origin, destination, date_from, date_to, duration_days, currency
        ),
        label=f"find_cheapest_dates {origin}->{destination} {date_from}..{date_to}",
    )
    if options:
        return {"options": options, "currency": currency, "estimated": False}

    logger.warning("Live date search unavailable; using synthetic estimate.")
    options = _synthetic_cheapest_dates(
        origin, destination, date_from, date_to, duration_days, currency
    )
    return {"options": options, "currency": currency, "estimated": True}


if __name__ == "__main__":
    mcp.run()
