"""Application logging configuration.

Centralizes how Kompass configures Python logging from the ``LOG_LEVEL``
setting. Keeping this cross-cutting concern here — rather than in the FastAPI
entrypoint (``app.main``) — mirrors how observability lives in
``app.telemetry``, so the entrypoint stays thin.
"""

import json
import logging

from app.config import settings

logger = logging.getLogger("kompass.logging")


def configure_logging() -> None:
    """Configure logging verbosity from the ``LOG_LEVEL`` setting.

    Safe to call once at startup. At DEBUG, emit a one-time redacted dump of the
    effective settings so it is easy to confirm how the app is configured (data
    mode, model, etc.) without leaking secrets.
    """
    level = getattr(logging, settings.log_level.strip().upper(), logging.INFO)
    logging.basicConfig(level=level)
    # Keep our own namespaces and the agent framework at the chosen level even if
    # an upstream (e.g. uvicorn) already configured the root logger handlers.
    logging.getLogger("kompass").setLevel(level)
    logging.getLogger("pydantic_ai").setLevel(level)

    logger.info(
        "Logging at %s | data mode: %s",
        logging.getLevelName(level),
        settings.mcp_mode.upper(),
    )
    if level <= logging.DEBUG:
        # model_dump(mode="json") renders SecretStr fields as "**********",
        # so secrets never reach the logs.
        logger.debug(
            "Effective settings (secrets masked):\n%s",
            json.dumps(settings.model_dump(mode="json"), indent=2, default=str, ensure_ascii=False),
        )
