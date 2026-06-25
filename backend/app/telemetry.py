"""Langfuse / OpenTelemetry instrumentation for the Pydantic AI agents.

Langfuse v4 is OpenTelemetry-based and Pydantic AI emits OTel spans natively
(via its logfire integration), so wiring tracing in is two steps:

1. ``get_client()`` initializes the Langfuse OTel tracer provider + exporter
   using the ``LANGFUSE_*`` credentials (exported to the environment in
   ``app.config``).
2. ``Agent.instrument_all()`` makes every Pydantic AI ``Agent`` instance
   (the main ``kompass_agent`` and the ``research_agent``) export spans into
   that provider — capturing each LLM request, tool call, input, and output.

Everything is a no-op when Langfuse keys are absent, so local/dev runs work
unconfigured.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import nullcontext
from typing import Any

from app.config import settings

logger = logging.getLogger("kompass.telemetry")

_enabled = False


def telemetry_enabled() -> bool:
    """True once Langfuse instrumentation has been successfully initialized."""
    return _enabled


def init_telemetry() -> None:
    """Initialize Langfuse and auto-instrument all Pydantic AI agents.

    Safe to call once at startup. Does nothing (and logs why) when the
    Langfuse keys are not configured, or when the langfuse import fails.
    """
    global _enabled

    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        logger.info("Langfuse keys not set; skipping agent instrumentation.")
        return

    try:
        from langfuse import get_client
        from pydantic_ai import Agent
    except ImportError as e:  # pragma: no cover - defensive, deps are declared
        logger.warning(f"Langfuse/Pydantic AI telemetry unavailable: {e}")
        return

    # get_client() reads LANGFUSE_* from the environment (see app.config) and
    # sets up the OTel tracer provider + exporter pointed at Langfuse.
    client = get_client()
    try:
        if not client.auth_check():
            logger.warning(
                "Langfuse auth check failed; spans may not be delivered. "
                "Verify LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_BASE_URL."
            )
    except Exception as e:  # noqa: BLE001 - never let telemetry break startup
        logger.warning(f"Langfuse auth check errored (continuing): {e}")

    # Instrument every Agent instance globally (main + research sub-agent).
    Agent.instrument_all()
    _enabled = True
    logger.info("Langfuse instrumentation enabled for Pydantic AI agents.")


def flush_telemetry() -> None:
    """Flush any buffered spans. Call on application shutdown."""
    if not _enabled:
        return
    try:
        from langfuse import get_client

        get_client().flush()
        logger.info("Flushed Langfuse telemetry buffer.")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to flush Langfuse telemetry: {e}")


def trace_attributes(
    *,
    session_id: str | None = None,
    user_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
):
    """Context manager that stamps trace-level attributes onto spans created within it.

    Returns a no-op context manager when telemetry is disabled so callers don't
    need to branch. Attributes only attach to spans created *after* the context
    is entered, so it must wrap the actual agent execution (see
    ``stream_with_attributes`` for the streaming case).
    """
    if not _enabled:
        return nullcontext()
    from langfuse import propagate_attributes

    return propagate_attributes(
        session_id=session_id,
        user_id=user_id,
        tags=tags,
        metadata=metadata,
    )


async def stream_with_attributes(
    body_iterator: AsyncIterator[Any],
    *,
    session_id: str | None = None,
    user_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AsyncIterator[Any]:
    """Wrap a streaming-response body iterator so trace attributes cover the run.

    Pydantic AI's AG-UI adapter runs the agent *lazily* while the streaming
    response body is consumed — i.e. after the HTTP handler returns. Wrapping the
    handler call in ``propagate_attributes`` would therefore exit before any span
    is created. Instead we keep the context open across the body iteration so the
    spans the agent creates while streaming inherit ``session_id`` / ``tags`` /
    etc.
    """
    with trace_attributes(
        session_id=session_id,
        user_id=user_id,
        tags=tags,
        metadata=metadata,
    ):
        async for chunk in body_iterator:
            yield chunk
