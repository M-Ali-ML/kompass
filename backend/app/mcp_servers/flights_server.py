"""Standalone Flights MCP server — SerpApi Google Flights provider.

Exposes two tools over MCP stdio that the Kompass agent calls through the
``MCPFlightServiceAdapter``:

* ``search_flights``       — live flight options for a specific departure date
* ``find_cheapest_dates``  — ranked travel-date windows by price

Live data comes from **SerpApi's Google Flights API** (https://serpapi.com/google-flights-api),
which returns structured Google Flights results. This replaces the previous
``fli`` scraper + synthetic fallback (unreliable / misleading fake prices).

Reliability contract: if ``SERPAPI_API_KEY`` is missing, or SerpApi errors /
returns nothing, the tools return ``available: false`` with **no fabricated
data** so the agent falls back to the grounded ``search_web`` tool. We never
invent prices.

The API key is read from the environment (``SERPAPI_API_KEY``); the parent app
exports it via ``app.config`` and the MCP subprocess inherits the environment.
"""

import logging
import os
from datetime import date, datetime, timedelta

import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("kompass.flights_mcp")

mcp = FastMCP("FlightsServer")

_SERPAPI_ENDPOINT = "https://serpapi.com/search"
_TIMEOUT = float(os.getenv("SERPAPI_TIMEOUT", "25"))
_TOP_N = max(1, int(os.getenv("FLIGHTS_TOP_N", "5")))
# How many candidate dates to probe across a cheapest-dates range. Each costs one
# SerpApi call, so keep it modest (overridable for ops via FLIGHTS_DATE_SAMPLES).
_DATE_SAMPLES = max(2, int(os.getenv("FLIGHTS_DATE_SAMPLES", "4")))

_UNAVAILABLE_NOTE = (
    "Structured flight data is currently unavailable. "
    "Use the search_web tool for live price ranges and travel dates."
)


def _api_key() -> str | None:
    key = os.getenv("SERPAPI_API_KEY")
    return key.strip() if key and key.strip() else None


def _unavailable(currency: str, note: str = _UNAVAILABLE_NOTE) -> dict:
    """A no-data result. The agent should fall back to search_web for prices."""
    return {
        "options": [],
        "currency": currency,
        "estimated": False,
        "available": False,
        "note": note,
    }


# --- Helpers ------------------------------------------------------------------

def _map_stops(max_stops: int | None) -> int:
    """Map an integer stop limit to the SerpApi ``stops`` enum.

    SerpApi: 0=Any, 1=Nonstop only, 2=1 stop or fewer, 3=2 stops or fewer.
    """
    if max_stops is None:
        return 0
    if max_stops <= 0:
        return 1
    if max_stops == 1:
        return 2
    return 3


def _outbound_times(preferred_time: str | None) -> str | None:
    """Convert a 'HH-HH' departure window into SerpApi ``outbound_times`` ('h1,h2')."""
    if not preferred_time or "-" not in preferred_time:
        return None
    try:
        start_s, end_s = preferred_time.split("-", 1)
        start, end = int(start_s.strip()), int(end_s.strip())
    except ValueError:
        return None
    if 0 <= start < end <= 24:
        return f"{start},{min(end, 23)}"
    return None


def _safe_date(value: str) -> date | None:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _to_iso(serpapi_time: str | None) -> str:
    """Convert SerpApi's '2026-09-10 15:10' local time into ISO '2026-09-10T15:10:00'."""
    if not serpapi_time:
        return ""
    try:
        return datetime.strptime(serpapi_time.strip(), "%Y-%m-%d %H:%M").isoformat()
    except ValueError:
        return serpapi_time


def _serpapi_search(params: dict) -> dict:
    """Call the SerpApi Google Flights endpoint. Raises on transport/API error."""
    query = {"engine": "google_flights", "hl": "en", **params, "api_key": _api_key()}
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.get(_SERPAPI_ENDPOINT, params=query)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"SerpApi error: {data['error']}")
    return data


def _parse_flight_item(item: dict, currency: str) -> dict | None:
    """Map one SerpApi flight result into the FlightOption-shaped dict."""
    segments = item.get("flights") or []
    if not segments:
        return None
    first, last = segments[0], segments[-1]
    dep = first.get("departure_airport", {}) or {}
    arr = last.get("arrival_airport", {}) or {}

    airlines: list[str] = []
    for seg in segments:
        name = seg.get("airline")
        if name and name not in airlines:
            airlines.append(name)

    layovers = item.get("layovers") or []
    return {
        "origin": dep.get("id", ""),
        "destination": arr.get("id", ""),
        "departure_time": _to_iso(dep.get("time")),
        "arrival_time": _to_iso(arr.get("time")),
        "duration_minutes": int(item.get("total_duration") or 0),
        "stops": len(layovers) if layovers else max(len(segments) - 1, 0),
        "airline": " / ".join(airlines) if airlines else "Unknown",
        "price": round(float(item.get("price") or 0.0), 2),
        "currency": currency,
        "estimated": False,
    }


def _all_items(data: dict) -> list[dict]:
    return (data.get("best_flights") or []) + (data.get("other_flights") or [])


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
    """Search one-way flight options for a specific date via Google Flights (SerpApi).

    Args:
        origin: Departure airport IATA code (e.g. 'BER').
        destination: Arrival airport IATA code (e.g. 'ATH').
        departure_date: Outbound date in YYYY-MM-DD format.
        passengers: Number of adult passengers.
        max_stops: Maximum stops (0 = direct only). Omit for no limit.
        preferred_time: Departure window as 'HH-HH' (e.g. '6-20').
        currency: ISO 4217 currency code for prices (defaults to EUR).

    Returns:
        dict with keys: options (list), currency (str), estimated (bool),
        available (bool). On any failure, available=false with empty options.
    """
    if not _api_key():
        logger.warning("SERPAPI_API_KEY not set; search_flights deferring to search_web.")
        return _unavailable(currency)

    params = {
        "departure_id": origin.strip().upper(),
        "arrival_id": destination.strip().upper(),
        "outbound_date": departure_date,
        "type": 2,  # one-way
        "currency": currency,
        "adults": max(passengers, 1),
        "stops": _map_stops(max_stops),
        "sort_by": 2,  # by price
    }
    outbound = _outbound_times(preferred_time)
    if outbound:
        params["outbound_times"] = outbound

    try:
        data = _serpapi_search(params)
    except Exception as e:  # noqa: BLE001 - degrade gracefully to search_web
        logger.warning(f"search_flights SerpApi call failed ({e}); deferring to search_web.")
        return _unavailable(currency)

    options = [o for o in (_parse_flight_item(it, currency) for it in _all_items(data)) if o]
    options.sort(key=lambda o: o["price"] if o["price"] > 0 else float("inf"))
    options = options[:_TOP_N]
    if not options:
        logger.info(f"search_flights {origin}->{destination} {departure_date}: no results.")
        return _unavailable(
            currency, "No flights returned for this route/date. Use search_web for prices."
        )
    return {"options": options, "currency": currency, "estimated": False, "available": True}


@mcp.tool()
def find_cheapest_dates(
    origin: str,
    destination: str,
    date_from: str,
    date_to: str,
    duration_days: int | None = None,
    currency: str = "EUR",
) -> dict:
    """Find the cheapest travel-date windows within a range via Google Flights (SerpApi).

    SerpApi has no future "date grid" endpoint, so we probe a bounded set of
    candidate outbound dates across the range (``FLIGHTS_DATE_SAMPLES``) and keep
    the cheapest fare found for each, ranked cheapest-first.

    Args:
        origin: Departure airport IATA code.
        destination: Arrival airport IATA code.
        date_from: Start of search window (YYYY-MM-DD).
        date_to: End of search window (YYYY-MM-DD).
        duration_days: Trip length in days for round-trip pricing (omit for one-way).
        currency: ISO 4217 currency code for prices (defaults to EUR).

    Returns:
        dict with keys: options (list, cheapest first), currency (str),
        estimated (bool), available (bool).
    """
    if not _api_key():
        logger.warning("SERPAPI_API_KEY not set; find_cheapest_dates deferring to search_web.")
        return _unavailable(currency)

    start = _safe_date(date_from) or date.today()
    end = _safe_date(date_to) or (start + timedelta(days=30))
    if end < start:
        end = start + timedelta(days=30)

    span = (end - start).days
    step = max(span // max(_DATE_SAMPLES - 1, 1), 1) if span else 1
    candidates: list[date] = []
    cursor = start
    while cursor <= end and len(candidates) < _DATE_SAMPLES:
        candidates.append(cursor)
        cursor += timedelta(days=step)
    if end not in candidates and len(candidates) < _DATE_SAMPLES:
        candidates.append(end)

    dep_id, arr_id = origin.strip().upper(), destination.strip().upper()
    options: list[dict] = []
    for cand in candidates:
        params = {
            "departure_id": dep_id,
            "arrival_id": arr_id,
            "outbound_date": cand.isoformat(),
            "currency": currency,
            "adults": 1,
            "sort_by": 2,  # by price
        }
        ret: date | None = None
        if duration_days:
            ret = cand + timedelta(days=duration_days)
            params["type"] = 1  # round trip
            params["return_date"] = ret.isoformat()
        else:
            params["type"] = 2  # one-way

        try:
            data = _serpapi_search(params)
        except Exception as e:  # noqa: BLE001 - skip a bad sample, keep the rest
            logger.info(f"find_cheapest_dates sample {cand} failed ({e}); skipping.")
            continue

        prices = [float(it["price"]) for it in _all_items(data) if it.get("price")]
        insights = data.get("price_insights") or {}
        if insights.get("lowest_price"):
            prices.append(float(insights["lowest_price"]))
        if not prices:
            continue
        options.append(
            {
                "departure_date": cand.isoformat(),
                "return_date": ret.isoformat() if ret else None,
                "price": round(min(prices), 2),
                "currency": currency,
                "estimated": False,
            }
        )

    if not options:
        return _unavailable(
            currency, "No date prices returned. Use search_web for cheapest dates."
        )
    options.sort(key=lambda o: o["price"])
    return {"options": options[:10], "currency": currency, "estimated": False, "available": True}


if __name__ == "__main__":
    mcp.run()
