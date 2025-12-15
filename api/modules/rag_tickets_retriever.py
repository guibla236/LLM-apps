"""
Módulo para la funcionalidad de resumen de noticias.
Este archivo contiene la estructura mock para que implementes la funcionalidad.
"""

from pydantic import BaseModel, field_validator, ConfigDict, Field
from enum import Enum
from typing import List
from .third_party_clients import groq_llm_client, vector_store_instance as vector_store
import sys
import os
import json

CHAT_MODEL_NAME = os.getenv("CHAT_MODEL_NAME")

TICKET_SUMMARIZER_SYSTEM_MESSAGE = """
    Eres un asistente que ayuda a obtener información sobre tickets de soporte técnico informático.
    Para eso cuentas con algunos ejemplos de tickets similares que permitan resolver el ticket de entrada.
    Tu deberás proveer en lenguaje natural una descripción que resuma los problemas más similares que han habido en otros tickets.
    Para eso cuentas con una lista de tickets antiguos. Indaga en su campo description para realizar el resumen.
    Además, debes brindar una lista de contactos que pueden ayudar a resolver el ticket de entrada, para lo cual has de usar los campos owner de los tickets antiguos.
    Tu respuesta debe estar contenida en el siguiente formato JSON (bajo ningún concepto podrás colocar texto por fuera del JSON):
    ```json
    {
        "resumen": <contenido del resumen que realizaste>,
        "contactos": <array de contactos>
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

def retrieve_relevant_tickets(inputTicket: TicketModel) -> List[TicketModel]:
    """
    Obtiene una lista de tickets similares que permitan resolver el ticket de entrada.
    
    Args:
        inputTicket (TicketModel): Objeto con los detalles del ticket a resolver.
        
    Returns:
        List[TicketModel]: Lista de los tickets similares al ingresado.
        
    Implementar:
        - Lógica de resumen (ej: con un modelo de IA, algoritmo de extracción, etc.)
        - Extracción de puntos clave
        - Validación de entrada
    """
    try:
        raw_results = vector_store.similarity_search(inputTicket.description, k=5)
        if raw_results is None or len(raw_results) == 0:
            return []
        
        results = []
        for result in raw_results:
            results.append(TicketModel(**result.metadata))
        return results
        
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en retrieve_relevant_tickets ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        import traceback
        sys.stderr.write(f"DEBUG: Traceback completo:\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.write("========== DEBUG: ERROR finalizado ==========\n")
        sys.stderr.flush()
        
        return []


def augment_similar_tickets(inputTicket: TicketModel) -> str:
    """
    Utilizando un LLM, retorna información sobre tickets similares, contactos y acciones sugeridas.
    
    Args:
        inputTicket (TicketModel): Objeto con los detalles del ticket a resolver.
        
    Returns:
        str: Un texto con información sobre tickets similares, contactos y acciones sugeridas.
    """

    relevant_tickets = retrieve_relevant_tickets(inputTicket)

    if (len(relevant_tickets) == 0):
        return {
            "resumen": "No se encontraron tickets similares",
            "contactos": []
        }

    user_message = {
                "role": "user",
                "content": f"""
                    Ticket de entrada:
                    {inputTicket}
                    
                    Tickets similares:
                    {relevant_tickets}
                """
            }

    message = groq_llm_client.chat.completions.create(
        model=CHAT_MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": TICKET_SUMMARIZER_SYSTEM_MESSAGE
            },
            {
                "role": "user",
                "content": f"""
                    Ticket de entrada:
                    {inputTicket}
                    
                    Tickets similares:
                    {relevant_tickets}
                """
            }
        ],
        temperature=0.7
    )

    choice = message.choices[0]
    
    summary_text = choice.message.content.split("```json")[1].split("```")[0]

    try:
        # Intentar parsear la respuesta como JSON
        response_data = json.loads(summary_text)
        resumen = response_data.get("resumen", "")
        if (not resumen or len(resumen) == 0 ):
            resumen = response_data.get("'resumen'", "")
        return {
            "resumen": resumen,
            "contactos": list(set([t.owner for t in relevant_tickets]))
        }
    except json.JSONDecodeError:
        # Fallback si el LLM no devuelve JSON válido
        sys.stderr.write(f"DEBUG: Error al parsear JSON del LLM. Usando fallback.\n")
        unique_owners = list(set([t.owner for t in relevant_tickets]))
        return {
            "resumen": summary_text,
            "contactos": unique_owners
        }
