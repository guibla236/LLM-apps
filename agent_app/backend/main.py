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

from model import TicketModel

API_MAIN_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

async def get_authorized_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_MAIN_URL}/api/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code != 200:
                # Propagate the error from the API instead of masking it
                detail = "Unknown error during token validation"
                try:
                    detail = response.json().get("detail", detail)
                except:
                    detail = response.text
                raise HTTPException(status_code=response.status_code, detail=detail)
            return response.json()
        except httpx.RequestError as e:
            # specifically log connection/network issues
            print(f"Error connecting to auth service at {API_MAIN_URL}: {str(e)}")
            raise HTTPException(status_code=401, detail="Could not connect to auth service")
        except HTTPException:
            # Re-raise HTTPExceptions we manually raised above
            raise
        except Exception as e:
            print(f"Unexpected error in get_authorized_user: {str(e)}")
            raise HTTPException(status_code=401, detail=f"Auth error: {str(e)}")

@app.post("/solve_ticket")
async def solve_ticket_endpoint(item: Item, request: Request):
    user = await get_authorized_user(request)
    try:
        # Convert dict to TicketModel
        ticket_model = TicketModel(**item.ticket)
        solution = await solve_ticket(ticket_model, username=user["username"])
        return {"solution": solution}
    except Exception as e:
        # This will be caught by the global handler if not caught here
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
