"""
Unified Retriever Module for Tickets and Knowledge Base.
This module allows searching and combining results from both sources for a more comprehensive RAG experience.
"""

import sys
import os
import json
from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from .third_party_clients import groq_llm_client, vector_store_instance as vector_store
from .rag_tickets_ingestor import TicketModel, TicketPriority
from .rag_kb_ingestor import KBDocument

CHAT_MODEL_NAME = os.getenv("CHAT_MODEL_NAME")

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

async def augment_search_results_with_tickets_and_kbs(query: str, search_type: SearchType = SearchType.BOTH, k: int = 10) -> dict:
    """
    Using an LLM, process the search results to generate a summary and suggested actions.
    
    Args:
        query (str): Original query
        search_type (SearchType): Search type to perform
        k (int): Number of results to retrieve and process
        
    Returns:
        dict: Dict containing summary, contacts, references, and suggested actions based on the search results.
    """
    try:

        if CHAT_MODEL_NAME is None:
            return {
                "answer": "The CHAT_MODEL_NAME env var is not set. The environment variable CHAT_MODEL_NAME is not configured. Nothing can be done.",
                "contacts": []
            }
        search_results = await unified_search(query, search_type, k)
        
        if not search_results:
            return {
                "summary": "No relevant tickets or KB documents found for the given query.",
                "contacts": [],
                "kb_references": [],
                "ticket_references": []
            }
        
        # Split results by type for better processing
        ticket_results = [r for r in search_results if r.source == "ticket"]
        kb_results = [r for r in search_results if r.source == "kb"]
        
        # Extract relevant information
        ticket_owners = list(set([r.metadata.get('owner', '') for r in ticket_results if r.metadata.get('owner')]))
        
        # Prepare LLM context
        context = f"Query: {query}\n\n"
        context += "Similar tickets found:\n"
        for ticket in ticket_results[:TICKETS_TO_CONSIDER]:  # Limit to 3 tickets to avoid exceeding token limit
        
        context += "\nDocumentos Knowledge Base relevantes:\n"
        for kb in kb_results[:3]:  # Limitar a 3 documentos KB
            context += f"- {kb.id}: {kb.content[:200]}...\n"
        
        # System prompt
        system_message = """
            You are an expert assistant in IT technical support. Based on the provided tickets and knowledge base documents, generate a useful summary and suggested actions.
            Your response must be in JSON format with the following structure:
            {
                "summary": "Concise summary of the relevant information found",
                "contacts": ["List of relevant contacts from the tickets' owners"],
                "suggested_actions": ["List of suggested actions based on the information"]
            }
        """

        try:
            message = await groq_llm_client.chat.completions.create(
                model=CHAT_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": context}
                ],
                temperature=0
            )
            
            if message.choices[0].message and message.choices[0].message.content:
                content = message.choices[0].message.content
                
                # Extract JSON from content
                if "```json" in content:
                    json_part = content.split("```json")[1].split("```")[0]
                else:
                    json_part = content
                
                response_data = json.loads(json_part)
                return {
                    "summary": response_data.get("summary", ""),
                    "contacts": response_data.get("contacts", []),
                    "kb_references": [k.id for k in kb_results[:KBS_TO_CONSIDER]],
                    "ticket_references": [r.id for r in ticket_results[:TICKETS_TO_CONSIDER]],
                    "suggested_actions": response_data.get("suggested_actions", [])
                }
            
        except json.JSONDecodeError:
            # Fallback if LLM does not return valid JSON
            return {
                "summary": f"Found {len(search_results)} relevant results. Check the tickets and KB documents for more details.",
                "contacts": ticket_owners,
                "kb_references": [k.id for k in kb_results[:KBS_TO_CONSIDER]],
                "ticket_references": [r.id for r in ticket_results[:TICKETS_TO_CONSIDER]],
                "suggested_actions": ["Review the KB documents and tickets mentioned to get more details"]
            }
        
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR in augment_search_results_with_tickets_and_kbs ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        
        return {
            "summary": f"Error processing the results: {str(e)}",
            "contacts": [],
            "kb_references": [],
            "ticket_references": [],
            "suggested_actions": []
        }

# Funciones de compatibilidad con el sistema existente
async def retrieve_relevant_tickets(inputTicket: TicketModel) -> List[TicketModel]:
    """
    Compatibility function with the existing system.
    Uses the new unified system but maintains the original interface.
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
    Compatibility function with the existing system.
    Uses the new unified system but maintains the original interface.
    """
    try:
        result = await augment_search_results_with_tickets_and_kbs(inputTicket.description, SearchType.TICKETS_ONLY, k=5)
        return {
            "summary": result.get("summary", ""),
            "contacts": result.get("contacts", [])
        }
    except Exception:
        return {
            "summary": "Error processing the ticket",
            "contacts": []
        }