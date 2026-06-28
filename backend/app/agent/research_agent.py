"""Grounded web-research sub-agent.

This is a deliberately small, single-purpose agent whose only capability is
the model's **native web search** (for Gemini this maps to Google Search
grounding, billed to the configured Google/Gemini credits). It is kept
separate from the main ``kompass_agent`` on purpose:

* Gemini does not reliably combine native search grounding with function
  tools *and* structured output in a single request. Isolating grounding in
  its own agent sidesteps that limitation.
* It gives the main agent a single, deep tool (``search_web``) with a simple
  string-in / string-out interface, rather than leaking grounding mechanics
  into the planning agent.

The main agent calls this via the ``search_web`` tool to fetch current,
real-world data — flight price ranges and dates, hotel options, "best time to
visit", visa notes, etc. — which the live (unofficial) flights endpoint cannot
reliably provide from every network.
"""

import logging
import os

from pydantic_ai import Agent
from pydantic_ai.capabilities import WebSearch

from app.adapters.file_prompt_service import FilePromptService
from app.config import settings

logger = logging.getLogger("kompass.research")

# Resolve the research prompt through the same PromptServicePort abstraction the
# main agent uses (see app/agent/dependency.py). Keeping the text in
# prompts/research_prompt.md — rather than inline — means a future swap to a
# Langfuse-backed prompt registry is a single change at the service layer.
_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")
_prompt_service: FilePromptService = FilePromptService(_PROMPTS_DIR)
RESEARCH_INSTRUCTIONS = _prompt_service.get_prompt("research_prompt")

# Single-capability agent: native web search only, plain-text output, no
# function tools and no structured output (see module docstring).
research_agent = Agent(
    settings.research_model,
    output_type=str,
    capabilities=[WebSearch()],
    instructions=RESEARCH_INSTRUCTIONS,
    # Disable Gemini's reasoning phase (thinking_budget=0 on gemini-2.5-flash).
    # These are quick, grounded lookups returning plain text — thinking only adds
    # latency, and several of these run in parallel per turn, so the saved time
    # compounds and keeps context out of the slow/fragile final synthesis path.
    model_settings={'thinking': False},
)


async def run_research(query: str) -> str:
    """Run a single grounded web-research query and return the grounded text.

    Returns a short human-readable note on failure rather than raising, so the
    calling tool degrades gracefully.
    """
    logger.info(f"Running grounded web research: {query!r}")
    try:
        result = await research_agent.run(query)
        return result.output
    except Exception as e:  # noqa: BLE001 - surface provider errors as a soft message
        logger.error(f"Grounded web research failed: {e}")
        return f"(Live web search was unavailable: {e})"
