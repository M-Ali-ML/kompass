import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from pydantic_ai.messages import ModelResponse
from pydantic_ai.ui.ag_ui import AGUIAdapter

from app.agent.agent import kompass_agent
from app.agent.dependency import get_agent_dependencies
from app.agent.image_agent import generate_trip_background
from app.config import settings
from app.db import SessionLocal
from app.domain import UserPreferences
from app.adapters.sqlite_trip_repository import SqliteTripRepository
from app.adapters.sqlite_trip_background_repository import SqliteTripBackgroundRepository
from app.adapters.sqlite_user_profile_repository import SqliteUserProfileRepository
from app.adapters.sqlite_saved_scenario_repository import SqliteSavedScenarioRepository
from app.telemetry import stream_with_attributes

logger = logging.getLogger("kompass.routes")

router = APIRouter()


def _trip_repository() -> SqliteTripRepository:
    return SqliteTripRepository(SessionLocal)


def _trip_background_repository() -> SqliteTripBackgroundRepository:
    return SqliteTripBackgroundRepository(SessionLocal)


def _conversation_text(ag_messages) -> str:
    """Join the user turns of an AG-UI message list into a single text blob the
    scene agent can read to infer the destination + vibe."""
    parts = []
    for m in ag_messages:
        if getattr(m, "role", None) == "user" and getattr(m, "content", None):
            parts.append(str(m.content))
    return "\n".join(parts)


def _profile_repository() -> SqliteUserProfileRepository:
    return SqliteUserProfileRepository(SessionLocal)


def _saved_scenario_repository() -> SqliteSavedScenarioRepository:
    return SqliteSavedScenarioRepository(SessionLocal)


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


def _title_from_messages(messages: list[dict]) -> str:
    """Derive a trip title from the first user turn of an AG-UI message list."""
    for m in messages:
        if m.get("role") == "user" and isinstance(m.get("content"), str) and m["content"].strip():
            text = m["content"].strip().replace("\n", " ")
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

    # Kick off the trip "vibe" background image as a fire-and-forget task so it
    # runs concurrently with — and never stalls — the agent stream. It guards
    # itself to run at most once per trip (and only once a destination is known).
    if settings.background_image_enabled and thread_id:
        convo_text = _conversation_text(ag_messages)
        if convo_text.strip():
            asyncio.create_task(
                generate_trip_background(thread_id, convo_text, user_preferences)
            )

    deps = get_agent_dependencies(user_preferences=user_preferences, trip_id=thread_id)

    async def on_complete(result) -> None:
        if not thread_id:
            return
        try:
            display = extract_display_messages(result.all_messages())
            await trip_repo.replace_messages(thread_id, display)
        except Exception as e:
            logger.error(f"Error persisting messages for trip {thread_id}: {e}")

    response = await AGUIAdapter.dispatch_request(
        request,
        agent=kompass_agent,
        deps=deps,
        on_complete=on_complete,
    )

    # The agent runs lazily as the streaming body is consumed (after this
    # handler returns), so trace attributes must wrap the body iterator rather
    # than the dispatch call. `session_id` groups all turns of a trip thread in
    # Langfuse; tags make agent traces easy to filter. (`session_id` is also
    # emitted automatically via the AG-UI threadId -> gen_ai.conversation.id
    # mapping, but we set it explicitly to be robust and add tags.) Only
    # streaming responses expose `body_iterator`; a non-streaming error response
    # (e.g. a 422) is returned untouched.
    body_iterator = getattr(response, "body_iterator", None)
    if thread_id and body_iterator is not None:
        response.body_iterator = stream_with_attributes(
            body_iterator,
            session_id=thread_id,
            tags=["kompass-agent"],
        )

    return response


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
        # Plain-text turns (legacy / fallback).
        "messages": [
            {"id": m.id, "role": m.role, "content": m.content}
            for m in trip.messages
        ],
        # Full AG-UI history (incl. tool calls + results) so the frontend can
        # rehydrate generative-UI cards on resume.
        "message_history": trip.message_history or [],
    }


class SaveMessagesRequest(BaseModel):
    messages: list[dict]
    title: str | None = None


@router.put("/api/trips/{trip_id}/messages")
async def save_trip_messages(trip_id: str, payload: SaveMessagesRequest):
    """Persist the full AG-UI message history for a trip (called by the client
    after each run so generative-UI cards survive a reload)."""
    title = payload.title or _title_from_messages(payload.messages)
    await _trip_repository().save_message_history(trip_id, payload.messages, title=title)
    return {"status": "ok", "id": trip_id, "count": len(payload.messages)}


@router.get("/api/trips/{trip_id}/background.img")
async def get_trip_background_image(trip_id: str):
    """Serve a trip's generated vibe image, or 404 until it's ready.

    The frontend loads this directly in an <img> tag and hides the element on
    error, so a 404 (not generated yet / generation failed) degrades cleanly.
    """
    row = await _trip_background_repository().get(trip_id)
    if row is None or row.status != "ready" or not row.image:
        raise HTTPException(status_code=404, detail="No background image")
    return Response(
        content=row.image,
        media_type=row.mime or "image/webp",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.delete("/api/trips/{trip_id}")
async def delete_trip(trip_id: str):
    await _trip_repository().delete_trip(trip_id)
    return {"status": "deleted", "id": trip_id}


# --- Saved scenarios -----------------------------------------------------------

class SaveScenarioRequest(BaseModel):
    scenario: dict
    trip_id: str | None = None
    destination: str | None = None
    currency: str | None = None


def _serialize_saved(s) -> dict:
    return {
        "id": s.id,
        "trip_id": s.trip_id,
        "destination": s.destination,
        "label": s.label,
        "comparison_label": s.comparison_label,
        "start_date": s.start_date,
        "end_date": s.end_date,
        "currency": s.currency,
        "grand_total": s.grand_total,
        "stress_score": s.stress_score,
        "scenario": s.scenario,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


@router.post("/api/saved-scenarios")
async def save_scenario(payload: SaveScenarioRequest):
    # Fold the comparison-level destination/currency into the scenario payload so
    # the saved record is self-contained and queryable.
    scenario = dict(payload.scenario or {})
    if payload.destination and not scenario.get("destination"):
        scenario["destination"] = payload.destination
    if payload.currency and not scenario.get("currency"):
        scenario["currency"] = payload.currency

    saved = await _saved_scenario_repository().save(scenario=scenario, trip_id=payload.trip_id)
    return _serialize_saved(saved)


@router.get("/api/saved-scenarios")
async def list_saved_scenarios(trip_id: str | None = None):
    saved = await _saved_scenario_repository().list_saved(trip_id=trip_id)
    return {"saved": [_serialize_saved(s) for s in saved]}


@router.get("/api/saved-scenarios/{saved_id}")
async def get_saved_scenario(saved_id: int):
    saved = await _saved_scenario_repository().get(saved_id)
    if saved is None:
        raise HTTPException(status_code=404, detail="Saved scenario not found")
    return _serialize_saved(saved)


@router.delete("/api/saved-scenarios/{saved_id}")
async def delete_saved_scenario(saved_id: int):
    await _saved_scenario_repository().delete(saved_id)
    return {"status": "deleted", "id": saved_id}


# --- Global user profile -------------------------------------------------------

@router.get("/api/profile")
async def get_profile():
    prefs = await _profile_repository().get_preferences()
    return prefs.model_dump()


@router.put("/api/profile")
async def update_profile(preferences: UserPreferences):
    await _profile_repository().save_preferences(preferences)
    return preferences.model_dump()
