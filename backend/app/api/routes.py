import uuid
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.agent.agent import handle_chat_session

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.post("/api/chat")
async def chat_endpoint(request: Request):
    """
    Endpoint for CopilotKit or AGUI frontend to interact with the Kompass agent.
    """
    body = await request.json()
    user_prompt = body.get("message", "")
    session_id = body.get("session_id", str(uuid.uuid4()))
    
    try:
        scenario_matrix = await handle_chat_session(session_id, user_prompt)
        
        return JSONResponse(content={
            "session_id": session_id,
            "response": scenario_matrix.model_dump()
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
