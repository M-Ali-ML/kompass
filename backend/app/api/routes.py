from fastapi import APIRouter, Request
from pydantic_ai.ui.ag_ui import AGUIAdapter
from app.agent.agent import kompass_agent
from app.agent.dependency import get_agent_dependencies

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.post("/api/copilotkit")
async def copilotkit_endpoint(request: Request):
    """AG-UI SSE streaming endpoint for CopilotKit frontend."""
    deps = get_agent_dependencies()
    return await AGUIAdapter.dispatch_request(
        request,
        agent=kompass_agent,
        deps=deps,
    )
