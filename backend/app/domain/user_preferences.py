from pydantic import BaseModel, Field

class UserPreferences(BaseModel):
    """Stores traveler preferences extracted from conversation or profiles."""
    home_city: str | None = Field(
        default=None,
        description=(
            "The traveler's home/departure city or airport (e.g. 'Berlin' or 'BER'). "
            "Used as the default flight/transport origin so it doesn't need to be "
            "asked every trip."
        ),
    )
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
    currency: str = Field(
        default="EUR",
        description="ISO 4217 currency code used for all prices shown to the traveler (defaults to EUR).",
    )

    def merged_with(self, override: "UserPreferences") -> "UserPreferences":
        """Return a new UserPreferences where non-default fields of ``override`` win.

        Used to layer conversation-derived preferences on top of the stored
        global profile baseline without wiping values the override omitted.
        """
        merged = self.model_copy(deep=True)
        if override.home_city:
            merged.home_city = override.home_city
        if override.direct_flights_only:
            merged.direct_flights_only = True
        if override.preferred_transit_modes:
            merged.preferred_transit_modes = list(override.preferred_transit_modes)
        if override.hotel_class:
            merged.hotel_class = override.hotel_class
        if override.vibe_tags:
            merged.vibe_tags = list(override.vibe_tags)
        # Currency always carries a value ("EUR" default). Only let the override
        # win when it names a non-default currency, so a stored profile currency
        # isn't clobbered by an unspecified conversation default.
        if override.currency and override.currency != "EUR":
            merged.currency = override.currency
        return merged
