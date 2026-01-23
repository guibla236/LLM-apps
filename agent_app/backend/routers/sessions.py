from fastapi import APIRouter, Request
from core.security import get_authorized_user
from services.session_service import get_user_sessions

router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
)

@router.get("/")
async def get_sessions_endpoint(http_request: Request):
    """
    Get the list of sessions for the authenticated user.
    
    Args:
        http_request: FastAPI Request object for authentication
        
    Returns:
        Dictionary with the list of sessions
    """
    user = await get_authorized_user(http_request)
    sessions = await get_user_sessions(user["username"])
    return {"sessions": sessions}
