import pytest


@pytest.fixture(autouse=True)
def _stub_grounded_research(monkeypatch):
    """Prevent the grounded web-search sub-agent from making real network calls.

    `TestModel` auto-invokes every registered tool, including `search_web`,
    which would otherwise delegate to the live Gemini grounding sub-agent.
    Individual tests that exercise `search_web` directly override this with
    their own stub.
    """

    async def _fast_research(query: str) -> str:
        return "STUBBED_RESEARCH"

    import app.agent.agent as agent_mod

    monkeypatch.setattr(agent_mod, "run_research", _fast_research, raising=False)
