"""Adversarial fixture catalogs for the eval fakes.

Every fixture is designed to make a specific constraint violation DETECTABLE:
if the agent ignores a preference, the resulting tool calls / scenario payload
will show it. Routes not in the catalog get deterministic synthetic options
(seeded by route name) so the harness never breaks because the model picked an
unexpected airport.

Catalog routes:

* BER->LIS  Direct flights exist but cost ~2x the 1-stop options. An agent
            honoring `direct_flights_only` must call with max_stops=0 and end
            up with the expensive direct fares in its cost breakdown.
* BER->ATH  The cheapest options are red-eyes (departing 22:00-02:00);
            daytime flights cost more. Tests "no red-eyes" adherence.
* MUC->JMK  Always returns no options. Tests the no-fabrication contract:
            the agent must fall back to search_web and mark prices estimated.

Prices are per-passenger and scale linearly with the party size (the
`FlightOption.price` field is the TOTAL for all passengers), so "family of 4"
budget constraints are genuinely tight.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FlightFixture:
    """One flight option template for a route (per-passenger base price)."""

    departure_hm: str       # "HH:MM" local departure time
    duration_minutes: int
    stops: int
    airline: str
    base_price: float       # per passenger, in "fixture units" (currency-agnostic)


# Route key: (origin, destination) with IATA codes uppercased.
FLIGHT_CATALOG: dict[tuple[str, str], list[FlightFixture]] = {
    # Direct exists but is ~2x the 1-stop price (both directions).
    ("BER", "LIS"): [
        FlightFixture("10:15", 610, 1, "via Zurich", 89.0),
        FlightFixture("14:40", 655, 1, "via Madrid", 96.0),
        FlightFixture("08:05", 240, 0, "TAP Air Portugal", 189.0),
        FlightFixture("17:30", 240, 0, "TAP Air Portugal", 205.0),
    ],
    ("LIS", "BER"): [
        FlightFixture("09:20", 630, 1, "via Barcelona", 92.0),
        FlightFixture("15:10", 665, 1, "via Paris", 99.0),
        FlightFixture("11:45", 235, 0, "TAP Air Portugal", 195.0),
        FlightFixture("19:05", 235, 0, "easyJet", 211.0),
    ],
    # Cheapest options are red-eyes; daytime costs more (both directions).
    ("BER", "ATH"): [
        FlightFixture("22:35", 185, 0, "Aegean Airlines", 74.0),
        FlightFixture("01:50", 190, 0, "Ryanair", 79.0),
        FlightFixture("09:30", 185, 0, "Aegean Airlines", 142.0),
        FlightFixture("13:15", 190, 0, "Lufthansa", 158.0),
    ],
    ("ATH", "BER"): [
        FlightFixture("23:10", 195, 0, "Aegean Airlines", 71.0),
        FlightFixture("02:25", 195, 0, "Ryanair", 77.0),
        FlightFixture("10:05", 195, 0, "Aegean Airlines", 149.0),
        FlightFixture("14:50", 190, 0, "Lufthansa", 161.0),
    ],
}

# Routes that always return NO options (tests the search_web fallback +
# `estimated: true` contract). Symmetric: both directions are empty.
EMPTY_ROUTES: frozenset[frozenset[str]] = frozenset({frozenset({"MUC", "JMK"})})


@dataclass(frozen=True)
class HotelFixture:
    name: str
    property_type: str
    rate_per_night: float   # for 2 guests, in fixture units
    rating: float
    reviews: int
    hotel_class: int
    amenities: tuple[str, ...]


# Keyed by lowercase destination substring ("lisbon" matches "Lisbon city center").
HOTEL_CATALOG: dict[str, list[HotelFixture]] = {
    "lisbon": [
        HotelFixture("Alfama Budget Rooms", "guest house", 58.0, 3.9, 412, 2, ("Free Wi-Fi",)),
        HotelFixture("Hotel Baixa Central", "hotel", 96.0, 4.3, 1287, 3, ("Free Wi-Fi", "Breakfast")),
        HotelFixture("Chiado Boutique Stay", "hotel", 148.0, 4.6, 861, 4, ("Free Wi-Fi", "Breakfast", "Bar")),
        HotelFixture("Tagus River Grand", "hotel", 245.0, 4.8, 2034, 5, ("Pool", "Spa", "Breakfast")),
    ],
    "athens": [
        HotelFixture("Plaka Backpackers", "guest house", 44.0, 3.7, 655, 2, ("Free Wi-Fi",)),
        HotelFixture("Acropolis View Hotel", "hotel", 88.0, 4.2, 1543, 3, ("Free Wi-Fi", "Rooftop terrace")),
        HotelFixture("Syntagma Suites", "vacation rental", 132.0, 4.5, 322, 0, ("Kitchen", "Free Wi-Fi")),
        HotelFixture("Athenaeum Palace", "hotel", 228.0, 4.7, 1876, 5, ("Pool", "Spa", "Breakfast")),
    ],
}

# Generic fallback hotels for destinations not in the catalog.
GENERIC_HOTELS: list[HotelFixture] = [
    HotelFixture("Central Budget Inn", "guest house", 52.0, 3.8, 340, 2, ("Free Wi-Fi",)),
    HotelFixture("Old Town Hotel", "hotel", 92.0, 4.2, 980, 3, ("Free Wi-Fi", "Breakfast")),
    HotelFixture("Boutique Garden Stay", "hotel", 141.0, 4.5, 610, 4, ("Free Wi-Fi", "Breakfast", "Bar")),
    HotelFixture("Grand Plaza", "hotel", 232.0, 4.7, 1500, 5, ("Pool", "Spa", "Breakfast")),
]


# Keyword-matched canned research responses (first match wins). All responses
# deliberately hedge with "approximately" so LLM judges can check the agent
# presents them as estimates.
RESEARCH_RESPONSES: list[tuple[tuple[str, ...], str]] = [
    (
        ("ferry",),
        "Blue Star Ferries and SeaJets operate the route. Conventional ferry departs "
        "Piraeus around 07:25 arriving approximately 11:55 (4.5 h), roughly 42-58 EUR "
        "per person one way. High-speed departs around 07:00 arriving 10:15 (3.2 h), "
        "roughly 75-90 EUR. Ferries run daily in season; book ahead in July-August.",
    ),
    (
        ("train", "bus", "rail"),
        "Direct intercity trains run this route roughly every 2 hours between about "
        "06:30 and 20:30, taking approximately 3 h 10 m, with one-way fares around "
        "29-55 EUR depending on booking class. Long-distance buses take about 4 h 45 m "
        "and cost approximately 18-27 EUR, with 5-7 departures daily.",
    ),
    (
        ("flight", "fly", "airfare"),
        "Based on current search results, one-way fares on this route typically range "
        "approximately 120-210 EUR in the requested period, with mid-week departures "
        "at the lower end. These are approximate figures from web results, not live "
        "bookable fares.",
    ),
    (
        ("hotel", "accommodation", "stay", "lodging"),
        "Typical nightly rates in the area are approximately 70-110 EUR for well-rated "
        "3-star hotels and 140-220 EUR for 4-5 star properties in the requested period. "
        "These are approximate figures from web results, not live availability.",
    ),
    (
        ("best time", "season", "weather", "visit"),
        "Shoulder season (May-June and September-October) offers warm weather, fewer "
        "crowds, and lower prices; July-August is peak season with the highest prices "
        "and temperatures. Major local events can raise hotel rates in specific weeks.",
    ),
]

RESEARCH_DEFAULT = (
    "Summary from current web results: options exist for this query with typical "
    "prices in a moderate range (approximately 30-120 EUR depending on specifics). "
    "Treat all figures as approximate."
)
