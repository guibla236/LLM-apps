"""
Unified Retriever Module for Tickets and Knowledge Base.
This module allows searching and combining results from both sources for a more comprehensive RAG experience.
"""

import sys
import os
import json
from typing import List, Optional
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from .third_party_clients import get_chat_client, vector_store_instance as vector_store, kb_vector_store_instance as kb_vector_store
from .rag_tickets_ingestor import TicketModel
from .utils import extract_json_from_llm_response, load_prompt
from models.search import SearchResult, SearchType, SearchMethod

# Environment variables and constants loading
TICKETS_TO_CONSIDER = int(os.getenv("TICKETS_TO_CONSIDER", 5))
KBS_TO_CONSIDER = int(os.getenv("KBS_TO_CONSIDER", 3))

# --- Global BM25 Retrievers ---
_TICKET_BM25_RETRIEVER: Optional[BM25Retriever] = None
_KB_BM25_RETRIEVER: Optional[BM25Retriever] = None

def _init_bm25_retrievers():
    """Initialize BM25 retrievers by loading the pre-computed index."""
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
        
        # Tickets: use enriched page_content_bm25 if available (SE corpus),
        # fall back to legacy "ticketId description" for synthetic tickets.
        ticket_docs = [
            Document(
                page_content=t.get("page_content_bm25", f"{t['ticketId']} {t['description']}"),
                metadata=t
            )
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

async def generate_hypothetical_ticket(query: str, model_name: str) -> str:
    """
    Generates a hypothetical IT support ticket based on a vague user query.
    This function uses a HyDE (Hypothetical Document Embeddings) approach to create a more structured representation of the user's issue, which can improve retrieval performance.
    Args:
        - query (str): The user's query describing the issue in an unstructured way.
        - model_name (str): The name of the model to use for generation.
    Returns:
        - str: A generated ticket description that can be used for retrieval.
    
    """

    # load the template from disk to keep prompts maintainable
    hyde_prompt = PromptTemplate.from_template(load_prompt("hyde_ticket.md"))
    chain = hyde_prompt | get_chat_client(model_name).bind(temperature=0, max_tokens=512)
    response = await chain.ainvoke({"query": query})

    return str(response.content)

async def search_tickets(
        query: str, 
        model_name: str,
        k: int = 5, 
        search_method: SearchMethod = SearchMethod.HYBRID, 
        use_hyde: bool = False, 
        precomputed_hyde_query: Optional[str] = None, 
    ) -> List[SearchResult]:
    """
    Search for relevant tickets based on a query.
    
    Args:
        query (str): Query to search for
        k (int): Maximum number of results
        search_method (SearchMethod): Search strategy; one of SearchMethod.VECTOR_ONLY ("vector_only"),
            SearchMethod.BM25_ONLY ("bm25_only"), or SearchMethod.HYBRID ("hybrid")
        use_hyde (bool): Whether to use hypothetical document generation
        precomputed_hyde_query (Optional[str]): Pre-generated HyDE query to avoid redundant LLM calls
        model_name (str): Model to use for HyDE augmentation if enabled (ignored if precomputed_hyde_query is provided)
        
    Returns:
        List[SearchResult]: List of relevant tickets
    """
    try:
        # 1. Vector search (Semantic)
        raw_vector_results = []
        if search_method in [SearchMethod.HYBRID, SearchMethod.VECTOR_ONLY]:
            vector_query = precomputed_hyde_query if precomputed_hyde_query else query
            # If not precomputed but use_hyde is True, compute it here (fallback)
            if not precomputed_hyde_query and use_hyde:
                vector_query = await generate_hypothetical_ticket(query, model_name)

            raw_vector_results = await vector_store.asimilarity_search(vector_query, k=k)

        # 2. BM25 search (Keywords)
        bm25_results = []
        if search_method in [SearchMethod.HYBRID, SearchMethod.BM25_ONLY]:
            _init_bm25_retrievers()
            if _TICKET_BM25_RETRIEVER:
                # BM25Retriever from LangChain is synchronous
                bm25_results = _TICKET_BM25_RETRIEVER.invoke(query)
        
        # 3. Combine and map to SearchResult
        seen_ids = set()
        results = []
        
        # Prioritize vectorials first for now (we could do RRF later)
        for doc in raw_vector_results:
            if 'ticketId' in doc.metadata:
                tid = doc.metadata['ticketId']
                if tid not in seen_ids:
                    seen_ids.add(tid)
                    results.append(SearchResult(
                        source="ticket", id=tid, title=f"Ticket {tid}",
                        content=doc.page_content, metadata=doc.metadata, score=0.75
                    ))
        
        # Add BM25 results that are not already present
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
        sys.stderr.write(f"\n========== DEBUG: ERROR in search_tickets ==========\n")
        sys.stderr.write(f"DEBUG: Error type: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Error message: {str(e)}\n")
        sys.stderr.flush()
        return []

async def search_kb_documents(query: str, k: int = 5, search_method: SearchMethod = SearchMethod.HYBRID, use_hyde: bool = False) -> List[SearchResult]:
    """
    Search for relevant Knowledge Base documents based on a query.
    
    Args:
        query (str): Query to search for
        k (int): Maximum number of results
        search_method (SearchMethod): Either SearchMethod.VECTOR_ONLY, SearchMethod.BM25_ONLY, or SearchMethod.HYBRID
        use_hyde (bool): Whether to use hypothetical document generation (IGNORE FOR KB)
        
    Returns:
        List[SearchResult]: List of relevant KB documents
    """
    try:
        # 1. Vector search
        raw_vector_results = []
        if search_method in [SearchMethod.HYBRID, SearchMethod.VECTOR_ONLY]:
            # HyDE is disabled for KB search as technical tickets don't match manual styles
            raw_vector_results = await kb_vector_store.asimilarity_search(query, k=k)
        
        # 2. BM25 search
        bm25_results = []
        if search_method in [SearchMethod.HYBRID, SearchMethod.BM25_ONLY]:
            _init_bm25_retrievers()
            if _KB_BM25_RETRIEVER:
                bm25_results = _KB_BM25_RETRIEVER.invoke(query)
        
        # 3. Combine
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
        sys.stderr.write(f"\n========== DEBUG: ERROR in search_kb_documents ==========\n")
        sys.stderr.write(f"DEBUG: Error type: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Error message: {str(e)}\n")
        sys.stderr.flush()
        return []

async def unified_search(
        query: str, 
        model_name: str,
        search_type: SearchType = SearchType.BOTH, 
        k: int = 10, 
        search_method: SearchMethod = SearchMethod.HYBRID, 
        use_hyde: bool = False,
        
    ) -> List[SearchResult]:
    """
    Unified search that combines tickets and KB documents.
    Args:
        query(str): Query to search for
        search_type(SearchType): Type of search to perform
        k(int): Number of results to retrieve
        search_method(SearchMethod): Method to use for search (HYBRID, VECTOR_ONLY, BM25_ONLY)
        use_hyde(bool): Whether to use hypothetical document generation for both ticket and KB vector searches
        model_name: str: Model to use for HyDE augmentation if enabled (only relevant if use_hyde is True and precomputed_hyde_query is not provided)
        
    Returns:
        List[SearchResult]: Combined and ordered results
    """
    try:
        results = []
        
        # Centralized HyDE generation to avoid redundant LLM calls
        hyde_query = None
        if use_hyde:
            hyde_query = await generate_hypothetical_ticket(query, model_name)
        
        if search_type in [SearchType.TICKETS_ONLY, SearchType.BOTH]:
            ticket_results = await search_tickets(
                query, model_name, 
                k, 
                search_method, 
                use_hyde=use_hyde, 
                precomputed_hyde_query=hyde_query
            )
            results.extend(ticket_results)
        
        if search_type in [SearchType.KB_ONLY, SearchType.BOTH]:
            # search_kb_documents ignores use_hyde internal logic
            kb_results = await search_kb_documents(query, k, search_method, use_hyde=use_hyde)
            results.extend(kb_results)

        # NOTE: no re-sort by score here. The per-source retrievers already
        # order results (search_tickets puts vector results first, then BM25
        # complements — see the "we could do RRF later" comment). The scores
        # are fixed placeholders (0.75 vector / 0.8 BM25), so sorting by them
        # would hoist BM25 above vector results and wreck contextual precision.
        return results[:2*k]
        
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en unified_search ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        return []

def _clean_ticket_content(ticket) -> str:
    """Return the ticket content without the leading ticketId prefix.

    BM25 page_content is built as `f"{ticketId} {title_body} ..."` to give
    the ID weight in keyword matching, which duplicates the ID when the
    context renderer already prints `ID: {id}`. Strip it for a clean Q&A.
    """
    content = ticket.content or ""
    tid = ticket.id or ""
    if tid and content.startswith(tid):
        content = content[len(tid):].lstrip()
    return content[:500]


async def context_retriever_for_unified_search(query: str, 
        model_name: str,
        search_type: SearchType = SearchType.BOTH, 
        k: int = 10, 
        search_method: SearchMethod = SearchMethod.HYBRID, 
        use_hyde: bool = False) -> list[str]:
    """
    Context generator that formats retrieval results as Q&A reference material.
    Formats each retrieved ticket as a StackExchange-style Q&A pair for the LLM generator.
    """
    
    unified_search_results = await unified_search(
        query, 
        model_name=model_name,
        search_type=search_type,
        k=k,
        search_method=search_method,
        use_hyde=use_hyde
    )
    unified_search_results = unified_search_results[:k]  # Limit to top k results
    
    ticket_results = [r for r in unified_search_results if r.source == "ticket"]
    kb_results = [r for r in unified_search_results if r.source == "kb"]
    results_to_return = []
    
    for ticket in ticket_results[:TICKETS_TO_CONSIDER]:
        expected = ticket.metadata.get('expected_output', '')
        desc = _clean_ticket_content(ticket)
        results_to_return.append(
            f"[Q&A] ID: {ticket.id}\n"
            f"Question: {desc}\n"
            f"Answer: {expected}\n"
        )
    
    for kb in kb_results[:KBS_TO_CONSIDER]:
        results_to_return.append(
            f"[KB] ID: {kb.id}\n"
            f"Content: {kb.content[:500]}...\n"
        )
    
    return results_to_return

async def augment_search_results_with_tickets_and_kbs(
        query: str, 
        model_name: str, 
        search_type: SearchType = SearchType.BOTH, 
        k: int = 10, 
        hybrid_search: bool = True, 
        use_hyde: bool = False
    ) -> dict:
    """
    Using an LLM, process the search results to generate a summary and suggested actions.
    
    Args:
        query (str): Original query
        search_type (SearchType): Search type to perform
        k (int): Number of results to retrieve and process
        hybrid_search (bool): If True, perform hybrid search (Vector + BM25)
        use_hyde (bool): Whether to use hypothetical ticket generation
        
    Returns:
        dict: Dict containing summary, contacts, references, and suggested actions based on the search results.
    """
    try:
        if TICKETS_TO_CONSIDER <= 0 and KBS_TO_CONSIDER <= 0:
            return {
                "answer": "Both TICKETS_TO_CONSIDER and KBS_TO_CONSIDER env vars are set to 0 or less. No results will be considered for the answer generation.",
                "contacts": []
            }
        search_method = SearchMethod.HYBRID if hybrid_search else SearchMethod.VECTOR_ONLY
        
        # Get search results from both tickets and KB
        search_results = await unified_search(
            query, 
            search_method=search_method, 
            search_type=search_type, 
            k=k, 
            use_hyde=use_hyde, 
            model_name=model_name
        )
        
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
        
        # Build Q&A context
        context = f"Query: {query}\n\n"
        context += "Retrieved Q&A pairs:\n"
        for ticket in ticket_results[:TICKETS_TO_CONSIDER]:
            expected = ticket.metadata.get('expected_output', '')
            desc = _clean_ticket_content(ticket)
            context += f"[Q&A] {ticket.id}\nQ: {desc}\nA: {expected}\n\n"
        
        for kb in kb_results[:KBS_TO_CONSIDER]:
            context += f"[KB] {kb.id}: {kb.content[:500]}...\n"
        
        llm_client = get_chat_client(model_name)
        
        response = await llm_client.ainvoke(
            input=[
                {"role": "system", "content": load_prompt("rag_system_prompt.md")},
                {"role": "user", "content": context}
            ],
            temperature=0
        )
        
        if response and response.content:
            return {"answer": str(response.content).strip()}

        return {"answer": "The system could not generate a response."}
        
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR in augment_search_results_with_tickets_and_kbs ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        
        return {"answer": f"Error processing the results: {str(e)}"}

# Funciones de compatibilidad con el sistema existente
async def retrieve_relevant_tickets(inputTicket: TicketModel, model_name: str) -> List[TicketModel]:
    """
    Compatibility function with the existing system.
    Uses the new unified system but maintains the original interface.
    Args:
        inputTicket(TicketModel): The input ticket for which to find similar tickets
        model_name(str): Model to use for HyDE augmentation if enabled
    Returns:
        List[TicketModel]: List of similar tickets
    """
    try:
        search_results = await search_tickets(inputTicket.description, model_name=model_name, k=5)
        tickets = []
        for result in search_results:
            if result.source == "ticket":
                tickets.append(TicketModel(**result.metadata))
        return tickets
    except Exception:
        return []

async def augment_similar_tickets(inputTicket: TicketModel, model_name: str) -> dict:
    """
    Compatibility function with the existing system.
    Uses the new unified system but maintains the original interface.
    """
    try:
        result = await augment_search_results_with_tickets_and_kbs(
            inputTicket.description, 
            model_name, 
            SearchType.TICKETS_ONLY,
            k=5
        )
        return {
            "summary": result.get("summary", ""),
            "contacts": result.get("contacts", [])
        }
    except Exception:
        return {
            "summary": "Error processing the ticket",
            "contacts": []
        }