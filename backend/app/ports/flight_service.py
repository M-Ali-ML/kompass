from abc import ABC, abstractmethod

from app.domain.flights import FlightDateOption, FlightOption


class FlightServicePort(ABC):
    """Port interface for fetching live flight pricing and date data.

    Implementations are free to source data from any provider (Google Flights,
    Amadeus, a synthetic estimator, ...). The agent depends only on this port.
    """

    @abstractmethod
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        *,
        passengers: int = 1,
        max_stops: int | None = None,
        preferred_time: str | None = None,
        currency: str = "EUR",
    ) -> list[FlightOption]:
        """Search one-way flights for a specific departure date.

        Args:
            origin: Departure airport IATA code (e.g. 'BER').
            destination: Arrival airport IATA code (e.g. 'ATH').
            departure_date: Outbound date in YYYY-MM-DD format.
            passengers: Number of adult passengers.
            max_stops: Maximum allowed stops (0 = direct). None = no limit.
            preferred_time: Optional departure time window as 'HH-HH' (e.g. '6-20').
            currency: ISO 4217 currency code for returned prices.

        Returns:
            A list of ranked flight options (cheapest first).
        """
        ...

    @abstractmethod
    async def find_cheapest_dates(
        self,
        origin: str,
        destination: str,
        *,
        date_from: str,
        date_to: str,
        duration_days: int | None = None,
        currency: str = "EUR",
    ) -> list[FlightDateOption]:
        """Find the cheapest travel-date windows within a range.

        Args:
            origin: Departure airport IATA code.
            destination: Arrival airport IATA code.
            date_from: Start of the search window (YYYY-MM-DD).
            date_to: End of the search window (YYYY-MM-DD).
            duration_days: Trip length in days for round-trip pricing (None = one-way).
            currency: ISO 4217 currency code for returned prices.

        Returns:
            A list of date options ranked by price (cheapest first).
        """
        ...
