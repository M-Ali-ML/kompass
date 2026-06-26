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


@pytest.fixture(autouse=True)
def _default_live_mcp_mode(monkeypatch):
    """Default the data MCP servers to live mode for tests.

    The repo `.env` may set ``MCP_MODE=mock`` for local dev (exported to
    os.environ at import via app.config). Most tests exercise the live SerpApi
    code paths, so force ``live`` by default; the dedicated mock-mode tests
    opt in with their own ``monkeypatch.setenv("MCP_MODE", "mock")``.
    """
    monkeypatch.setenv("MCP_MODE", "live")
