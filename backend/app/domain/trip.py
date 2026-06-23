from pydantic import BaseModel, Field

class TripRequest(BaseModel):
    """Represents a user's initial trip planning request."""
    destination: str = Field(
        ..., 
        description="The target destination for the trip (e.g. 'Greece', 'Kyoto, Japan')."
    )
    duration_days: int = Field(
        ..., 
        description="The length of the trip in days."
    )
    month: str = Field(
        ..., 
        description="The month or broad date window (e.g. 'September', 'late July') for travel."
    )
    budget_range: str = Field(
        ..., 
        description="Broad budget category (e.g., 'budget', 'mid-range', 'luxury')."
    )
    traveler_count: int = Field(
        ..., 
        description="Number of people traveling.",
        ge=1
    )
