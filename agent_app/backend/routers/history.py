from fastapi import APIRouter, Request
from core.security import get_authorized_user
from services.session_service import delete_user_session, get_session_history_messages

router = APIRouter(
    prefix="/history",
    tags=["history"],
)

@router.get("/{session_id}")
async def get_history_endpoint(session_id: str, http_request: Request):
    """
    Get the history of a specific session.
    
    Args:
        session_id: ID of the session to retrieve history for
        http_request: FastAPI Request object for authentication
        
    Returns:
        Dictionary with the agent's response
    """
    user = await get_authorized_user(http_request)
    # Reconstruct thread_id
    thread_id = f"{user['username']}_{session_id}"
    messages = await get_session_history_messages(thread_id)
    return {"messages": messages}

@router.delete("/{session_id}")
async def delete_history_endpoint(session_id: str, http_request: Request):
    """
    Delete a specific session.
    
    Args:
        session_id: ID of the session to delete
        http_request: FastAPI Request object for authentication
        
    Returns:
        Dictionary with the status of the operation
    """
    user = await get_authorized_user(http_request)
    await delete_user_session(user["username"], session_id)
    return {"status": "success", "message": "Session deleted"}
