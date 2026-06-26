from datetime import date

from pydantic import BaseModel, Field

from app.domain.itinerary import Itinerary


class CostBreakdown(BaseModel):
    """Itemized cost subtotals for a scenario, in the traveler's preferred currency."""
    transportation: float = Field(
        ...,
        description="Total transport cost across all legs (flights, trains, ferries, buses).",
        ge=0.0,
    )
    accommodation: float = Field(
        ...,
        description="Total lodging cost for the whole stay.",
        ge=0.0,
    )
    grand_total: float = Field(
        ...,
        description="Grand total for the scenario (transportation + accommodation).",
        ge=0.0,
    )


class StressFactors(BaseModel):
    """The concrete sub-factors that justify a scenario's stress score."""
    layover_count: int = Field(
        ...,
        description="Total number of layovers/connections across the journey.",
        ge=0,
    )
    overnight_travel: bool = Field(
        ...,
        description="Whether any segment requires overnight travel.",
    )
    tight_connection: bool = Field(
        ...,
        description="Whether any connection is tight (<1.5h for flights, <30m for ground transit).",
    )
    total_travel_hours: float = Field(
        ...,
        description="Total door-to-door travel time in hours.",
        ge=0.0,
    )


class Scenario(BaseModel):
    """Combines a concrete itinerary option with cost, convenience metrics, and reasoning."""
    label: str = Field(
        ...,
        description="A short descriptive name (e.g., 'Scenario A: Express Flight & Coastal Hotel').",
    )
    comparison_label: str = Field(
        ...,
        description="A concise label for side-by-side display (e.g. 'Early September', 'Late August').",
    )
    start_date: date = Field(
        ...,
        description="Trip start date in ISO 8601 (e.g. 2026-09-04).",
    )
    end_date: date = Field(
        ...,
        description="Trip end date in ISO 8601 (e.g. 2026-09-11).",
    )
    travelers: int = Field(
        1,
        description=(
            "Number of travelers this scenario is priced for — set it to the same "
            "`passengers`/`guests` count used when searching flights and lodging. "
            "Transport leg costs and the cost breakdown are TOTALS for this many "
            "people, so the UI shows per-person fares as (leg cost / travelers)."
        ),
        ge=1,
    )
    itinerary: Itinerary = Field(..., description="The full travel itinerary for this scenario.")
    cost_breakdown: CostBreakdown = Field(
        ...,
        description="Itemized cost subtotals and grand total for the scenario.",
    )
    stress_score: int = Field(
        ...,
        description="A rating from 1 (relaxed) to 5 (highly stressful, tight connections, multiple layovers).",
        ge=1,
        le=5,
    )
    stress_factors: StressFactors = Field(
        ...,
        description="The concrete sub-factors behind the stress score.",
    )
    highlights: list[str] = Field(
        default_factory=list,
        description=(
            "2-4 short chips summarizing notable traits for at-a-glance scanning "
            "(e.g. '1 layover', 'Direct flight', 'Night ferry', 'Peak crowd')."
        ),
    )
    reasoning_summary: str = Field(
        ...,
        description="Explanation of why this scenario was chosen and the pros/cons of this option.",
    )
