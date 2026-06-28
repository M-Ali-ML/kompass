from pydantic import BaseModel, Field


class FlightOption(BaseModel):
    """A single flight result returned by the flights data provider."""
    origin: str = Field(..., description="Departure airport IATA code (e.g. 'BER').")
    destination: str = Field(..., description="Arrival airport IATA code (e.g. 'ATH').")
    departure_time: str = Field(
        ...,
        description="ISO 8601 local departure timestamp (e.g. '2026-09-10T10:00:00').",
    )
    arrival_time: str = Field(
        ...,
        description="ISO 8601 local arrival timestamp (e.g. '2026-09-10T13:30:00').",
    )
    duration_minutes: int = Field(..., description="Total trip duration in minutes.", ge=0)
    stops: int = Field(..., description="Number of stops/layovers (0 = direct).", ge=0)
    airline: str = Field(
        "",
        description=(
            "Operating airline name, or a routing label ('Direct' / 'via <city>') when the "
            "provider does not expose a carrier (e.g. Kiwi's multi-carrier itineraries)."
        ),
    )
    price: float = Field(..., description="Total price for all passengers.", ge=0.0)
    currency: str = Field("EUR", description="ISO 4217 currency code for the price.")
    booking_link: str | None = Field(
        None, description="Direct deep link to book/view this itinerary (provider URL)."
    )
    estimated: bool = Field(
        False,
        description="True when the price is a synthetic estimate (live data was unavailable).",
    )


class FlightDateOption(BaseModel):
    """A candidate travel-date window ranked by price (cheapest-dates search)."""
    departure_date: str = Field(..., description="Outbound date in YYYY-MM-DD format.")
    return_date: str | None = Field(
        None, description="Return date in YYYY-MM-DD format (None for one-way searches)."
    )
    price: float = Field(..., description="Total price for this date window.", ge=0.0)
    currency: str = Field("EUR", description="ISO 4217 currency code for the price.")
    estimated: bool = Field(
        False,
        description="True when the price is a synthetic estimate (live data was unavailable).",
    )
