"""Deterministic in-memory implementations of the data-service ports.

These stand in for the live Kiwi MCP / SerpApi / Gemini-grounding adapters
during evals. They are pure functions of their inputs (no network, no time
dependence beyond the dates the agent passes in), and they record every call
in `.calls` so evaluators can assert on tool arguments (e.g. `max_stops=0`
when the traveler wants direct flights only).
"""

import hashlib
import math
from datetime import date, datetime, timedelta
from typing import Any

from app.domain.accommodations import AccommodationOption
from app.domain.flights import FlightDateOption, FlightOption
from app.ports.accommodation_service import AccommodationServicePort
from app.ports.flight_service import FlightServicePort
from app.ports.research_service import ResearchServicePort

from evals.fixtures import (
    EMPTY_ROUTES,
    FLIGHT_CATALOG,
    GENERIC_HOTELS,
    HOTEL_CATALOG,
    RESEARCH_DEFAULT,
    RESEARCH_RESPONSES,
    FlightFixture,
)


def _stable_int(seed: str, lo: int, hi: int) -> int:
    """Deterministic pseudo-random int in [lo, hi] derived from a string seed."""
    digest = hashlib.sha256(seed.encode()).digest()
    return lo + int.from_bytes(digest[:4], "big") % (hi - lo + 1)


def _synthetic_route(origin: str, destination: str) -> list[FlightFixture]:
    """Deterministic options for routes outside the curated catalog.

    Seeded by the route so any airport pair the model picks yields stable,
    plausible daytime options (a cheaper 1-stop and a pricier direct).
    """
    seed = f"{origin}->{destination}"
    base = _stable_int(seed, 60, 140)
    duration = _stable_int(seed + "dur", 120, 420)
    return [
        FlightFixture("11:20", duration + 150, 1, f"via hub ({seed})", float(base)),
        FlightFixture("15:45", duration + 180, 1, "via hub", float(base + 12)),
        FlightFixture("09:10", duration, 0, "Direct carrier", float(base) * 1.7),
    ]


def _safe_date(value: str, default: date = date(2026, 9, 15)) -> date:
    """Lenient ISO-date parse. Model-generated args are a boundary: the live
    adapters tolerate malformed dates, so the fakes must too (TestModel in
    particular sends junk strings)."""
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return default


def _parse_window(preferred_time: str | None) -> tuple[int, int] | None:
    """Parse an 'HH-HH' departure window; None when absent/malformed."""
    if not preferred_time:
        return None
    try:
        lo, hi = preferred_time.split("-")
        return int(lo), int(hi)
    except ValueError:
        return None


class FakeFlightService(FlightServicePort):
    """FlightServicePort backed by the adversarial fixture catalog."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

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
        self.calls.append({
            "method": "search_flights",
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "passengers": passengers,
            "max_stops": max_stops,
            "preferred_time": preferred_time,
            "currency": currency,
        })
        o, d = origin.upper(), destination.upper()
        if frozenset({o, d}) in EMPTY_ROUTES:
            return []

        fixtures = FLIGHT_CATALOG.get((o, d)) or _synthetic_route(o, d)
        window = _parse_window(preferred_time)
        options: list[FlightOption] = []
        for fx in fixtures:
            if max_stops is not None and fx.stops > max_stops:
                continue
            hour = int(fx.departure_hm.split(":")[0])
            if window is not None and not (window[0] <= hour <= window[1]):
                continue
            dep = datetime.fromisoformat(
                f"{_safe_date(departure_date).isoformat()}T{fx.departure_hm}:00"
            )
            arr = dep + timedelta(minutes=fx.duration_minutes)
            options.append(
                FlightOption(
                    origin=o,
                    destination=d,
                    departure_time=dep.isoformat(),
                    arrival_time=arr.isoformat(),
                    duration_minutes=fx.duration_minutes,
                    stops=fx.stops,
                    airline=fx.airline,
                    price=round(fx.base_price * passengers, 2),
                    currency=currency,
                    booking_link=f"https://example.test/book/{o}-{d}",
                    estimated=False,
                )
            )
        return sorted(options, key=lambda f: f.price)

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
        self.calls.append({
            "method": "find_cheapest_dates",
            "origin": origin,
            "destination": destination,
            "date_from": date_from,
            "date_to": date_to,
            "duration_days": duration_days,
            "currency": currency,
        })
        o, d = origin.upper(), destination.upper()
        if frozenset({o, d}) in EMPTY_ROUTES:
            return []

        fixtures = FLIGHT_CATALOG.get((o, d)) or _synthetic_route(o, d)
        cheapest_leg = min(fx.base_price for fx in fixtures)
        round_trip = cheapest_leg * (2.0 if duration_days else 1.0)

        start = _safe_date(date_from)
        end = _safe_date(date_to, default=start + timedelta(days=30))
        span = max((end - start).days, 1)
        # Three deterministic windows: mid-window is cheapest, edges pricier.
        offsets_and_multipliers = [
            (span // 2, 1.0),
            (span // 4, 1.18),
            (max(span - 2, 0), 1.32),
        ]
        options: list[FlightDateOption] = []
        for offset, mult in offsets_and_multipliers:
            dep_date = start + timedelta(days=offset)
            if dep_date > end:
                dep_date = end
            ret_date = (
                (dep_date + timedelta(days=duration_days)).isoformat()
                if duration_days
                else None
            )
            options.append(
                FlightDateOption(
                    departure_date=dep_date.isoformat(),
                    return_date=ret_date,
                    price=round(round_trip * mult, 2),
                    currency=currency,
                    estimated=False,
                )
            )
        return sorted(options, key=lambda x: x.price)


class FakeAccommodationService(AccommodationServicePort):
    """AccommodationServicePort backed by the per-destination hotel catalog."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def search_accommodations(
        self,
        destination: str,
        *,
        check_in_date: str,
        check_out_date: str,
        guests: int = 2,
        max_price: int | None = None,
        min_rating: float | None = None,
        currency: str = "EUR",
    ) -> list[AccommodationOption]:
        self.calls.append({
            "method": "search_accommodations",
            "destination": destination,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "guests": guests,
            "max_price": max_price,
            "min_rating": min_rating,
            "currency": currency,
        })
        check_in = _safe_date(check_in_date)
        check_out = _safe_date(check_out_date, default=check_in + timedelta(days=3))
        nights = max((check_out - check_in).days, 1)
        dest_lower = destination.lower()
        fixtures = next(
            (hotels for key, hotels in HOTEL_CATALOG.items() if key in dest_lower),
            GENERIC_HOTELS,
        )
        # Fixture rates cover a double room; larger parties need more rooms.
        rooms = max(math.ceil(guests / 2), 1)

        options: list[AccommodationOption] = []
        for hx in fixtures:
            nightly = round(hx.rate_per_night * rooms, 2)
            if max_price is not None and nightly > max_price:
                continue
            if min_rating is not None and hx.rating < min_rating:
                continue
            options.append(
                AccommodationOption(
                    name=hx.name,
                    property_type=hx.property_type,
                    rate_per_night=nightly,
                    total_rate=round(nightly * nights, 2),
                    currency=currency,
                    rating=hx.rating,
                    reviews=hx.reviews,
                    hotel_class=hx.hotel_class or None,
                    amenities=list(hx.amenities),
                    link=f"https://example.test/hotel/{hx.name.replace(' ', '-').lower()}",
                    estimated=False,
                )
            )
        return sorted(options, key=lambda a: a.total_rate)


class FakeResearchService(ResearchServicePort):
    """ResearchServicePort returning canned grounded text by keyword match."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def research(self, query: str) -> str:
        self.calls.append(query)
        q = query.lower()
        for keywords, response in RESEARCH_RESPONSES:
            if any(kw in q for kw in keywords):
                return response
        return RESEARCH_DEFAULT
