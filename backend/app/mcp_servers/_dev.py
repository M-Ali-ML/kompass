"""Shared dev helpers for the standalone MCP servers: mock mode + call logging.

These let you run the data MCP servers without hitting paid APIs (SerpApi) and
inspect exactly what each tool received and returned.

* ``MCP_MODE=mock`` → tools return deterministic, clearly-flagged fake data and
  make **no** network calls (and need no API key). Mock results carry
  ``estimated: true`` so the UI shows its "≈ approx" badge — a visible signal
  that you're not looking at live data.
* ``MCP_LOG_FILE=/path/to/mcp_calls.jsonl`` → every tool call's full request and
  response is appended as a JSON line for later inspection (in addition to the
  always-on compact INFO log line).

This module is imported both as a package module (``app.mcp_servers._dev`` — in
tests and the parent app) and as a top-level module (when a server is launched
directly as a subprocess via ``uv run .../server.py``, where only the script's
own directory is on ``sys.path``). Callers use a try/except to cover both.
"""

import json
import logging
import os
from datetime import datetime, timezone


def mock_mode() -> bool:
    """True when MCP servers should return canned data instead of calling paid APIs."""
    return os.getenv("MCP_MODE", "live").strip().lower() == "mock"


def log_call(
    logger: logging.Logger,
    server: str,
    tool: str,
    request: dict,
    response: dict,
) -> None:
    """Log an MCP tool call's input + output.

    Always emits a compact INFO line. If ``MCP_LOG_FILE`` is set, also appends
    the full request/response as a JSON line for later inspection.
    """
    opts = response.get("options")
    count = len(opts) if isinstance(opts, list) else None
    logger.info(
        "[%s] tool=%s mock=%s available=%s count=%s request=%s",
        server,
        tool,
        mock_mode(),
        response.get("available"),
        count,
        request,
    )

    path = os.getenv("MCP_LOG_FILE")
    if not path:
        return
    try:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "server": server,
            "tool": tool,
            "mock": mock_mode(),
            "request": request,
            "response": response,
        }
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as e:  # noqa: BLE001 - logging must never break a tool call
        logger.warning("Failed to write MCP_LOG_FILE %s: %s", path, e)
