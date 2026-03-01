import uvicorn
import os
import warnings
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import traceback
from core.logger import agent_logger
from services.agent_service import solve_ticket
from dotenv import load_dotenv
from schema.ticket import Item, TicketModel
from core.security import get_authorized_user

# Import routers
from routers.chat import router as chat_router
from routers.sessions import router as sessions_router
from routers.history import router as history_router

load_dotenv()

app = FastAPI(title="Ticket Resolution Agent API")

# Register routers
app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(history_router)

@app.get("/")
async def root():
    return {"message": "Agent Backend is running", "status": "online"}

@app.post(
    "/solve_ticket", 
    deprecated=True, 
    summary="DEPRECATED: Use /chat/solve_ticket instead", 
    description="This endpoint is deprecated. Please use /chat/solve_ticket for better performance and additional features."
)
async def solve_ticket_endpoint(item: Item, request: Request):
    warnings.warn(
        "The /solve_ticket endpoint is deprecated. Please use /chat/solve_ticket instead.",
        DeprecationWarning
    )
    user = await get_authorized_user(request)
    ticket_model = TicketModel(**item.ticket)
    solution = await solve_ticket(ticket_model, username=user["username"])
    return {"solution": solution}

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle HTTP exceptions (401, 403, 404, etc.) and log them to MongoDB.
    This allows us to track authentication failures and other HTTP errors.
    """
    user_info = "unknown"
    try:
        # Try to extract user info from the request if available
        auth_header = request.headers.get("Authorization")
        if auth_header:
            # We could decode the token here, but for simplicity just note it exists
            user_info = "authenticated_user"
    except:
        pass
    
    # Log HTTP exceptions to MongoDB
    error_id = await agent_logger.log_error(
        user=user_info,
        path=request.url.path,
        method=request.method,
        error_message=f"HTTP {exc.status_code}: {exc.detail}",
        traceback_data=f"HTTPException: {exc.status_code} - {exc.detail}"
    )
    
    # Log to console for debugging
    print(f"\n[ERROR_ID: {error_id}] HTTP EXCEPTION in Agent Backend:")
    print(f"Status: {exc.status_code}, Detail: {exc.detail}, Path: {request.url.path}")
    
    # Return the original HTTP exception response
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_id": error_id
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log to MongoDB centralized error_logs
    user_info = "agent_user"
    try:
        # Try to get user from state if available (future implementation)
        pass
    except:
        pass

    error_id = await agent_logger.log_error(
        user=user_info,
        path=request.url.path,
        method=request.method,
        error_message=str(exc),
        traceback_data=traceback.format_exc()
    )
    
    # Also log to console for debugging
    print(f"\n[ERROR_ID: {error_id}] GLOBAL EXCEPTION in Agent Backend:")
    print(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred in the Agent. Please try again later.",
            "error_id": error_id
        },
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
