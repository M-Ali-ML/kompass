from pydantic import BaseModel, Field
from app.domain.itinerary import Itinerary

class Scenario(BaseModel):
    """Combines a concrete itinerary option with cost, convenience metrics, and reasoning."""
    label: str = Field(
        ..., 
        description="A short descriptive name (e.g., 'Scenario A: Express Flight & Coastal Hotel')."
    )
    itinerary: Itinerary = Field(..., description="The full travel itinerary for this scenario.")
    total_cost: float = Field(
        ..., 
        description="Total estimated cost of the scenario (including transit, lodging, activities).", 
        ge=0.0
    )
    stress_score: int = Field(
        ..., 
        description="A rating from 1 (relaxed) to 5 (highly stressful, tight connections, multiple layovers).",
        ge=1,
        le=5
    )
    reasoning_summary: str = Field(
        ..., 
        description="Explanation of why this scenario was chosen and the pros/cons of this option."
    )
