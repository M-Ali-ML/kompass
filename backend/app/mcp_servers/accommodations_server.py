"""Standalone Accommodations MCP server — SerpApi Google Hotels provider.

Exposes one tool over MCP stdio that the Kompass agent calls through the
``MCPAccommodationServiceAdapter``:

* ``search_accommodations`` — live hotel / vacation-rental options for a stay

Live data comes from **SerpApi's Google Hotels API**
(https://serpapi.com/google-hotels-api), which returns structured Google Hotels
results (nightly + total rates, ratings, amenities). This mirrors the Flights
MCP server (SerpApi Google Flights) and reuses the same ``SERPAPI_API_KEY``.

Reliability contract: if ``SERPAPI_API_KEY`` is missing, or SerpApi errors /
returns nothing, the tool returns ``available: false`` with **no fabricated
data** so the agent falls back to the grounded ``search_web`` tool. We never
invent prices.

The API key is read from the environment (``SERPAPI_API_KEY``); the parent app
exports it via ``app.config`` and the MCP subprocess inherits the environment.
"""

import logging
import os
from datetime import date, datetime

import httpx
from mcp.server.fastmcp import FastMCP

# Dev helpers (mock mode + call logging). Imported as a package module in tests /
# the parent app, or as a top-level module when this file is launched directly
# as a subprocess (only its own directory is then on sys.path).
try:
    from app.mcp_servers._dev import log_call, mock_mode
except ImportError:  # pragma: no cover - standalone subprocess import path
    from _dev import log_call, mock_mode

logger = logging.getLogger("kompass.accommodations_mcp")

mcp = FastMCP("AccommodationsServer")

_SERPAPI_ENDPOINT = "https://serpapi.com/search"
_TIMEOUT = float(os.getenv("SERPAPI_TIMEOUT", "25"))
_TOP_N = max(1, int(os.getenv("ACCOMMODATIONS_TOP_N", "6")))
# How many amenities to keep per property so the agent payload stays compact.
_MAX_AMENITIES = max(1, int(os.getenv("ACCOMMODATIONS_MAX_AMENITIES", "6")))

_UNAVAILABLE_NOTE = (
    "Structured accommodation data is currently unavailable. "
    "Use the search_web tool for live hotel options and nightly rates."
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

def _safe_date(value: str) -> date | None:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _nights(check_in: str, check_out: str) -> int:
    """Number of nights between two ISO dates (minimum 1)."""
    ci, co = _safe_date(check_in), _safe_date(check_out)
    if ci and co and co > ci:
        return (co - ci).days
    return 1


def _map_rating(min_rating: float | None) -> int | None:
    """Map a minimum star/guest rating to the SerpApi ``rating`` enum.

    SerpApi: 7 = 3.5+, 8 = 4.0+, 9 = 4.5+ (no finer buckets exist).
    """
    if min_rating is None:
        return None
    if min_rating >= 4.5:
        return 9
    if min_rating >= 4.0:
        return 8
    if min_rating >= 3.5:
        return 7
    return None


def _serpapi_search(params: dict) -> dict:
    """Call the SerpApi Google Hotels endpoint. Raises on transport/API error."""
    query = {"engine": "google_hotels", "hl": "en", **params, "api_key": _api_key()}
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.get(_SERPAPI_ENDPOINT, params=query)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"SerpApi error: {data['error']}")
    return data


def _extracted(rate: dict | None) -> float | None:
    """Pull the numeric ``extracted_lowest`` out of a SerpApi rate object."""
    if not isinstance(rate, dict):
        return None
    value = rate.get("extracted_lowest")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _hotel_class(item: dict) -> int | None:
    """Best-effort star rating from SerpApi's class fields."""
    extracted = item.get("extracted_hotel_class")
    if isinstance(extracted, (int, float)):
        return int(extracted)
    return None


def _parse_property(item: dict, currency: str, nights: int) -> dict | None:
    """Map one SerpApi hotel property into the AccommodationOption-shaped dict."""
    name = item.get("name")
    if not name:
        return None

    nightly = _extracted(item.get("rate_per_night"))
    total = _extracted(item.get("total_rate"))
    # Derive whichever rate SerpApi omitted so both are always populated.
    if nightly is None and total is not None:
        nightly = round(total / nights, 2)
    if total is None and nightly is not None:
        total = round(nightly * nights, 2)
    if nightly is None and total is None:
        return None  # no price → not useful; agent falls back to search_web

    coords = item.get("gps_coordinates") or {}
    amenities = [a for a in (item.get("amenities") or []) if isinstance(a, str)]

    return {
        "name": name,
        "property_type": item.get("type") or "hotel",
        "rate_per_night": round(float(nightly), 2),
        "total_rate": round(float(total), 2),
        "currency": currency,
        "rating": item.get("overall_rating"),
        "reviews": item.get("reviews"),
        "hotel_class": _hotel_class(item),
        "amenities": amenities[:_MAX_AMENITIES],
        "link": item.get("link") or item.get("serpapi_property_details_link"),
        "latitude": coords.get("latitude"),
        "longitude": coords.get("longitude"),
        "estimated": False,
    }


# --- Mock data (MCP_MODE=mock) ------------------------------------------------

def _mock_accommodations(destination: str, nights: int, currency: str) -> list[dict]:
    """Deterministic fake lodging options (no network). Flagged estimated=true."""
    place = destination.strip() or "the destination"
    catalog = [
        ("Harbor View Inn", "hotel", 3, 4.2, 210, ["Free Wi-Fi", "Breakfast", "Air conditioning"]),
        ("Azure Boutique Hotel", "hotel", 4, 4.6, 540, ["Pool", "Free Wi-Fi", "Spa", "Bar"]),
        ("Old Town Studios", "vacation rental", 0, 4.4, 88, ["Kitchen", "Free Wi-Fi", "Balcony"]),
        ("Grand Caldera Resort", "hotel", 5, 4.8, 932, ["Pool", "Spa", "Breakfast", "Beach access"]),
    ]
    options = []
    for i, (name, ptype, stars, rating, reviews, amenities) in enumerate(catalog):
        nightly = round(85.0 + i * 60, 2)
        options.append(
            {
                "name": f"{name} {place}",
                "property_type": ptype,
                "rate_per_night": nightly,
                "total_rate": round(nightly * nights, 2),
                "currency": currency,
                "rating": rating,
                "reviews": reviews,
                "hotel_class": stars or None,
                "amenities": amenities,
                "link": None,
                "latitude": None,
                "longitude": None,
                "estimated": True,
            }
        )
    options.sort(key=lambda o: o["rate_per_night"])
    return options


# --- MCP tools ----------------------------------------------------------------

@mcp.tool()
def search_accommodations(
    destination: str,
    check_in_date: str,
    check_out_date: str,
    guests: int = 2,
    max_price: int | None = None,
    min_rating: float | None = None,
    currency: str = "EUR",
) -> dict:
    """Search live lodging options for a stay via Google Hotels (SerpApi).

    Args:
        destination: City / area / property query (e.g. 'Santorini', 'Athens city center').
        check_in_date: Check-in date in YYYY-MM-DD format.
        check_out_date: Check-out date in YYYY-MM-DD format.
        guests: Number of adult guests.
        max_price: Optional maximum nightly rate (in ``currency``) to cap results.
        min_rating: Optional minimum guest rating (e.g. 4.0) to filter results.
        currency: ISO 4217 currency code for prices (defaults to EUR).

    Returns:
        dict with keys: options (list, cheapest first), currency (str),
        estimated (bool), available (bool). On any failure, available=false
        with empty options so the agent falls back to search_web.
    """
    request = {
        "destination": destination,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "guests": guests,
        "max_price": max_price,
        "min_rating": min_rating,
        "currency": currency,
    }

    ci, co = _safe_date(check_in_date), _safe_date(check_out_date)
    if not ci or not co or co <= ci:
        result = _unavailable(
            currency,
            "Invalid check-in/check-out dates. Provide YYYY-MM-DD with check-out after check-in.",
        )
        log_call(logger, "accommodations", "search_accommodations", request, result)
        return result

    if mock_mode():
        nights = _nights(ci.isoformat(), co.isoformat())
        options = _mock_accommodations(destination, nights, currency)
        if max_price is not None and max_price > 0:
            options = [o for o in options if o["rate_per_night"] <= max_price] or options[:1]
        if min_rating is not None:
            options = [o for o in options if (o["rating"] or 0) >= min_rating] or options
        result = {"options": options, "currency": currency, "estimated": True, "available": True}
        log_call(logger, "accommodations", "search_accommodations", request, result)
        return result

    if not _api_key():
        logger.warning("SERPAPI_API_KEY not set; search_accommodations deferring to search_web.")
        result = _unavailable(currency)
        log_call(logger, "accommodations", "search_accommodations", request, result)
        return result

    params = {
        "q": destination.strip(),
        "check_in_date": ci.isoformat(),
        "check_out_date": co.isoformat(),
        "adults": max(guests, 1),
        "currency": currency,
        "sort_by": 3,  # lowest price first
    }
    if max_price is not None and max_price > 0:
        params["max_price"] = int(max_price)
    rating = _map_rating(min_rating)
    if rating is not None:
        params["rating"] = rating

    try:
        data = _serpapi_search(params)
    except Exception as e:  # noqa: BLE001 - degrade gracefully to search_web
        logger.warning(
            f"search_accommodations SerpApi call failed ({e}); deferring to search_web."
        )
        result = _unavailable(currency)
        log_call(logger, "accommodations", "search_accommodations", request, result)
        return result

    nights = _nights(ci.isoformat(), co.isoformat())
    properties = data.get("properties") or []
    options = [o for o in (_parse_property(p, currency, nights) for p in properties) if o]
    options.sort(key=lambda o: o["rate_per_night"] if o["rate_per_night"] > 0 else float("inf"))
    options = options[:_TOP_N]
    if not options:
        logger.info(f"search_accommodations {destination!r} {ci}..{co}: no results.")
        result = _unavailable(
            currency,
            "No accommodations returned for this destination/dates. Use search_web for options.",
        )
    else:
        result = {"options": options, "currency": currency, "estimated": False, "available": True}
    log_call(logger, "accommodations", "search_accommodations", request, result)
    return result


if __name__ == "__main__":
    mcp.run()
