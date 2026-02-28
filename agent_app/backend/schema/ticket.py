from enum import Enum
from pydantic import BaseModel, Field

class TicketPriority(str, Enum):
    """Enum for the priorities of the tickets."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"

class Item(BaseModel):
    ticket: dict

class TicketModel(BaseModel):
    """Model for a support ticket."""
    ticketId: str = Field(..., description="Unique ID of the ticket (ej. SOFT-20251211-001)")
    creationDate: str = Field(..., description="Creation date in YYYY-MM-DD format")
    priority: TicketPriority
    owner: str = Field(..., description="Name and department of the requester")
    description: str = Field(..., description="Detailed description of the problem")
    impact: str = Field(..., description="Impact of the problem on productivity")
    actions: str = Field(..., description="Actions taken by the requester before reporting")