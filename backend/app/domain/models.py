from pydantic import BaseModel, Field
from typing import List, Optional

class FlightDetail(BaseModel):
    airline: str
    flight_number: str
    departure_time: str
    arrival_time: str
    origin: str
    destination: str
    duration_minutes: int
    price_usd: float

class StayDetail(BaseModel):
    name: str
    location: str
    check_in: str
    check_out: str
    rating: float
    price_per_night_usd: float
    total_price_usd: float

class ActivityDetail(BaseModel):
    name: str
    description: str
    start_time: str
    end_time: str
    category: str

class ItineraryDay(BaseModel):
    day_number: int
    title: str
    date: str
    activities: List[ActivityDetail]

class ItineraryScenario(BaseModel):
    scenario_id: str
    title: str
    summary: str
    transportation_subtotal_usd: float
    accommodation_subtotal_usd: float
    grand_total_usd: float
    stress_score: int = Field(ge=1, le=5, description="1 is very relaxed, 5 is high stress (e.g., tight connections, multiple layovers).")
    flights: List[FlightDetail]
    stays: List[StayDetail]
    itinerary: List[ItineraryDay]

class ScenarioMatrix(BaseModel):
    scenarios: List[ItineraryScenario]
    active_constraints: List[str]

class UserPreferenceProfile(BaseModel):
    user_id: str
    preferred_vibe: List[str] = Field(default_factory=list)
    budget_max_usd: Optional[float] = None
    max_flight_stops: int = 1
    preferred_hotel_rating: int = 4
