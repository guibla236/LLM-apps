"""
Módulo para la funcionalidad de resumen de noticias.
Este archivo contiene la estructura mock para que implementes la funcionalidad.
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import List
from .third_party_clients import groq_llm_client, vector_store_instance as vector_store
import sys
import os
import json

CHAT_MODEL_NAME = os.getenv("CHAT_MODEL_NAME")

TICKET_SUMMARIZER_SYSTEM_MESSAGE = """
    You are an assistant that helps to obtain solutions about IT support tickets.
    For that, you have some examples of similar tickets that allow you to solve the input ticket.
    Your duty is to provide in natural language a guide that helps in solving the problem of the input ticket 
    by using the information from the similar tickets that allows the user to solve the input ticket.
    You should delve into the old tickets' description field to compare with the input ticket and evaluate similarities and possible fixes.
    Additionally, you should provide a list of contacts that can help solve the input ticket, for which you have to use the owner fields of the old tickets.
    Your answer must be contained in the following JSON format (under no circumstances can you place text outside the JSON):
    ```json
    {
        "answer": <content of the answer you give to solve the input ticket>,
        "contacts": <array of contacts>
    }
    ```
"""

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

async def retrieve_relevant_tickets(inputTicket: TicketModel) -> List[TicketModel]:
    """
    Obtains a list of similar tickets that can help solve the input ticket.
    
    Args:
        inputTicket (TicketModel): Object with details about the ticket to solve.
        
    Returns:
        List[TicketModel]: List of similar tickets that can help solve the input ticket.
        
    """
    try:
        raw_results = await vector_store.asimilarity_search(inputTicket.description, k=5)
        if raw_results is None or len(raw_results) == 0:
            return []
        
        results = []
        for result in raw_results:
            results.append(TicketModel(**result.metadata))
        return results
        
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR in retrieve_relevant_tickets ==========\n")
        sys.stderr.write(f"DEBUG: Error type: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Error message: {str(e)}\n")
        sys.stderr.flush()
        import traceback
        sys.stderr.write(f"DEBUG: Complete traceback:\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.write("========== DEBUG: ERROR finished ==========\n")
        sys.stderr.flush()
        
        return []


async def augment_similar_tickets(inputTicket: TicketModel) -> dict:
    """
    Using an LLM, return information about similar tickets, contacts, and suggested actions.
    
    Args:
        inputTicket (TicketModel): Object with details about the ticket to solve.
        
    Returns:
        str: A text containing information about similar tickets, contacts, and suggested actions.
    """

    relevant_tickets = await retrieve_relevant_tickets(inputTicket)

    if (len(relevant_tickets) == 0):
        return {
            "answer": "No similar tickets found in the system for the given input ticket.",
            "contacts": []
        }

    if CHAT_MODEL_NAME is None:
        return {
            "answer": "The CHAT_MODEL_NAME env var is not set. The environment variable CHAT_MODEL_NAME is not configured. Nothing can be done.",
            "contacts": []
        }

    message = await groq_llm_client.chat.completions.create(
        model=CHAT_MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": TICKET_SUMMARIZER_SYSTEM_MESSAGE
            },
            {
                "role": "user",
                "content": f"""
                    Input ticket:
                    {inputTicket}
                    
                    Similar tickets:
                    {relevant_tickets}
                """
            }
        ],
        temperature=0
    )

    choice = message.choices[0]
    if choice.message is None or choice.message.content is None:
        return {
            "answer": "The LLM did not return any content.",
            "contacts": []
        }
    summary_text = choice.message.content.split("```json")[1].split("```")[0]

    try:
        # Intentar parsear la respuesta como JSON
        response_data = json.loads(summary_text)
        summary = response_data.get("answer", "")
        if (not summary or len(summary) == 0 ):
            summary = response_data.get("'answer'", "")
        return {
            "answer": summary,
            "contacts": list(set([t.owner for t in relevant_tickets]))
        }
    except json.JSONDecodeError:
        # Fallback si el LLM no devuelve JSON válido
        sys.stderr.write(f"DEBUG: Error on parsing JSON from LLM. Using fallback.\n")
        unique_owners = list(set([t.owner for t in relevant_tickets]))
        return {
            "answer": summary_text,
            "contacts": unique_owners
        }
