from typing import List
import random
from app.domain.models import FlightDetail
from app.ports.flight_service import FlightServicePort
import asyncio

class FliFlightService(FlightServicePort):
    async def search_flights(self, origin: str, destination: str, date: str, passengers: int = 1) -> List[FlightDetail]:
        # Simulate network delay for MCP call
        await asyncio.sleep(1.5)
        # Return mock data for MVP
        return [
            FlightDetail(
                airline="SkyHigh Airlines",
                flight_number=f"SH{random.randint(100, 999)}",
                departure_time=f"{date}T10:00:00",
                arrival_time=f"{date}T14:30:00",
                origin=origin,
                destination=destination,
                duration_minutes=270,
                price_usd=random.uniform(150.0, 450.0)
            ),
            FlightDetail(
                airline="Global Airways",
                flight_number=f"GA{random.randint(100, 999)}",
                departure_time=f"{date}T16:00:00",
                arrival_time=f"{date}T20:15:00",
                origin=origin,
                destination=destination,
                duration_minutes=255,
                price_usd=random.uniform(180.0, 500.0)
            )
        ]
