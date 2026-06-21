import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.agent.agent import kompass_agent
from app.agent.dependency import get_agent_dependencies
import uuid

# In a real setup, we would integrate copilotkit-python here,
# e.g., from copilotkit import CopilotKitRemoteEndpoint
# But for MVP scaffolding, we set up standard FastAPI.

app = FastAPI(title="Kompass Backend API")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """
    Endpoint for CopilotKit or AGUI frontend to interact with the Kompass agent.
    """
    body = await request.json()
    user_prompt = body.get("message", "")
    session_id = body.get("session_id", str(uuid.uuid4()))
    
    # 1. Inject Dependencies for this session
    deps = get_agent_dependencies(session_id)
    
    # 2. Save user message to repository
    await deps.repository.append_message(session_id, "user", user_prompt)
    
    # 3. Run Agent
    try:
        # We pass the dependencies into the run context
        result = await kompass_agent.run(user_prompt, deps=deps)
        
        # result.output is guaranteed to be a ScenarioMatrix based on output_type
        await deps.repository.save_scenario_matrix(session_id, result.output)
        await deps.repository.append_message(session_id, "agent", result.output.model_dump_json())
        
        return JSONResponse(content={
            "session_id": session_id,
            "response": result.output.model_dump()
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
