from enum import Enum
from pydantic import BaseModel, Field

class TicketPriority(str, Enum):
    """Enum para las prioridades de los tickets."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"


class TicketModel(BaseModel):
    """Modelo de un ticket de soporte."""
    ticketId: str = Field(..., description="ID único del ticket (ej. SOFT-20251211-001)")
    creationDate: str = Field(..., description="Fecha de creación en formato YYYY-MM-DD")
    priority: TicketPriority
    owner: str = Field(..., description="Nombre y departamento del solicitante")
    description: str = Field(..., description="Descripción detallada del problema")
    impact: str = Field(..., description="Impacto del problema en la productividad")
    actions: str = Field(..., description="Acciones tomadas por el solicitante antes de reportar")