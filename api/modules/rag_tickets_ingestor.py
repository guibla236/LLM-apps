"""
Module for the tickets ingestor functionality.
This module defines the TicketModel and functions to load tickets from a JSON file and ingest them into a vectorstore for later retrieval.
"""

import sys
import json
from pydantic import BaseModel, Field
from enum import Enum
from typing import List
from .third_party_clients import vector_store_instance as vector_store
from .unified_logger import log_execution, log_error
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
    description: str = Field(..., min_length=10, max_length=5000, description="Descripción detallada del problema")
    impact: str = Field(..., max_length=500, description="Impacto del problema en la productividad")
    actions: str = Field(..., max_length=1000, description="Acciones tomadas por el solicitante antes de reportar")

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

    Ingest support tickets to the vectorstore for later retrieval.
    
    Args:
        tickets (List[TicketModel]): TicketModel objects to ingest.
    """
    try:
        for i, ticket in enumerate(tickets):
            print(f"\nDEBUG: Processing ticket {i+1}/{len(tickets)}: {ticket.ticketId}\n")
            # Log: start ingestion for this ticket
            try:
                log_execution(ticket_id=f"TICKET-INGEST-{ticket.ticketId}", user=ticket.owner, input_data={"ticketId": ticket.ticketId}, solution="started", execution_time=0)
            except Exception:
                pass
            splits = [ticket.description]
            if len(ticket.description) < 5:
                sys.stderr.write(f"\nDEBUG: Ticket {ticket.ticketId} has a very short description, so it is omitted.\n")
                sys.stderr.flush()
                continue
            if len(ticket.description) > 200:
                # If the ticket description is very long, it is splitted into different chunks.
                splits = text_splitter.split_text(ticket.description)
            
            # Generate deterministic IDs based on the ticketId and chunk index to ensure consistent retrieval later
            ids = [f"{ticket.ticketId}_{i}" for i in range(len(splits))]
            
            vector_store.add_texts(
                texts=splits,
                metadatas=[ticket.model_dump() for _ in range(len(splits))],
                ids=ids
            )
            print(f"DEBUG: Ticket {ticket.ticketId} ingested successfully.\n")
            try:
                log_execution(ticket_id=f"TICKET-INGEST-{ticket.ticketId}", user=ticket.owner, input_data={"ticketId": ticket.ticketId}, solution="success", execution_time=0)
            except Exception:
                pass
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR in ingest_tickets_to_vectorstore ==========\n")
        sys.stderr.write(f"DEBUG: Error type: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Error message: {str(e)}\n")
        sys.stderr.flush()
        try:
            log_error(user="system", path="ingest_tickets_to_vectorstore", method="ingest", error_message=str(e), traceback_data="see stderr")
        except Exception:
            pass

def run_ingestion_from(file_path: str) -> None:
    """
    Executes the process of ingesting tickets from a JSON file to the vectorstore.
    
    Args:
        file_path (str): Path to the JSON file containing the tickets to be ingested.
    """
    print(f"\n========== DEBUG: Starting massive ingestion ==========\n")
    print(f"DEBUG: File received: {file_path}")
    try: 
        tickets = load_support_tickets(file_path)
        print(f"\nDEBUG: {len(tickets)} tickets loaded.\n")
        ingest_tickets_to_vectorstore(tickets)
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR in run_ingestion_from ==========\n")
        sys.stderr.write(f"DEBUG: Error type: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Error message: {str(e)}\n")
        sys.stderr.flush()

def ingest_individual_ticket(ticket: TicketModel) -> str:
    """
    Ingests an individual ticket into the vectorstore.
    
    Args:
        ticket (TicketModel): TicketModel object to ingest.
        
    Returns:
        str: Message indicating the result of the ingestion process.
    """
    try:
        splits = [ticket.description]
        if len(ticket.description) < 5:
            return f"ERROR: The ticket description for ticket {ticket.ticketId} is too short."
        if len(ticket.description) > 200:
            # If the ticket description is very long, it is splitted into different chunks.
            splits = text_splitter.split_text(ticket.description)
            
        # Generate deterministic IDs based on the ticketId and chunk index to ensure consistent retrieval later
        ids = [f"{ticket.ticketId}_{i}" for i in range(len(splits))]
        
        vector_store.add_texts(
            texts=splits,
            metadatas=[ticket.model_dump() for _ in range(len(splits))],
            ids=ids
        )
        return f"Ticket {ticket.ticketId} ingested successfully."
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR in ingest_individual_ticket ==========\n")
        sys.stderr.write(f"DEBUG: Error type: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Error message: {str(e)}\n")
        sys.stderr.flush()
        return f"ERROR ingesting ticket {ticket.ticketId}: {str(e)}"