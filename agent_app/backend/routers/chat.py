from fastapi import APIRouter, Request
from schema.chat import ChatRequest
from core.security import get_authorized_user
from services.agent_service import chat_with_agent

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)

@router.post("/")
async def chat_endpoint(request: ChatRequest, http_request: Request):
    """
    Chat endpoint that processes user messages through the agent.
    
    Args:
        request: ChatRequest containing message and session_id
        http_request: FastAPI Request object for authentication
        
    Returns:
        Dictionary with the agent's response
    """

    user = await get_authorized_user(http_request)
    
    # Use a combination of username and session_id as thread_id
    # This allows multiple independent sessions for the same user
    thread_id = f"{user['username']}_{request.session_id}"
    
    response, trace = await chat_with_agent(
        message=request.message, 
        thread_id=thread_id
    )
    
    return {"response": response, "trace": trace}
