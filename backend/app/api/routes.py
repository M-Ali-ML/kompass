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
    Endpoint for FE to interact with the Kompass agent.
    """
    body = await request.json()
    user_prompt = body.get("message", "")
    
    try:
        response_text = await handle_chat_session(user_prompt)
        return JSONResponse(content={
            "response": response_text
        })
    except Exception as e:
        err_msg = str(e)
        # Check nested exceptions if it's an ExceptionGroup
        if isinstance(e, BaseExceptionGroup):
            err_msg = " | ".join(str(sub_e) for sub_e in e.exceptions)
        
        if "503" in err_msg or "temporarily unavailable" in err_msg.lower() or "high demand" in err_msg.lower() or "unavailable" in err_msg.lower():
            friendly_msg = "The AI model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again in a few seconds."
            return JSONResponse(content={"error": friendly_msg}, status_code=503)
        
        return JSONResponse(content={"error": err_msg}, status_code=500)
