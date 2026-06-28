"""Flight data adapter backed by the official Kiwi.com MCP server.

Connects directly to the remote Kiwi MCP (``https://mcp.kiwi.com/mcp`` by default,
overridable via ``KIWI_MCP_URL``) over streamable HTTP — no API key required. Kiwi
is already an MCP server, so there is no local wrapper subprocess: this adapter is
the only translation layer between the agent's ``FlightServicePort`` and Kiwi.

Kiwi exposes a single ``search-flight`` tool. We map it to the two port methods:

* ``search_flights``      — one ``search-flight`` call for a specific date, then
  client-side filtering for ``max_stops`` / ``preferred_time`` (Kiwi has no such
  server-side filters) and cheapest-first ranking.
* ``find_cheapest_dates`` — several ``search-flight`` calls fired concurrently,
  each using Kiwi's ±3-day flex window so a handful of calls covers a whole month,
  then the cheapest fare per departure date is kept and ranked.

Reliability contract: any transport/API error degrades to an **empty** result
(no fabricated data) so the agent falls back to its grounded ``search_web`` tool.
Each call uses a short-lived connection, which keeps concurrent date sampling
simple and avoids stale long-lived remote sessions.
"""

import asyncio
import json
import logging
import os
from datetime import date, datetime, timedelta

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.config import settings
from app.domain.flights import FlightDateOption, FlightOption
from app.ports.flight_service import FlightServicePort

logger = logging.getLogger("kompass.kiwi_flight_service")

_KIWI_TOOL = "search-flight"
# Cheapest-first cap for a single-date search.
_TOP_N = max(1, int(os.getenv("KIWI_FLIGHTS_TOP_N", "5")))
# How many flex-window searches to fire across a cheapest-dates range. Each Kiwi
# call covers a ~7-day window (±3 flex), so ~5 calls span a month. Also bounds
# the concurrency of the gather below.
_DATE_SAMPLES = max(1, int(os.getenv("KIWI_DATE_SAMPLES", "5")))
# Kiwi flex range maximum (the tool accepts 0..3 days either side).
_FLEX = 3


# --- Date helpers -------------------------------------------------------------

def _iso_to_kiwi(iso: str) -> str:
    """Convert an ISO 'YYYY-MM-DD' date into Kiwi's 'dd/mm/yyyy' format."""
    return datetime.strptime(iso.strip(), "%Y-%m-%d").date().strftime("%d/%m/%Y")


def _date_to_kiwi(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def _safe_date(value: str) -> date | None:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _kiwi_local_to_iso(local: str | None) -> str:
    """Normalize Kiwi's local timestamp ('2026-09-10T06:00:00.000') to ISO seconds."""
    if not local:
        return ""
    s = local.replace("Z", "")
    if "." in s:
        s = s.split(".", 1)[0]
    return s


# --- Result mapping -----------------------------------------------------------

def _routing_label(layovers: list[dict]) -> str:
    """A truthful carrier-less label: 'Direct' or 'via <city>, <city>'.

    Kiwi's MCP output omits airline names (its itineraries are often multi-carrier
    self-transfers), so we surface the connection routing instead of a carrier.
    """
    cities: list[str] = []
    for lay in layovers or []:
        name = lay.get("city") or lay.get("cityCode") or lay.get("at")
        if name and name not in cities:
            cities.append(name)
    if not cities:
        return "Direct"
    return "via " + ", ".join(cities)


def _parse_option(item: dict, currency: str) -> FlightOption | None:
    """Map one Kiwi ``search-flight`` result into a ``FlightOption``."""
    price = item.get("price")
    if price is None:
        return None
    layovers = item.get("layovers") or []
    dep = item.get("departure") or {}
    arr = item.get("arrival") or {}
    return FlightOption(
        origin=item.get("flyFrom", ""),
        destination=item.get("flyTo", ""),
        departure_time=_kiwi_local_to_iso(dep.get("local")),
        arrival_time=_kiwi_local_to_iso(arr.get("local")),
        duration_minutes=round(float(item.get("totalDurationInSeconds") or 0) / 60),
        stops=len(layovers),
        airline=_routing_label(layovers),
        price=round(float(price), 2),
        currency=item.get("currency") or currency,
        booking_link=item.get("deepLink"),
        estimated=False,
    )


def _within_window(departure_time: str, start_h: int, end_h: int) -> bool:
    """True when an ISO departure timestamp's hour falls in [start_h, end_h].

    Unparseable timestamps are kept (we don't drop options we can't evaluate).
    """
    try:
        return start_h <= datetime.fromisoformat(departure_time).hour <= end_h
    except (ValueError, TypeError):
        return True


def _time_window(preferred_time: str | None) -> tuple[int, int] | None:
    """Parse a 'HH-HH' window into an (start_hour, end_hour) tuple."""
    if not preferred_time or "-" not in preferred_time:
        return None
    try:
        start_s, end_s = preferred_time.split("-", 1)
        start, end = int(start_s.strip()), int(end_s.strip())
    except ValueError:
        return None
    if 0 <= start <= end <= 24:
        return start, end
    return None


class KiwiMCPFlightServiceAdapter(FlightServicePort):
    """Talks to the remote Kiwi.com MCP over streamable HTTP.

    Searches use short-lived connections (one per call), which makes the
    concurrent cheapest-dates sampling trivial and avoids stale remote sessions.
    ``start``/``stop`` only do a best-effort reachability check at app startup.
    """

    def __init__(self, url: str | None = None):
        self.url = url or settings.kiwi_mcp_url
        logger.info(f"Initialized KiwiMCPFlightServiceAdapter (url={self.url})")

    async def start(self) -> None:
        """Best-effort reachability probe so boot logs surface a dead endpoint."""
        try:
            async with streamablehttp_client(self.url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
            logger.info("Kiwi MCP reachable at %s", self.url)
        except Exception as e:  # noqa: BLE001 - tools degrade per-call, so never fatal
            logger.warning(
                "Kiwi MCP not reachable at startup (%s); flight tools will retry per call.", e
            )

    async def stop(self) -> None:
        # Nothing to tear down: each search opens and closes its own connection.
        return None

    async def _search(self, arguments: dict) -> list[dict]:
        """One ``search-flight`` call over a short-lived session. ``[]`` on any error.

        Retries once on a transport failure to ride out a transient TLS/connect
        blip, then degrades to an empty result so the agent falls back to search_web.
        """
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                async with streamablehttp_client(self.url) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(_KIWI_TOOL, arguments=arguments)
            except Exception as e:  # noqa: BLE001 - degrade gracefully to search_web
                last_error = e
                if attempt == 0:
                    await asyncio.sleep(0.5)
                    continue
                logger.warning("Kiwi search-flight call failed (%s); degrading.", last_error)
                return []

            if getattr(result, "isError", False):
                logger.warning("Kiwi search-flight returned an error: %s", result.content)
                return []
            return _extract_items(result)
        return []

    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        *,
        passengers: int = 1,
        max_stops: int | None = None,
        preferred_time: str | None = None,
        currency: str = "EUR",
    ) -> list[FlightOption]:
        try:
            depart_kiwi = _iso_to_kiwi(departure_date)
        except (ValueError, AttributeError):
            logger.warning("search_flights got an invalid departure_date %r; degrading.", departure_date)
            return []

        arguments = {
            "flyFrom": origin.strip().upper(),
            "flyTo": destination.strip().upper(),
            "departureDate": depart_kiwi,
            "passengers": {"adults": max(passengers, 1)},
            "curr": currency,
            "sort": "price",
        }
        items = await self._search(arguments)

        options = [o for o in (_parse_option(it, currency) for it in items) if o]
        if max_stops is not None:
            options = [o for o in options if o.stops <= max_stops]
        window = _time_window(preferred_time)
        if window is not None:
            start_h, end_h = window
            options = [o for o in options if _within_window(o.departure_time, start_h, end_h)]

        options.sort(key=lambda o: o.price if o.price > 0 else float("inf"))
        return options[:_TOP_N]

    async def find_cheapest_dates(
        self,
        origin: str,
        destination: str,
        *,
        date_from: str,
        date_to: str,
        duration_days: int | None = None,
        currency: str = "EUR",
    ) -> list[FlightDateOption]:
        start = _safe_date(date_from) or date.today()
        end = _safe_date(date_to) or (start + timedelta(days=30))
        if end < start:
            end = start + timedelta(days=30)

        # Sample departure dates ~7 days apart; each Kiwi call's ±3 flex window
        # makes the samples tile the range contiguously.
        samples: list[date] = []
        cursor = start
        while cursor <= end and len(samples) < _DATE_SAMPLES:
            samples.append(cursor)
            cursor += timedelta(days=7)

        fly_from, fly_to = origin.strip().upper(), destination.strip().upper()
        sem = asyncio.Semaphore(_DATE_SAMPLES)

        async def probe(dep: date) -> list[dict]:
            arguments = {
                "flyFrom": fly_from,
                "flyTo": fly_to,
                "departureDate": _date_to_kiwi(dep),
                "departureDateFlexRange": _FLEX,
                "passengers": {"adults": 1},
                "curr": currency,
                "sort": "price",
            }
            if duration_days:
                arguments["returnDate"] = _date_to_kiwi(dep + timedelta(days=duration_days))
                arguments["returnDateFlexRange"] = _FLEX
            async with sem:
                return await self._search(arguments)

        batches = await asyncio.gather(*(probe(d) for d in samples))

        # Keep the cheapest fare per actual returned departure date, within range.
        best: dict[str, dict] = {}
        for items in batches:
            for it in items:
                price = it.get("price")
                dep_iso = _kiwi_local_to_iso((it.get("departure") or {}).get("local"))[:10]
                if price is None or not dep_iso:
                    continue
                dep_d = _safe_date(dep_iso)
                if dep_d is None or dep_d < start or dep_d > end:
                    continue
                ret_iso: str | None = None
                ret_block = it.get("return") or {}
                if ret_block:
                    ret_iso = _kiwi_local_to_iso((ret_block.get("departure") or {}).get("local"))[:10] or None
                elif duration_days:
                    ret_iso = (dep_d + timedelta(days=duration_days)).isoformat()
                price_f = round(float(price), 2)
                current = best.get(dep_iso)
                if current is None or price_f < current["price"]:
                    best[dep_iso] = {
                        "departure_date": dep_iso,
                        "return_date": ret_iso,
                        "price": price_f,
                        "currency": currency,
                        "estimated": False,
                    }

        ranked = sorted(best.values(), key=lambda o: o["price"])[:10]
        return [FlightDateOption(**o) for o in ranked]


def _extract_items(result) -> list[dict]:
    """Pull the list of flight dicts out of an MCP tool result.

    Kiwi returns a JSON array as the text content block; some servers also mirror
    it in ``structuredContent``. Returns ``[]`` for anything unparseable (e.g. a
    plain error string), which the callers treat as "no data".
    """
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, list):
        return structured
    if isinstance(structured, dict):
        for value in structured.values():
            if isinstance(value, list):
                return value

    content = getattr(result, "content", None)
    if content:
        text = getattr(content[0], "text", "")
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            inner = data.get("data")
            return inner if isinstance(inner, list) else []
    return []


# Singleton instance started/stopped by the FastAPI lifespan.
flight_service = KiwiMCPFlightServiceAdapter()
