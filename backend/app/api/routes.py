import json
import logging
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from pydantic_ai.messages import ModelResponse
from pydantic_ai.ui.ag_ui import AGUIAdapter

from app.agent.agent import kompass_agent
from app.agent.dependency import get_agent_dependencies
from app.db import SessionLocal
from app.domain import UserPreferences
from app.adapters.sqlite_trip_repository import SqliteTripRepository
from app.adapters.sqlite_user_profile_repository import SqliteUserProfileRepository

logger = logging.getLogger("kompass.routes")

router = APIRouter()


def _trip_repository() -> SqliteTripRepository:
    return SqliteTripRepository(SessionLocal)


def _profile_repository() -> SqliteUserProfileRepository:
    return SqliteUserProfileRepository(SessionLocal)


def extract_preferences_from_history(messages) -> UserPreferences:
    prefs = UserPreferences()
    for message in messages:
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if part.part_kind == 'tool-call' and part.tool_name == 'gather_preferences':
                    args = part.args
                    if isinstance(args, str):
                        try:
                            args_dict = json.loads(args)
                        except Exception:
                            args_dict = {}
                    elif isinstance(args, dict):
                        args_dict = args
                    else:
                        args_dict = {}

                    if 'direct_flights_only' in args_dict:
                        prefs.direct_flights_only = args_dict['direct_flights_only']
                    if 'preferred_transit_modes' in args_dict:
                        prefs.preferred_transit_modes = args_dict['preferred_transit_modes']
                    if 'hotel_class' in args_dict:
                        prefs.hotel_class = args_dict['hotel_class']
                    if 'vibe_tags' in args_dict:
                        prefs.vibe_tags = args_dict['vibe_tags']
                    if 'currency' in args_dict and args_dict['currency']:
                        prefs.currency = args_dict['currency']
    return prefs


def _derive_title(ag_messages) -> str:
    """Use the first user message as a human-friendly trip title."""
    for message in ag_messages:
        if getattr(message, "role", None) == "user" and getattr(message, "content", None):
            text = message.content.strip().replace("\n", " ")
            return text[:60] + ("…" if len(text) > 60 else "")
    return "New Trip"


def extract_display_messages(model_messages) -> list[dict]:
    """Flatten PydanticAI message history into user/assistant text turns."""
    out: list[dict] = []
    for msg in model_messages:
        for part in getattr(msg, "parts", []):
            kind = getattr(part, "part_kind", None)
            if kind == "user-prompt":
                content = part.content
                if isinstance(content, list):
                    content = " ".join(str(c) for c in content)
                out.append({"role": "user", "content": str(content)})
            elif kind == "text" and getattr(part, "content", None):
                out.append({"role": "assistant", "content": part.content})
    return out


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.post("/api/copilotkit")
async def copilotkit_endpoint(request: Request):
    """AG-UI SSE streaming endpoint for CopilotKit frontend."""
    logger.info("Received request on /api/copilotkit")
    body = await request.body()

    thread_id: str | None = None
    ag_messages: list = []
    convo_prefs = UserPreferences()
    try:
        run_input = AGUIAdapter.build_run_input(body)
        thread_id = run_input.thread_id
        ag_messages = run_input.messages
        logger.info(f"Parsed run input for thread ID: {thread_id}")
        messages = AGUIAdapter.load_messages(run_input.messages)
        logger.info(f"Loaded {len(messages)} messages from history.")
        convo_prefs = extract_preferences_from_history(messages)
        logger.info(f"Reconstructed conversation preferences: {convo_prefs}")
    except Exception as e:
        logger.error(f"Error parsing AG-UI run input: {e}")

    trip_repo = _trip_repository()
    profile_repo = _profile_repository()

    # Layer conversation preferences on top of the stored global profile baseline.
    try:
        baseline = await profile_repo.get_preferences()
    except Exception as e:
        logger.error(f"Error loading global profile: {e}")
        baseline = UserPreferences()
    user_preferences = baseline.merged_with(convo_prefs)
    logger.info(f"Effective user preferences for run: {user_preferences}")

    # Ensure a trip row exists for this thread so messages can be persisted.
    if thread_id:
        try:
            await trip_repo.upsert_trip(thread_id, _derive_title(ag_messages))
        except Exception as e:
            logger.error(f"Error upserting trip {thread_id}: {e}")

    deps = get_agent_dependencies(user_preferences=user_preferences, trip_id=thread_id)

    async def on_complete(result) -> None:
        if not thread_id:
            return
        try:
            display = extract_display_messages(result.all_messages())
            await trip_repo.replace_messages(thread_id, display)
        except Exception as e:
            logger.error(f"Error persisting messages for trip {thread_id}: {e}")

    return await AGUIAdapter.dispatch_request(
        request,
        agent=kompass_agent,
        deps=deps,
        on_complete=on_complete,
    )


# --- Session / trip management -------------------------------------------------

class CreateTripRequest(BaseModel):
    id: str | None = None
    title: str | None = None


def _serialize_trip(trip) -> dict:
    return {
        "id": trip.id,
        "title": trip.title,
        "status": trip.status,
        "created_at": trip.created_at.isoformat() if trip.created_at else None,
        "updated_at": trip.updated_at.isoformat() if trip.updated_at else None,
    }


@router.get("/api/trips")
async def list_trips():
    trips = await _trip_repository().list_trips()
    return {"trips": [_serialize_trip(t) for t in trips]}


@router.post("/api/trips")
async def create_trip(payload: CreateTripRequest):
    trip_id = payload.id or str(uuid.uuid4())
    trip = await _trip_repository().create_trip(trip_id, payload.title or "New Trip")
    return _serialize_trip(trip)


@router.get("/api/trips/{trip_id}")
async def get_trip(trip_id: str):
    trip = await _trip_repository().get_trip(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {
        **_serialize_trip(trip),
        "messages": [
            {"id": m.id, "role": m.role, "content": m.content}
            for m in trip.messages
        ],
    }


@router.delete("/api/trips/{trip_id}")
async def delete_trip(trip_id: str):
    await _trip_repository().delete_trip(trip_id)
    return {"status": "deleted", "id": trip_id}


# --- Global user profile -------------------------------------------------------

@router.get("/api/profile")
async def get_profile():
    prefs = await _profile_repository().get_preferences()
    return prefs.model_dump()


@router.put("/api/profile")
async def update_profile(preferences: UserPreferences):
    await _profile_repository().save_preferences(preferences)
    return preferences.model_dump()
