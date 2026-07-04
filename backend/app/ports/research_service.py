from abc import ABC, abstractmethod


class ResearchServicePort(ABC):
    """Port interface for grounded web research.

    Implementations are free to source grounded text from any provider (Gemini
    Google Search grounding, a search API, a deterministic fixture catalog for
    evals, ...). The agent depends only on this port.
    """

    @abstractmethod
    async def research(self, query: str) -> str:
        """Run a single grounded research query and return grounded text.

        Implementations should degrade gracefully: on provider failure, return
        a short human-readable note rather than raising, so the calling tool
        can surface it to the model.
        """
        ...
