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

# Lazily-created google-genai client (needs GOOGLE_API_KEY, exported by config).
_genai_client = None


def _client():
    global _genai_client
    if _genai_client is None:
        from google import genai  # imported lazily so module import stays cheap

        _genai_client = genai.Client()
    return _genai_client


def _encode_image(raw: bytes, mime: str) -> tuple[bytes, str]:
    """Downscale + compress to a small WebP. Falls back to the raw bytes if
    Pillow is unavailable or the image can't be processed."""
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


async def _generate_image(scene_prompt: str) -> tuple[bytes, str]:
    """Render the scene with the configured Gemini image model. Returns
    (image_bytes, mime). Raises if the model returns no image part."""
    resp = await _client().aio.models.generate_content(
        model=settings.image_model,
        contents=scene_prompt,
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

    if trip_id in _in_flight:
        return

    repo = SqliteTripBackgroundRepository(SessionLocal)

    if not force:
        existing = await repo.get(trip_id)
        if existing is not None and existing.status in ("pending", "ready"):
            return

    _in_flight.add(trip_id)
    try:
        destination: str | None = None
        scene_prompt = override_scene
        if scene_prompt is None:
            scene = await _describe_scene(conversation_text, preferences)
            # No destination committed yet: don't lock a row, so a later turn can
            # retry once the traveler names a place.
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
