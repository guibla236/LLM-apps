from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import solve_ticket
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Ticket Resolution Agent API")

class Item(BaseModel):
    ticket: dict

from model import TicketModel

@app.post("/solve_ticket")
async def solve_ticket_endpoint(item: Item):
    try:
        # Convert dict to TicketModel
        ticket_model = TicketModel(**item.ticket)
        solution = solve_ticket(ticket_model)
        return {"solution": solution}
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
    uvicorn.run(app, host="0.0.0.0", port=8001)
