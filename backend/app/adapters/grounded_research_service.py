"""ResearchServicePort adapter backed by the Gemini-grounded research sub-agent."""

from app.agent.research_agent import run_research
from app.ports.research_service import ResearchServicePort


class GroundedResearchService(ResearchServicePort):
    """Delegates to the grounded web-search sub-agent (research_agent.py)."""

    async def research(self, query: str) -> str:
        return await run_research(query)
