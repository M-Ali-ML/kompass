import pytest

# Grounded web research is injected via AgentDependencies.research_service
# (ResearchServicePort). Tests build deps without it (None), so `search_web` /
# `search_ground_transport` degrade to a soft "unavailable" message and never
# hit the network — even when `TestModel` auto-invokes every registered tool.
# Tests that exercise research behavior inject their own fake service.


@pytest.fixture(autouse=True)
def _default_live_mcp_mode(monkeypatch):
    """Default the data MCP servers to live mode for tests.

    The repo `.env` may set ``MCP_MODE=mock`` for local dev (exported to
    os.environ at import via app.config). Most tests exercise the live SerpApi
    code paths, so force ``live`` by default; the dedicated mock-mode tests
    opt in with their own ``monkeypatch.setenv("MCP_MODE", "mock")``.
    """
    monkeypatch.setenv("MCP_MODE", "live")
