"""
Módulo unificado para recuperación de información desde tickets y Knowledge Base.
Este módulo permite buscar y combinar resultados de ambas fuentes para un RAG más completo.
"""

import sys
import json
from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from .third_party_clients import groq_llm_client, vector_store_instance as vector_store
from .rag_tickets_ingestor import TicketModel, TicketPriority
from .rag_kb_ingestor import KBDocument

CHAT_MODEL_NAME = "llama3-8b-8192"  # Modelo por defecto

class SearchType(str, Enum):
    """Tipos de búsqueda disponibles."""
    TICKETS_ONLY = "tickets_only"
    KB_ONLY = "kb_only"
    BOTH = "both"

class SearchResult(BaseModel):
    """Modelo para resultados de búsqueda unificados."""
    source: str = Field(..., description="Fuente del resultado (ticket o kb)")
    id: str = Field(..., description="ID del documento/ticket")
    title: str = Field(..., description="Título o nombre del documento")
    content: str = Field(..., description="Contenido relevante")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales")
    score: float = Field(..., description="Puntuación de relevancia")

async def search_tickets(query: str, k: int = 5) -> List[SearchResult]:
    """
    Busca tickets relevantes basados en una consulta.
    
    Args:
        query (str): Consulta de búsqueda
        k (int): Número máximo de resultados
        
    Returns:
        List[SearchResult]: Lista de tickets relevantes
    """
    try:
        raw_results = await vector_store.asimilarity_search(query, k=k)
        if not raw_results:
            return []
        
        results = []
        for result in raw_results:
            # Verificar si el resultado es un ticket
            if 'ticketId' in result.metadata:
                ticket = TicketModel(**result.metadata)
                search_result = SearchResult(
                    source="ticket",
                    id=ticket.ticketId,
                    title=f"Ticket {ticket.ticketId}",
                    content=ticket.description,
                    metadata=ticket.model_dump(),
                    score=0.8  # Placeholder para score real
                )
                results.append(search_result)
        
        return results
        
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en search_tickets ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        return []

async def search_kb_documents(query: str, k: int = 5) -> List[SearchResult]:
    """
    Busca documentos Knowledge Base relevantes basados en una consulta.
    
    Args:
        query (str): Consulta de búsqueda
        k (int): Número máximo de resultados
        
    Returns:
        List[SearchResult]: Lista de documentos KB relevantes
    """
    try:
        raw_results = await vector_store.asimilarity_search(query, k=k)
        if not raw_results:
            return []
        
        results = []
        for result in raw_results:
            # Verificar si el resultado es un documento KB
            if 'fileId' in result.metadata:
                metadata = result.metadata
                search_result = SearchResult(
                    source="kb",
                    id=metadata['fileId'],
                    title=f"KB {metadata['fileId']}",
                    content=result.page_content,
                    metadata=metadata,
                    score=0.8  # Placeholder para score real
                )
                results.append(search_result)
        
        return results
        
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en search_kb_documents ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        return []

async def unified_search(query: str, search_type: SearchType = SearchType.BOTH, k: int = 10) -> List[SearchResult]:
    """
    Búsqueda unificada que combina tickets y documentos KB.
    
    Args:
        query (str): Consulta de búsqueda
        search_type (SearchType): Tipo de búsqueda a realizar
        k (int): Número total de resultados
        
    Returns:
        List[SearchResult]: Resultados combinados y ordenados
    """
    try:
        results = []
        
        if search_type in [SearchType.TICKETS_ONLY, SearchType.BOTH]:
            ticket_results = await search_tickets(query, k)
            results.extend(ticket_results)
        
        if search_type in [SearchType.KB_ONLY, SearchType.BOTH]:
            kb_results = await search_kb_documents(query, k)
            results.extend(kb_results)
        
        # Ordenar por score (placeholder) y limitar resultados
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:k]
        
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en unified_search ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        return []

async def augment_search_results(query: str, search_type: SearchType = SearchType.BOTH, k: int = 10) -> dict:
    """
    Utilizando un LLM, procesa los resultados de búsqueda para generar un resumen y acciones sugeridas.
    
    Args:
        query (str): Consulta original
        search_type (SearchType): Tipo de búsqueda
        k (int): Número de resultados a considerar
        
    Returns:
        dict: Diccionario con resumen y acciones sugeridas
    """
    try:
        # Obtener resultados de búsqueda
        search_results = await unified_search(query, search_type, k)
        
        if not search_results:
            return {
                "resumen": "No se encontraron resultados relevantes",
                "contactos": [],
                "kb_references": [],
                "ticket_references": []
            }
        
        # Separar resultados por tipo
        ticket_results = [r for r in search_results if r.source == "ticket"]
        kb_results = [r for r in search_results if r.source == "kb"]
        
        # Extraer información relevante
        ticket_owners = list(set([r.metadata.get('owner', '') for r in ticket_results if r.metadata.get('owner')]))
        kb_ids = list(set([r.id for r in kb_results]))
        
        # Preparar contexto para el LLM
        context = f"Consulta: {query}\n\n"
        context += "Tickets similares encontrados:\n"
        for ticket in ticket_results[:3]:  # Limitar a 3 tickets para no exceder token limit
            context += f"- {ticket.id}: {ticket.content[:200]}...\n"
        
        context += "\nDocumentos Knowledge Base relevantes:\n"
        for kb in kb_results[:3]:  # Limitar a 3 documentos KB
            context += f"- {kb.id}: {kb.content[:200]}...\n"
        
        # Mensaje para el LLM
        system_message = """
Eres un asistente experto en soporte técnico informático. Basado en los tickets y documentos de conocimiento proporcionados, genera un resumen útil y acciones sugeridas.

Tu respuesta debe ser en formato JSON con la siguiente estructura:
{
    "resumen": "Resumen conciso de la información relevante encontrada",
    "contactos": ["Lista de contactos relevantes de los tickets"],
    "kb_references": ["IDs de documentos KB mencionados"],
    "ticket_references": ["IDs de tickets mencionados"],
    "acciones_sugeridas": ["Lista de acciones sugeridas basadas en la información"]
}
"""

        try:
            message = await groq_llm_client.chat.completions.create(
                model=CHAT_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": context}
                ],
                temperature=0.7
            )
            
            if message.choices[0].message and message.choices[0].message.content:
                content = message.choices[0].message.content
                
                # Extraer JSON del contenido
                if "```json" in content:
                    json_part = content.split("```json")[1].split("```")[0]
                else:
                    json_part = content
                
                response_data = json.loads(json_part)
                return {
                    "resumen": response_data.get("resumen", ""),
                    "contactos": response_data.get("contactos", []),
                    "kb_references": response_data.get("kb_references", []),
                    "ticket_references": response_data.get("ticket_references", []),
                    "acciones_sugeridas": response_data.get("acciones_sugeridas", [])
                }
            
        except json.JSONDecodeError:
            # Fallback si el LLM no devuelve JSON válido
            return {
                "resumen": f"Se encontraron {len(search_results)} resultados relevantes. Consulta los tickets y documentos KB para más detalles.",
                "contactos": ticket_owners,
                "kb_references": kb_ids,
                "ticket_references": [r.id for r in ticket_results],
                "acciones_sugeridas": ["Revisar los documentos KB y tickets mencionados para obtener más detalles"]
            }
        
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en augment_search_results ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        
        return {
            "resumen": f"Error al procesar los resultados: {str(e)}",
            "contactos": [],
            "kb_references": [],
            "ticket_references": [],
            "acciones_sugeridas": []
        }

# Funciones de compatibilidad con el sistema existente
async def retrieve_relevant_tickets(inputTicket: TicketModel) -> List[TicketModel]:
    """
    Función de compatibilidad con el sistema existente.
    Obtiene tickets similares usando el nuevo sistema unificado.
    """
    try:
        search_results = await search_tickets(inputTicket.description, k=5)
        tickets = []
        for result in search_results:
            if result.source == "ticket":
                tickets.append(TicketModel(**result.metadata))
        return tickets
    except Exception:
        return []

async def augment_similar_tickets(inputTicket: TicketModel) -> dict:
    """
    Función de compatibilidad con el sistema existente.
    Utiliza el nuevo sistema unificado pero mantiene la interfaz original.
    """
    try:
        result = await augment_search_results(inputTicket.description, SearchType.TICKETS_ONLY, k=5)
        return {
            "resumen": result.get("resumen", ""),
            "contactos": result.get("contactos", [])
        }
    except Exception:
        return {
            "resumen": "Error al procesar el ticket",
            "contactos": []
        }