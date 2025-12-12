"""
Módulo para la funcionalidad de resumen de noticias.
Este archivo contiene la estructura mock para que implementes la funcionalidad.
"""

import sys
import json
from pydantic import BaseModel, field_validator, ConfigDict, Field
from enum import Enum
from typing import List
from .third_party_clients import vector_store_instance as vector_store
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=20,
    add_start_index=True
)

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

def load_support_tickets(file_path: str) -> List[TicketModel]:
    """
    Carga los tickets de soporte desde un archivo JSON.
    
    Args:
        file_path (str): Ruta al archivo JSON que contiene los tickets.
        
    Returns:
        List[TicketModel]: Lista de objetos TicketModel cargados desde el archivo.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            tickets_data = json.load(file)
            return [TicketModel(**ticket) for ticket in tickets_data]
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en load_support_tickets ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        return []

def ingest_tickets_to_vectorstore(tickets: List[TicketModel]) -> None:
    """
    Ingresa los tickets de soporte al vectorstore para su posterior recuperación.
    
    Args:
        tickets (List[TicketModel]): Lista de objetos TicketModel a ingresar.
    """
    try:
        for ticket in tickets:
            splits = [ticket.description]
            if len(ticket.description) < 5:
                sys.stderr.write(f"\nDEBUG: Ticket {ticket.ticketId} tiene descripción muy corta, se omite.\n")
                sys.stderr.flush()
                continue
            if len(ticket.description) > 200:
                # Si la descripción del ticket es muy larga, se divide en fragmentos
                splits = text_splitter.split_text(ticket.description)
            
            # Generar IDs deterministas basados en el ticketId
            ids = [f"{ticket.ticketId}_{i}" for i in range(len(splits))]
            
            vector_store.add_texts(
                texts=splits,
                metadatas=[ticket.model_dump() for _ in range(len(splits))],
                ids=ids
            )
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en ingest_tickets_to_vectorstore ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()

def run_ingestion_from(file_path: str) -> None:
    """
    Ejecuta el proceso de ingestión de tickets desde un archivo JSON al vectorstore.
    
    Args:
        file_path (str): Ruta al archivo JSON que contiene los tickets.
    """
    try: 
        tickets = load_support_tickets(file_path)
        ingest_tickets_to_vectorstore(tickets)
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en run_ingestion_from ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()

def ingest_individual_ticket(ticket: TicketModel) -> str:
    """
    Ingresa un ticket individual al vectorstore.
    
    Args:
        ticket (TicketModel): Objeto TicketModel a ingresar.
        
    Returns:
        str: Mensaje de éxito o error.
    """
    try:
        splits = [ticket.description]
        if len(ticket.description) < 5:
            return f"ERROR: La descripción del ticket {ticket.ticketId} es demasiado corta."
        if len(ticket.description) > 200:
            # Si la descripción del ticket es muy larga, se divide en fragmentos
            splits = text_splitter.split_text(ticket.description)
            
        # Generar IDs deterministas basados en el ticketId
        ids = [f"{ticket.ticketId}_{i}" for i in range(len(splits))]
        
        vector_store.add_texts(
            texts=splits,
            metadatas=[ticket.model_dump() for _ in range(len(splits))],
            ids=ids
        )
        return f"Ticket {ticket.ticketId} ingresado exitosamente."
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en ingest_individual_ticket ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        return f"ERROR al ingresar el ticket {ticket.ticketId}: {str(e)}"