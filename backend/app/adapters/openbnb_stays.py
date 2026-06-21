from typing import List
import random
from app.domain.models import StayDetail
from app.ports.stay_service import StayServicePort
import asyncio

class AirbnbStayService(StayServicePort):
    async def search_stays(self, location: str, check_in: str, check_out: str, guests: int = 2) -> List[StayDetail]:
        # Simulate network delay for MCP call
        await asyncio.sleep(1.5)
        # Return mock data for MVP
        base_price = random.uniform(80.0, 300.0)
        return [
            StayDetail(
                name=f"Luxury Villa in {location}",
                location=location,
                check_in=check_in,
                check_out=check_out,
                rating=random.uniform(4.0, 5.0),
                price_per_night_usd=base_price,
                total_price_usd=base_price * 4  # Assuming ~4 nights
            ),
            StayDetail(
                name=f"Cozy Downtown Apartment",
                location=location,
                check_in=check_in,
                check_out=check_out,
                rating=random.uniform(3.5, 4.8),
                price_per_night_usd=base_price * 0.6,
                total_price_usd=(base_price * 0.6) * 4
            )
        ]
