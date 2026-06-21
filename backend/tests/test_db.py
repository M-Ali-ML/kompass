import pytest
import os
import asyncio
from app.adapters.db_sqlite import SQLiteTripRepository
from app.domain.models import ScenarioMatrix, UserPreferenceProfile, ItineraryScenario

@pytest.fixture
def temp_db():
    db_path = "test_kompass.db"
    # Ensure fresh start
    if os.path.exists(db_path):
        os.remove(db_path)
    
    repo = SQLiteTripRepository(db_path=db_path)
    yield repo
    
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.mark.asyncio
async def test_user_profile_persistence(temp_db):
    profile = UserPreferenceProfile(
        user_id="user123",
        preferred_vibe=["Beach Bliss", "Culture"],
        budget_max_usd=3000.0,
        max_flight_stops=1,
        preferred_hotel_rating=4
    )
    
    # Save
    await temp_db.save_user_profile(profile)
    
    # Retrieve
    retrieved = await temp_db.get_user_profile("user123")
    assert retrieved is not None
    assert retrieved.user_id == "user123"
    assert retrieved.preferred_vibe == ["Beach Bliss", "Culture"]
    assert retrieved.budget_max_usd == 3000.0

@pytest.mark.asyncio
async def test_messages_persistence(temp_db):
    session_id = "session_test"
    await temp_db.append_message(session_id, "user", "I want to go to Bali")
    await temp_db.append_message(session_id, "agent", "Here is a beach itinerary")
    
    messages = await temp_db.get_messages(session_id)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "I want to go to Bali"
    assert messages[1]["role"] == "agent"
    assert messages[1]["content"] == "Here is a beach itinerary"

@pytest.mark.asyncio
async def test_scenario_matrix_persistence(temp_db):
    session_id = "session_matrix"
    matrix = ScenarioMatrix(
        scenarios=[
            ItineraryScenario(
                scenario_id="sc1",
                title="Bali Plan",
                summary="Chilled out beach trip",
                transportation_subtotal_usd=400.0,
                accommodation_subtotal_usd=600.0,
                grand_total_usd=1000.0,
                stress_score=1,
                flights=[],
                stays=[],
                itinerary=[]
            )
        ],
        active_constraints=["$2500 Budget"]
    )
    
    await temp_db.save_scenario_matrix(session_id, matrix)
    
    retrieved = await temp_db.get_scenario_matrix(session_id)
    assert retrieved is not None
    assert len(retrieved.scenarios) == 1
    assert retrieved.scenarios[0].title == "Bali Plan"
    assert retrieved.active_constraints == ["$2500 Budget"]
