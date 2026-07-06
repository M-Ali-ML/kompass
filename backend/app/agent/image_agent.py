"""Trip "vibe" background image generation.

A deliberately small, self-contained module that runs as a fire-and-forget
background task (never in the main agent's request path). It:

1. Uses a cheap text model (``scene_agent``) to turn the conversation into a
   destination + a vivid, photographic scene description.
2. Calls a cheap Gemini image model to render that scene.
3. Downscales/compresses the result and stores it on the trip's
   ``TripBackground`` row for the frontend to display.

Everything is wrapped so failures only log and never affect the chat stream.
Mirrors the separate-sub-agent pattern of ``research_agent.py``.
"""
import asyncio
import logging
from io import BytesIO

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.adapters.sqlite_trip_background_repository import SqliteTripBackgroundRepository
from app.config import settings
from app.db import SessionLocal
from app.domain.user_preferences import UserPreferences
from app.telemetry import trace_attributes

logger = logging.getLogger("kompass.image")


class BackgroundScene(BaseModel):
    """Structured output of the scene agent."""

    destination: str | None = Field(
        default=None,
        description=(
            "The primary travel destination named so far (city/region/country), "
            "or null if the conversation has not committed to one yet."
        ),
    )
    scene_prompt: str = Field(
        description=(
            "A vivid, photographic image-generation prompt depicting the "
            "destination and the traveler's vibe. No text, letters, words, "
            "logos, captions, maps, or watermarks."
        ),
    )


_SCENE_INSTRUCTIONS = (
    "You write image-generation prompts for a travel app. Given the conversation "
    "so far and the traveler's vibe tags, identify the primary destination and "
    "compose a single vivid, atmospheric, photographic scene that captures that "
    "place and mood (iconic scenery, golden light, seasonal feel). "
    "If no concrete destination has been chosen yet, set destination to null. "
    "The scene_prompt MUST NOT contain any text, letters, words, signage, logos, "
    "captions, maps, charts, or watermarks — purely a photographic landscape/"
    "cityscape. Keep it under 60 words."
)

# Cheap text model: conversation -> destination + scene prompt.
scene_agent = Agent(
    settings.image_scene_model,
    output_type=BackgroundScene,
    instructions=_SCENE_INSTRUCTIONS,
)

# Tracks trips currently being generated in THIS process so concurrent turns of
# the same conversation don't both kick off a job before the DB lock lands.
_in_flight: set[str] = set()

# Strong references to spawned tasks: asyncio only keeps weak refs to tasks, so
# a fire-and-forget task with no other reference can be garbage-collected
# mid-flight. Discarded on completion via the done callback.
_bg_tasks: set[asyncio.Task] = set()


def spawn_trip_background(*args, **kwargs) -> None:
    """Launch `generate_trip_background` as a tracked fire-and-forget task."""
    task = asyncio.create_task(generate_trip_background(*args, **kwargs))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)

# Lazily-created google-genai client (needs GOOGLE_API_KEY, exported by config).
_genai_client = None


def _client():
    global _genai_client
    if _genai_client is None:
        from google import genai  # imported lazily so module import stays cheap

        _genai_client = genai.Client()
    return _genai_client


# Cap decode size so a pathological model response can't balloon memory: skip
# compression for anything over ~24MB raw, and let Pillow refuse decompression
# bombs (its default MAX_IMAGE_PIXELS check stays enabled).
_MAX_RAW_BYTES = 24 * 1024 * 1024


def _encode_image(raw: bytes, mime: str) -> tuple[bytes, str]:
    """Downscale + compress to a small WebP. Falls back to the raw bytes if
    Pillow is unavailable or the image can't be processed."""
    if len(raw) > _MAX_RAW_BYTES:
        raise RuntimeError(f"Image response too large ({len(raw)} bytes); refusing to decode")
    try:
        from PIL import Image

        img = Image.open(BytesIO(raw)).convert("RGB")
        img.thumbnail((896, 896))
        buf = BytesIO()
        img.save(buf, format="WEBP", quality=72, method=6)
        return buf.getvalue(), "image/webp"
    except Exception as e:  # noqa: BLE001 - never fail generation over compression
        logger.warning("Image compression skipped (%s); storing raw bytes", e)
        return raw, mime or "image/png"


# Bound the image-model round-trip; the job is fire-and-forget, so a hung call
# would otherwise hold the in-flight lock for this trip forever.
_IMAGE_TIMEOUT_S = 120.0


def _image_config():
    """Build the image-generation config, requesting a landscape aspect ratio so
    the vibe image fills its wide banner frame. Returns None when no ratio is
    configured (model default) or the installed google-genai lacks the type, so
    generation degrades to the previous square behavior instead of failing."""
    ratio = (settings.image_aspect_ratio or "").strip()
    if not ratio:
        return None
    try:
        from google.genai import types

        return types.GenerateContentConfig(
            image_config=types.ImageConfig(aspect_ratio=ratio)
        )
    except Exception as e:  # noqa: BLE001 - config is an enhancement, never a hard dep
        logger.warning("Image aspect-ratio config unavailable (%s); using default", e)
        return None


async def _generate_image(scene_prompt: str) -> tuple[bytes, str]:
    """Render the scene with the configured Gemini image model. Returns
    (image_bytes, mime). Raises if the model returns no image part."""
    resp = await asyncio.wait_for(
        _client().aio.models.generate_content(
            model=settings.image_model,
            contents=scene_prompt,
            config=_image_config(),
        ),
        timeout=_IMAGE_TIMEOUT_S,
    )
    candidates = getattr(resp, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            inline = getattr(part, "inline_data", None)
            if inline is not None and getattr(inline, "data", None):
                raw = inline.data
                mime = getattr(inline, "mime_type", None) or "image/png"
                return await asyncio.to_thread(_encode_image, raw, mime)
    raise RuntimeError("Image model returned no image data")


async def _describe_scene(
    conversation_text: str, preferences: UserPreferences | None
) -> BackgroundScene | None:
    vibe = ", ".join(preferences.vibe_tags) if preferences and preferences.vibe_tags else "none"
    prompt = (
        f"Conversation so far:\n{conversation_text.strip()}\n\n"
        f"Traveler vibe tags: {vibe}"
    )
    try:
        result = await scene_agent.run(prompt)
        return result.output
    except Exception as e:  # noqa: BLE001 - degrade silently, just skip the image
        logger.error("Scene description failed: %s", e)
        return None


async def generate_trip_background(
    trip_id: str | None,
    conversation_text: str,
    preferences: UserPreferences | None,
    *,
    force: bool = False,
    override_scene: str | None = None,
) -> None:
    """Generate (or regenerate) a trip's background image.

    Designed to be launched via ``asyncio.create_task`` so it runs concurrently
    with the agent stream. Guarded so it runs at most once per trip unless
    ``force`` is set (explicit user request). Never raises.
    """
    if not settings.background_image_enabled or not trip_id:
        return

    # Claim the in-process slot SYNCHRONOUSLY — before the first `await` — so two
    # near-simultaneous turns of the same conversation can't both slip past the
    # guard and each fire the (LLM-backed) scene_agent describe step. Previously
    # `_in_flight.add` happened *after* `await repo.get`, so both turns saw an
    # empty set and empty row, and both described. Whoever loses the claim bails.
    if trip_id in _in_flight:
        return
    _in_flight.add(trip_id)
    # This is a detached fire-and-forget task, so its `scene_agent` spans are
    # created OUTSIDE the request's `stream_with_attributes` context and would
    # otherwise land as orphan root traces on the `default` environment. Stamp
    # them with the trip's `session_id` (== thread_id) and `environment` so they
    # group under the same Langfuse session as the conversation, and tag them
    # `background-image` so they can be filtered out of the main agent view.
    try:
        repo = SqliteTripBackgroundRepository(SessionLocal)

        # Short-circuit BEFORE describing the scene when a background already
        # exists (or is mid-flight) for this trip — this is the guard that keeps
        # the scene_agent from re-running on every follow-up turn. A forced regen
        # (explicit user request) always proceeds.
        if not force:
            existing = await repo.get(trip_id)
            if existing is not None and existing.status in ("pending", "ready"):
                return

        with trace_attributes(
            session_id=trip_id,
            environment="production",
            tags=["background-image"],
        ):
            destination: str | None = None
            scene_prompt = override_scene
            if scene_prompt is None:
                scene = await _describe_scene(conversation_text, preferences)
                # No destination committed yet: don't lock a row, so a later turn
                # can retry once the traveler names a place.
                if scene is None or not scene.destination:
                    logger.info("No destination yet for trip %s; skipping image", trip_id)
                    return
                destination = scene.destination
                scene_prompt = scene.scene_prompt

            # Claim the slot. For a forced regen we overwrite; otherwise the atomic
            # try_begin both locks and dedupes against concurrent turns.
            if force:
                await repo.set_status(trip_id, "pending")
            elif not await repo.try_begin(trip_id):
                return

            logger.info("Generating background for trip %s (dest=%r)", trip_id, destination)
            image_bytes, mime = await _generate_image(scene_prompt)
            await repo.save_ready(
                trip_id,
                destination=destination,
                scene_prompt=scene_prompt,
                image=image_bytes,
                mime=mime,
            )
    except Exception as e:  # noqa: BLE001 - background job must never crash the app
        logger.error("Background image generation failed for trip %s: %s", trip_id, e)
        try:
            await repo.set_status(trip_id, "error")
        except Exception:  # noqa: BLE001
            pass
    finally:
        _in_flight.discard(trip_id)
