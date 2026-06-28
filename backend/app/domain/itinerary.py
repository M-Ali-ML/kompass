from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class TransportMode(str, Enum):
    FLIGHT = "flight"
    TRAIN = "train"
    BUS = "bus"
    FERRY = "ferry"
    CAR = "car"
    OTHER = "other"

class Leg(BaseModel):
    """Represents a single segment of transit between two locations."""
    mode: TransportMode = Field(..., description="The mode of transport used.")
    origin: str = Field(..., description="The departure location code or name.")
    destination: str = Field(..., description="The arrival location code or name.")
    departure_time: datetime = Field(
        ..., 
        description="ISO 8601 timezone-aware departure timestamp (e.g. YYYY-MM-DDTHH:MM:SSZ)."
    )
    arrival_time: datetime = Field(
        ..., 
        description="ISO 8601 timezone-aware arrival timestamp (e.g. YYYY-MM-DDTHH:MM:SSZ)."
    )
    carrier: str = Field(..., description="The carrier name or flight/train number (e.g., 'Lufthansa LH123').")
    cost: float = Field(..., description="The cost of this transit segment in the base currency.", ge=0.0)

class Accommodation(BaseModel):
    """Represents a lodging booking for a duration of the trip."""
    name: str = Field(..., description="Name of the hotel, hostel, or rental property.")
    location: str = Field(..., description="City or address of the accommodation.")
    check_in: datetime = Field(
        ..., 
        description="ISO 8601 timezone-aware check-in timestamp (e.g. YYYY-MM-DDTHH:MM:SSZ)."
    )
    check_out: datetime = Field(
        ..., 
        description="ISO 8601 timezone-aware check-out timestamp (e.g. YYYY-MM-DDTHH:MM:SSZ)."
    )
    cost: float = Field(..., description="Total cost of the stay for this accommodation.", ge=0.0)
    booking_link: str | None = Field(
        None,
        description=(
            "URL to the property's details / booking page, copied from the chosen "
            "search_accommodations option's `link` when available."
        ),
    )

class PlanItem(BaseModel):
    """A single scheduled activity within a day."""
    period: str = Field(
        ...,
        description="Time-of-day or clock time, e.g. 'Morning', 'Afternoon', 'Evening', or '09:00'.",
    )
    activity: str = Field(
        ...,
        description="Short title of the activity (e.g. 'Explore the Old Town', 'Sunset boat tour').",
    )
    details: str | None = Field(
        None,
        description="One practical sentence of context (what/why/how, tips, rough cost or duration).",
    )
    location: str | None = Field(
        None,
        description="Specific place, neighborhood, or venue for this activity, if relevant.",
    )


class DaySummary(BaseModel):
    """A comprehensive day-by-day plan entry for the traveler."""
    day_number: int = Field(..., description="The day index of the trip (starting from 1).", ge=1)
    title: str | None = Field(
        None,
        description=(
            "A short, evocative headline for the day (e.g. 'Arrival & Sunset Stroll'). "
            "Optional — backfilled from the day's description if omitted."
        ),
    )
    description: str = Field(..., description="Brief narrative of the day's vibe and overall plan.")
    schedule: list[PlanItem] = Field(
        default_factory=list,
        description=(
            "Time-ordered activities for the day (morning → afternoon → evening). "
            "Provide 3-5 concrete items with specific places, not generic filler."
        ),
    )

class Itinerary(BaseModel):
    """Aggregates all transit legs, lodgings, and daily plans for a single option."""
    legs: list[Leg] = Field(default_factory=list, description="Ordered transit segments for the trip.")
    accommodations: list[Accommodation] = Field(default_factory=list, description="Lodgings booked/selected.")
    days: list[DaySummary] = Field(default_factory=list, description="Day-by-day plan summaries.")
