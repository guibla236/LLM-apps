from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import traceback
from logger import agent_logger
from pydantic import BaseModel
from agent import solve_ticket
from dotenv import load_dotenv
import uvicorn
import os
import httpx

load_dotenv()

app = FastAPI(title="Ticket Resolution Agent API")

@app.get("/")
async def root():
    return {"message": "Agent Backend is running", "status": "online"}

class Item(BaseModel):
    ticket: dict

class ChatRequest(BaseModel):
    message: str
    session_id: str

from agent import solve_ticket, chat_with_agent, get_user_sessions, get_session_history_messages, delete_user_session
from model import TicketModel
from core.security import get_authorized_user

@app.post("/solve_ticket", deprecated=True)
async def solve_ticket_endpoint(item: Item, request: Request):
    user = await get_authorized_user(request)
    try:
        ticket_model = TicketModel(**item.ticket)
        solution = await solve_ticket(ticket_model, username=user["username"])
        return {"solution": solution}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat_endpoint(request: ChatRequest, http_request: Request):
    user = await get_authorized_user(http_request)
    try:
        # Use a combination of username and session_id as thread_id
        # This allows multiple independent sessions for the same user
        thread_id = f"{user['username']}_{request.session_id}"
        response = await chat_with_agent(
            message=request.message, 
            thread_id=thread_id
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions")
async def get_sessions_endpoint(http_request: Request):
    user = await get_authorized_user(http_request)
    try:
        sessions = await get_user_sessions(user["username"])
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{session_id}")
async def get_history_endpoint(session_id: str, http_request: Request):
    user = await get_authorized_user(http_request)
    try:
        # Reconstruct thread_id
        thread_id = f"{user['username']}_{session_id}"
        messages = await get_session_history_messages(thread_id)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.delete("/history/{session_id}")
async def delete_history_endpoint(session_id: str, http_request: Request):
    user = await get_authorized_user(http_request)
    try:
        await delete_user_session(user["username"], session_id)
        return {"status": "success", "message": "Session deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            "detail": "Ocurrió un error interno en el Agente. Por favor intente más tarde.",
            "error_id": error_id
        },
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
