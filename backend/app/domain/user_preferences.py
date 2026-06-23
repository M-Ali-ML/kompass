from pydantic import BaseModel, Field

class UserPreferences(BaseModel):
    """Stores traveler preferences extracted from conversation or profiles."""
    direct_flights_only: bool = Field(
        default=False, 
        description="Whether the user strictly prefers direct flights."
    )
    preferred_transit_modes: list[str] = Field(
        default_factory=list, 
        description="List of preferred modes of transport (e.g., ['train', 'flight'])."
    )
    hotel_class: str | None = Field(
        default=None, 
        description="Preferred accommodation standard (e.g., '3-star', '5-star boutique')."
    )
    vibe_tags: list[str] = Field(
        default_factory=list, 
        description="Vibe descriptors (e.g., ['adventure', 'foodie', 'relaxation', 'history'])."
    )
