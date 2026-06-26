from abc import ABC, abstractmethod

from app.domain.accommodations import AccommodationOption


class AccommodationServicePort(ABC):
    """Port interface for fetching live accommodation availability and pricing.

    Implementations are free to source data from any provider (Google Hotels,
    Booking.com, ...). The agent depends only on this port.
    """

    @abstractmethod
    async def search_accommodations(
        self,
        destination: str,
        *,
        check_in_date: str,
        check_out_date: str,
        guests: int = 2,
        max_price: int | None = None,
        min_rating: float | None = None,
        currency: str = "EUR",
    ) -> list[AccommodationOption]:
        """Search lodging options for a stay.

        Args:
            destination: City / area / property query (e.g. 'Santorini').
            check_in_date: Check-in date in YYYY-MM-DD format.
            check_out_date: Check-out date in YYYY-MM-DD format.
            guests: Number of adult guests.
            max_price: Optional maximum nightly rate to cap results.
            min_rating: Optional minimum guest rating (e.g. 4.0) to filter results.
            currency: ISO 4217 currency code for returned prices.

        Returns:
            A list of ranked accommodation options (cheapest first).
        """
        ...
