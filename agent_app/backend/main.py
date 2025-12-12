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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
