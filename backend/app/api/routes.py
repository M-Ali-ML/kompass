import json
import logging
from fastapi import APIRouter, Request
from pydantic_ai.ui.ag_ui import AGUIAdapter
from pydantic_ai.messages import ModelResponse
from app.agent.agent import kompass_agent
from app.agent.dependency import get_agent_dependencies
from app.domain import UserPreferences

logger = logging.getLogger("kompass.routes")

router = APIRouter()

def extract_preferences_from_history(messages) -> UserPreferences:
    prefs = UserPreferences()
    for message in messages:
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if part.part_kind == 'tool-call' and part.tool_name == 'gather_preferences':
                    args = part.args
                    if isinstance(args, str):
                        try:
                            args_dict = json.loads(args)
                        except Exception:
                            args_dict = {}
                    elif isinstance(args, dict):
                        args_dict = args
                    else:
                        args_dict = {}
                    
                    if 'direct_flights_only' in args_dict:
                        prefs.direct_flights_only = args_dict['direct_flights_only']
                    if 'preferred_transit_modes' in args_dict:
                        prefs.preferred_transit_modes = args_dict['preferred_transit_modes']
                    if 'hotel_class' in args_dict:
                        prefs.hotel_class = args_dict['hotel_class']
                    if 'vibe_tags' in args_dict:
                        prefs.vibe_tags = args_dict['vibe_tags']
    return prefs

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.post("/api/copilotkit")
async def copilotkit_endpoint(request: Request):
    """AG-UI SSE streaming endpoint for CopilotKit frontend."""
    logger.info("Received request on /api/copilotkit")
    body = await request.body()
    user_preferences = UserPreferences()
    try:
        run_input = AGUIAdapter.build_run_input(body)
        logger.info(f"Parsed run input for thread ID: {run_input.thread_id}")
        messages = AGUIAdapter.load_messages(run_input.messages)
        logger.info(f"Loaded {len(messages)} messages from history.")
        user_preferences = extract_preferences_from_history(messages)
        logger.info(f"Reconstructed user preferences: {user_preferences}")
    except Exception as e:
        logger.error(f"Error extracting preferences from message history: {e}")

    deps = get_agent_dependencies(user_preferences=user_preferences)
    return await AGUIAdapter.dispatch_request(
        request,
        agent=kompass_agent,
        deps=deps,
    )


