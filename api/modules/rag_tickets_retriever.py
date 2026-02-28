"""
DEPRECATED: This module is deprecated and will be removed in future versions.
Please use `rag_unified_retriever.py` instead, which provides the same interface 
but leverages the unified hybrid search system.

Module for the support tickets summary functionality.
This file contains the mock structure for you to implement the functionality.
"""

import warnings

warnings.warn(
    "The rag_tickets_retriever module is deprecated. Please use rag_unified_retriever instead.",
    DeprecationWarning,
    stacklevel=2
)

from typing import List
from .third_party_clients import groq_llm_client, vector_store_instance as vector_store
from .utils import extract_json_from_llm_response
from models.tickets import TicketModel
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

    response = await groq_llm_client.ainvoke(
        input=[
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

    chat_response = response.content

    if not chat_response:
        return {
            "answer": "LLM did not return a valid response",
            "contacts": list(set([t.owner for t in relevant_tickets]))
        }

    clean_content = extract_json_from_llm_response(str(chat_response))
    parsed_json = None
    try:
        parsed_json = json.loads(clean_content)
    except Exception:
        parsed_json = None

    owners = list(set([t.owner for t in relevant_tickets]))

    if isinstance(parsed_json, dict):
        return {
            "answer": parsed_json.get("answer", ""),
            "contacts": parsed_json.get("contacts", owners)
        }

    # Fallback if JSON parsing fails
    return {
        "answer": str(chat_response),
        "contacts": owners
    }
