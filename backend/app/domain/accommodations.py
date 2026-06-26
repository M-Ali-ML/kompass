from pydantic import BaseModel, Field


class AccommodationOption(BaseModel):
    """A single lodging result returned by the accommodations data provider."""
    name: str = Field(..., description="Name of the hotel, vacation rental, or property.")
    property_type: str = Field(
        "hotel",
        description="Kind of lodging (e.g. 'hotel', 'vacation rental', 'guest house').",
    )
    rate_per_night: float = Field(
        ...,
        description="Lowest nightly rate for the stay, in the traveler's currency.",
        ge=0.0,
    )
    total_rate: float = Field(
        ...,
        description="Lowest total cost for the whole stay (all nights), in the traveler's currency.",
        ge=0.0,
    )
    currency: str = Field("EUR", description="ISO 4217 currency code for the prices.")
    rating: float | None = Field(
        None, description="Overall guest rating out of 5 (e.g. 4.4)."
    )
    reviews: int | None = Field(None, description="Number of guest reviews.", ge=0)
    hotel_class: int | None = Field(
        None, description="Star rating of the property (1-5), when known.", ge=0, le=5
    )
    amenities: list[str] = Field(
        default_factory=list,
        description="Notable amenities (e.g. 'Pool', 'Free Wi-Fi', 'Breakfast').",
    )
    link: str | None = Field(
        None, description="A link to the property's details / booking page."
    )
    latitude: float | None = Field(None, description="Property latitude, when known.")
    longitude: float | None = Field(None, description="Property longitude, when known.")
    estimated: bool = Field(
        False,
        description="True when the price is an estimate (live data was unavailable).",
    )
