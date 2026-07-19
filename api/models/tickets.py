from enum import Enum
from pydantic import BaseModel, Field

class TicketPriority(str, Enum):
    """Enum for ticket priorities."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"


class TicketModel(BaseModel):
    """Model for a support ticket (synthetic or Stack Exchange Q&A)."""
    ticketId: str = Field(..., description="Unique ticket ID (e.g. DEV-20251211-001 or SE-SUPERUSER-142340)")
    creationDate: str = Field(default="", description="Creation date (YYYY-MM-DD). Empty for Stack Exchange entries.")
    priority: TicketPriority
    owner: str = Field(default="community", description="Requester name. Defaults to 'community' for SE entries.")
    description: str = Field(..., description="Problem description / title_body from Stack Exchange")
    impact: str = Field(default="", description="Business impact. Empty for SE entries (not applicable).")
    actions: str = Field(default="", description="Actions taken before reporting. Empty for SE entries.")
    expected_output: str = Field(
        default="",
        description="Canonical answer (upvoted_answer for Stack Exchange). Empty for legacy synthetic."
    )
    community: str = Field(
        default="",
        description="Stack Exchange community (superuser, askubuntu, ...). Empty for synthetic tickets."
    )