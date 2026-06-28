import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from pydantic_ai.messages import ModelResponse
from pydantic_ai.ui.ag_ui import AGUIAdapter
from pydantic_ai.usage import UsageLimits

from app.agent.agent import kompass_agent
from app.agent.dependency import get_agent_dependencies
from app.agent.image_agent import generate_trip_background
from app.api.dependencies import (
    get_profile_repository,
    get_saved_scenario_repository,
    get_trip_background_repository,
    get_trip_repository,
)
from app.config import settings
from app.domain import UserPreferences
from app.ports.saved_scenario_repository import SavedScenarioRepository
from app.ports.trip_background_repository import TripBackgroundRepository
from app.ports.trip_repository import TripRepository
from app.ports.user_profile_repository import UserProfileRepository
from app.telemetry import stream_with_attributes

logger = logging.getLogger("kompass.routes")

router = APIRouter()


# Preference fields copied verbatim from a `gather_preferences` tool call.
# `currency` is handled separately because it only overrides when truthy.
_PREFERENCE_FIELDS = (
    "home_city",
    "direct_flights_only",
    "preferred_transit_modes",
    "hotel_class",
    "vibe_tags",
)


def _log_agui_chunk(chunk) -> None:
    """Log AG-UI SSE events streamed back to the client.

    Each chunk is one or more SSE lines (``data: {json}``). Error events
    (``RUN_ERROR``) are always logged at ERROR level so failures surface in the
    logs immediately; the full event stream is logged at DEBUG only — set
    ``LOG_LEVEL=DEBUG`` to see every AG-UI interaction.
    """
    debug = logger.isEnabledFor(logging.DEBUG)
    try:
        text = chunk.decode("utf-8", "replace") if isinstance(chunk, (bytes, bytearray)) else str(chunk)
    except Exception:  # noqa: BLE001 - logging must never break the stream
        return

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if not payload:
            continue

        event_type = payload
        try:
            data = json.loads(payload)
            event_type = data.get("type", "?")
        except (ValueError, TypeError):
            pass

        is_error = isinstance(event_type, str) and "ERROR" in event_type.upper()
        if is_error:
            # Full payload, always — this is the line you want when a run fails.
            logger.error(f"AG-UI {event_type}: {payload}")
        elif debug:
            snippet = payload if len(payload) <= 2000 else f"{payload[:2000]}… ({len(payload)} bytes)"
            logger.debug(f"AG-UI {event_type}: {snippet}")


async def _log_agui_events(body_iterator):
    """Tee the AG-UI streaming body through :func:`_log_agui_chunk` for visibility."""
    async for chunk in body_iterator:
        _log_agui_chunk(chunk)
        yield chunk


def _message_role(message) -> str | None:
    """Read the role of an AG-UI message in either object or dict form."""
    return message.get("role") if isinstance(message, dict) else getattr(message, "role", None)


def _message_content(message) -> str | None:
    """Read the content of an AG-UI message in either object or dict form."""
    content = message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
    return content if isinstance(content, str) else None


def _conversation_text(ag_messages) -> str:
    """Join the user turns of an AG-UI message list into a single text blob the
    scene agent can read to infer the destination + vibe."""
    parts = [c for m in ag_messages if _message_role(m) == "user" and (c := _message_content(m))]
    return "\n".join(parts)


def _title_from_messages(messages) -> str:
    """Derive a human-friendly trip title from the first user turn.

    Accepts both AG-UI message objects and plain dicts so the same logic backs
    the live run and the client-side history save.
    """
    for message in messages:
        if _message_role(message) == "user" and (content := _message_content(message)) and content.strip():
            text = content.strip().replace("\n", " ")
            return text[:60] + ("…" if len(text) > 60 else "")
    return "New Trip"


def extract_preferences_from_history(messages) -> UserPreferences:
    prefs = UserPreferences()
    for message in messages:
        if not isinstance(message, ModelResponse):
            continue
        for part in message.parts:
            if part.part_kind != 'tool-call' or part.tool_name != 'gather_preferences':
                continue
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

            for field in _PREFERENCE_FIELDS:
                if field in args_dict:
                    setattr(prefs, field, args_dict[field])
            if args_dict.get('currency'):
                prefs.currency = args_dict['currency']
    return prefs


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
async def copilotkit_endpoint(
    request: Request,
    trip_repo: TripRepository = Depends(get_trip_repository),
    profile_repo: UserProfileRepository = Depends(get_profile_repository),
):
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
            await trip_repo.upsert_trip(thread_id, _title_from_messages(ag_messages))
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
        # Hardening: bound a single turn so a hung model call can't stall the
        # stream for minutes (logs showed a 600s default), and cap the agent
        # loop so a runaway tool/retry cycle can't burn unbounded time/cost.
        model_settings={"timeout": 60.0},
        usage_limits=UsageLimits(request_limit=30),
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
    if body_iterator is not None:
        # Defeat SSE buffering so AG-UI events reach the browser token-by-token
        # rather than in one batch at the end. `no-transform` stops proxies from
        # compressing/coalescing the stream, and `X-Accel-Buffering: no` disables
        # nginx-style response buffering in front of the app. (The pydantic-ai
        # AG-UI adapter sets only the `text/event-stream` content type.)
        response.headers["Cache-Control"] = "no-cache, no-transform"
        response.headers["X-Accel-Buffering"] = "no"
        response.headers["Connection"] = "keep-alive"
        # Tee the AG-UI event stream to the logger first (innermost wrapper) so
        # we see the raw events — including RUN_ERROR — exactly as sent. Error
        # events always log; the full stream logs at DEBUG (LOG_LEVEL=DEBUG).
        body_iterator = _log_agui_events(body_iterator)
        if thread_id:
            body_iterator = stream_with_attributes(
                body_iterator,
                session_id=thread_id,
                tags=["kompass-agent"],
            )
        response.body_iterator = body_iterator

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
async def list_trips(trip_repo: TripRepository = Depends(get_trip_repository)):
    trips = await trip_repo.list_trips()
    return {"trips": [_serialize_trip(t) for t in trips]}


@router.post("/api/trips")
async def create_trip(
    payload: CreateTripRequest,
    trip_repo: TripRepository = Depends(get_trip_repository),
):
    trip_id = payload.id or str(uuid.uuid4())
    trip = await trip_repo.create_trip(trip_id, payload.title or "New Trip")
    return _serialize_trip(trip)


@router.get("/api/trips/{trip_id}")
async def get_trip(
    trip_id: str,
    trip_repo: TripRepository = Depends(get_trip_repository),
):
    trip = await trip_repo.get_trip(trip_id)
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
async def save_trip_messages(
    trip_id: str,
    payload: SaveMessagesRequest,
    trip_repo: TripRepository = Depends(get_trip_repository),
):
    """Persist the full AG-UI message history for a trip (called by the client
    after each run so generative-UI cards survive a reload)."""
    title = payload.title or _title_from_messages(payload.messages)
    await trip_repo.save_message_history(trip_id, payload.messages, title=title)
    return {"status": "ok", "id": trip_id, "count": len(payload.messages)}


@router.get("/api/trips/{trip_id}/background.img")
async def get_trip_background_image(
    trip_id: str,
    background_repo: TripBackgroundRepository = Depends(get_trip_background_repository),
):
    """Serve a trip's generated vibe image, or 404 until it's ready.

    The frontend loads this directly in an <img> tag and hides the element on
    error, so a 404 (not generated yet / generation failed) degrades cleanly.
    """
    row = await background_repo.get(trip_id)
    if row is None or row.status != "ready" or not row.image:
        raise HTTPException(status_code=404, detail="No background image")
    return Response(
        content=row.image,
        media_type=row.mime or "image/webp",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.delete("/api/trips/{trip_id}")
async def delete_trip(
    trip_id: str,
    trip_repo: TripRepository = Depends(get_trip_repository),
):
    await trip_repo.delete_trip(trip_id)
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
async def save_scenario(
    payload: SaveScenarioRequest,
    saved_repo: SavedScenarioRepository = Depends(get_saved_scenario_repository),
):
    # Fold the comparison-level destination/currency into the scenario payload so
    # the saved record is self-contained and queryable.
    scenario = dict(payload.scenario or {})
    if payload.destination and not scenario.get("destination"):
        scenario["destination"] = payload.destination
    if payload.currency and not scenario.get("currency"):
        scenario["currency"] = payload.currency

    saved = await saved_repo.save(scenario=scenario, trip_id=payload.trip_id)
    return _serialize_saved(saved)


@router.get("/api/saved-scenarios")
async def list_saved_scenarios(
    trip_id: str | None = None,
    saved_repo: SavedScenarioRepository = Depends(get_saved_scenario_repository),
):
    saved = await saved_repo.list_saved(trip_id=trip_id)
    return {"saved": [_serialize_saved(s) for s in saved]}


@router.get("/api/saved-scenarios/{saved_id}")
async def get_saved_scenario(
    saved_id: int,
    saved_repo: SavedScenarioRepository = Depends(get_saved_scenario_repository),
):
    saved = await saved_repo.get(saved_id)
    if saved is None:
        raise HTTPException(status_code=404, detail="Saved scenario not found")
    return _serialize_saved(saved)


@router.delete("/api/saved-scenarios/{saved_id}")
async def delete_saved_scenario(
    saved_id: int,
    saved_repo: SavedScenarioRepository = Depends(get_saved_scenario_repository),
):
    await saved_repo.delete(saved_id)
    return {"status": "deleted", "id": saved_id}


# --- Global user profile -------------------------------------------------------

@router.get("/api/profile")
async def get_profile(
    profile_repo: UserProfileRepository = Depends(get_profile_repository),
):
    prefs = await profile_repo.get_preferences()
    return prefs.model_dump()


@router.put("/api/profile")
async def update_profile(
    preferences: UserPreferences,
    profile_repo: UserProfileRepository = Depends(get_profile_repository),
):
    await profile_repo.save_preferences(preferences)
    return preferences.model_dump()
