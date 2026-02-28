"""
Unified Retriever Module for Tickets and Knowledge Base.
This module allows searching and combining results from both sources for a more comprehensive RAG experience.
"""

import sys
import os
import json
from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Dict, Any, Optional
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from .third_party_clients import groq_llm_client, vector_store_instance as vector_store, kb_vector_store_instance as kb_vector_store
from .rag_tickets_ingestor import TicketModel
from .utils import extract_json_from_llm_response

CHAT_MODEL_NAME = os.getenv("CHAT_MODEL_NAME")
TICKETS_TO_CONSIDER = int(os.getenv("TICKETS_TO_CONSIDER", 5))
KBS_TO_CONSIDER = int(os.getenv("KBS_TO_CONSIDER", 3))

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

# --- Global BM25 Retrievers ---
_TICKET_BM25_RETRIEVER: Optional[BM25Retriever] = None
_KB_BM25_RETRIEVER: Optional[BM25Retriever] = None

def _init_bm25_retrievers():
    """Inicializa los retrievers BM25 cargando el índice pre-computado."""
    global _TICKET_BM25_RETRIEVER, _KB_BM25_RETRIEVER
    
    if _TICKET_BM25_RETRIEVER is not None:
        return

    index_path = os.path.join(os.path.dirname(__file__), "..", "static", "bm25_index.json")
    if not os.path.exists(index_path):
        sys.stderr.write(f"DEBUG: BM25 index not found at {index_path}\n")
        return

    try:
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Tickets
        ticket_docs = [
            Document(page_content=f"{t['ticketId']} {t['description']}", metadata=t)
            for t in data.get("tickets", [])
        ]
        if ticket_docs:
            _TICKET_BM25_RETRIEVER = BM25Retriever.from_documents(ticket_docs)
        
        # KB
        kb_docs = [
            Document(page_content=d["content"], metadata=d)
            for d in data.get("kb", [])
        ]
        if kb_docs:
            _KB_BM25_RETRIEVER = BM25Retriever.from_documents(kb_docs)

        sys.stderr.write(f"DEBUG: BM25 Retrievers initialized successfully.\n")
    except Exception as e:
        sys.stderr.write(f"DEBUG: Error initializing BM25: {str(e)}\n")

async def search_tickets(query: str, k: int = 5, hybrid_search: bool = True) -> List[SearchResult]:
    """
    Busca tickets relevantes basados en una consulta.
    
    Args:
        query (str): Consulta de búsqueda
        k (int): Número máximo de resultados
        hybrid_search (bool): Si es True, realiza búsqueda híbrida (Vector + BM25)
        
    Returns:
        List[SearchResult]: Lista de tickets relevantes
    """
    try:
        # 1. Búsqueda Vectorial (Semántica)
        raw_vector_results = await vector_store.asimilarity_search(query, k=k)
        
        # 2. Búsqueda BM25 (Palabras Clave)
        bm25_results = []
        if hybrid_search:
            _init_bm25_retrievers()
            if _TICKET_BM25_RETRIEVER:
                # BM25Retriever de LangChain es síncrono
                bm25_results = _TICKET_BM25_RETRIEVER.invoke(query)
        
        # 3. Combinar y mapear a SearchResult
        seen_ids = set()
        results = []
        
        # Priorizar vectoriales primero por ahora (podríamos hacer RRF más adelante)
        for doc in raw_vector_results:
            if 'ticketId' in doc.metadata:
                tid = doc.metadata['ticketId']
                if tid not in seen_ids:
                    seen_ids.add(tid)
                    results.append(SearchResult(
                        source="ticket", id=tid, title=f"Ticket {tid}",
                        content=doc.page_content, metadata=doc.metadata, score=0.75
                    ))
        
        # Agregar resultados de BM25 que no estén ya
        for doc in bm25_results[:k]:
            tid = doc.metadata['ticketId']
            if tid not in seen_ids:
                seen_ids.add(tid)
                results.append(SearchResult(
                    source="ticket", id=tid, title=f"Ticket {tid}",
                    content=doc.page_content, metadata=doc.metadata, score=0.8
                ))
        
        return results
        
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en search_tickets ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        return []

async def search_kb_documents(query: str, k: int = 5, hybrid_search: bool = True) -> List[SearchResult]:
    """
    Busca documentos Knowledge Base relevantes basados en una consulta.
    
    Args:
        query (str): Consulta de búsqueda
        k (int): Número máximo de resultados
        hybrid_search (bool): Si es True, realiza búsqueda híbrida (Vector + BM25)
        
    Returns:
        List[SearchResult]: Lista de documentos KB relevantes
    """
    try:
        # 1. Búsqueda Vectorial
        raw_vector_results = await kb_vector_store.asimilarity_search(query, k=k)
        
        # 2. Búsqueda BM25
        bm25_results = []
        if hybrid_search:
            _init_bm25_retrievers()
            if _KB_BM25_RETRIEVER:
                bm25_results = _KB_BM25_RETRIEVER.invoke(query)
        
        # 3. Combinar
        seen_ids = set()
        results = []
        
        for doc in raw_vector_results:
            if 'fileId' in doc.metadata:
                fid = doc.metadata['fileId']
                if fid not in seen_ids:
                    seen_ids.add(fid)
                    results.append(SearchResult(
                        source="kb", id=fid, title=f"KB {fid}",
                        content=doc.page_content, metadata=doc.metadata, score=0.75
                    ))
        
        for doc in bm25_results[:k]:
            fid = doc.metadata['fileId']
            if fid not in seen_ids:
                seen_ids.add(fid)
                results.append(SearchResult(
                    source="kb", id=fid, title=f"KB {fid}",
                    content=doc.page_content, metadata=doc.metadata, score=0.8
                ))
        
        return results
        
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en search_kb_documents ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        return []

async def unified_search(query: str, search_type: SearchType = SearchType.BOTH, k: int = 10, hybrid_search: bool = True) -> List[SearchResult]:
    """
    Búsqueda unificada que combina tickets y documentos KB.
    
    Args:
        query (str): Consulta de búsqueda
        search_type (SearchType): Tipo de búsqueda a realizar
        k (int): Número total de resultados
        hybrid_search (bool): Si es True, realiza búsqueda híbrida (Vector + BM25)
        
    Returns:
        List[SearchResult]: Resultados combinados y ordenados
    """
    try:
        results = []
        
        if search_type in [SearchType.TICKETS_ONLY, SearchType.BOTH]:
            ticket_results = await search_tickets(query, k, hybrid_search)
            results.extend(ticket_results)
        
        if search_type in [SearchType.KB_ONLY, SearchType.BOTH]:
            kb_results = await search_kb_documents(query, k, hybrid_search)
            results.extend(kb_results)
        
        # Ordenar por score (placeholder) y limitar resultados
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:2*k]
        
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en unified_search ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        return []

async def augment_search_results_with_tickets_and_kbs(query: str, search_type: SearchType = SearchType.BOTH, k: int = 10, hybrid_search: bool = True) -> dict:
    """
    Using an LLM, process the search results to generate a summary and suggested actions.
    
    Args:
        query (str): Original query
        search_type (SearchType): Search type to perform
        k (int): Number of results to retrieve and process
        hybrid_search (bool): Si es True, realiza búsqueda híbrida (Vector + BM25)
        
    Returns:
        dict: Dict containing summary, contacts, references, and suggested actions based on the search results.
    """
    try:

        if CHAT_MODEL_NAME is None:
            return {
                "answer": "The CHAT_MODEL_NAME env var is not set. The environment variable CHAT_MODEL_NAME is not configured. Nothing can be done.",
                "contacts": []
            }
        if TICKETS_TO_CONSIDER <= 0 and KBS_TO_CONSIDER <= 0:
            return {
                "answer": "Both TICKETS_TO_CONSIDER and KBS_TO_CONSIDER env vars are set to 0 or less. No results will be considered for the answer generation.",
                "contacts": []
            }
        
        # Get search results from both tickets and KB
        search_results = await unified_search(query, search_type, k, hybrid_search)
        
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
            context += f"""
                Id: {ticket.id} \n
                Description: {ticket.content[:200]}... \n
                Actions taken: {ticket.metadata.get('actions', 'No actions recorded')} \n
                Owner: {ticket.metadata.get('owner', 'Unknown')}\n
                """
        
        context += "\n Knowledge Base relevant documents:\n"
        for kb in kb_results[:KBS_TO_CONSIDER]:
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

        response = await groq_llm_client.ainvoke(
            input=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": context}
            ],
            temperature=0
        )
        
        if response and response.content:
            # Clean the LLM response from markdown and extract the JSON block
            clean_content = extract_json_from_llm_response(str(response.content))

            # El extractor devuelve siempre str: intentar parsear JSON
            parsed_json = None
            try:
                parsed_json = json.loads(clean_content)
            except Exception:
                parsed_json = None

            if isinstance(parsed_json, dict):
                return {
                    "summary": parsed_json.get("summary", ""),
                    "contacts": parsed_json.get("contacts", []),
                    "kb_references": [k.id for k in kb_results[:KBS_TO_CONSIDER]],
                    "ticket_references": [r.id for r in ticket_results[:TICKETS_TO_CONSIDER]],
                    "suggested_actions": parsed_json.get("suggested_actions", [])
                }

            # Fallback si no se pudo parsear el JSON
            return {
                "summary": str(response.content),
                "contacts": ticket_owners,
                "kb_references": [k.id for k in kb_results[:KBS_TO_CONSIDER]],
                "ticket_references": [r.id for r in ticket_results[:TICKETS_TO_CONSIDER]],
                "suggested_actions": ["Review the KB documents and tickets mentioned to get more details"]
            }

        # Si la LLM no devolvió respuesta válida (response es falsy), devolver fallback explícito
        return {
            "summary": "Something went wrong: LLM did not return a valid response",
            "contacts": ticket_owners,
            "kb_references": [k.id for k in kb_results[:KBS_TO_CONSIDER]],
            "ticket_references": [r.id for r in ticket_results[:TICKETS_TO_CONSIDER]],
            "suggested_actions": ["Something went wrong"]
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