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

from pydantic_ai import Agent
from pydantic_ai.capabilities import WebSearch

from app.config import settings

logger = logging.getLogger("kompass.research")

RESEARCH_INSTRUCTIONS = """\
You are Kompass's travel research assistant. Use web search to answer the \
query with current, real-world facts.

Guidelines:
- Prefer concrete numbers: price ranges, typical durations, number of stops, \
  nightly hotel rates, ratings. Always say prices are approximate and note the \
  rough date/source they reflect.
- For flights: give a realistic price range and example carriers/routes for \
  the requested dates; mention if it is direct or requires a connection.
- For accommodation: list a few concrete options (name, area, approx nightly \
  price, rating) when asked.
- Keep the answer compact and factual — a few short bullets, not an essay. \
  This text is consumed by another agent, not shown verbatim to the user.
- Report prices in the currency requested in the query (default EUR).
- If the web results are thin or conflicting, say so plainly rather than \
  inventing precise figures.
"""

# Single-capability agent: native web search only, plain-text output, no
# function tools and no structured output (see module docstring).
research_agent = Agent(
    settings.llm_model,
    output_type=str,
    capabilities=[WebSearch()],
    instructions=RESEARCH_INSTRUCTIONS,
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
