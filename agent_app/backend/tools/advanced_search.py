from typing import Literal
from langchain_core.tools import tool
from core.config import get_env_var
from core.utils import is_tool_enabled
import httpx

API_BASE_URL = get_env_var("API_BASE_URL")
APP_API_KEY = get_env_var("APP_API_KEY")

VALID_SEARCH_TYPES = ("both", "tickets_only", "kb_only")
VALID_SEARCH_METHODS = ("hybrid", "vector_only", "bm25_only")

@tool
async def advanced_search_tool(
    query: str,
    search_type: Literal["both", "tickets_only", "kb_only"] = "both",
    search_method: Literal["hybrid", "vector_only", "bm25_only"] = "hybrid",
    use_hyde: bool = False
) -> str:
    """
    Searches the IT knowledge base and tickets database
    Parameters:
    - query: Exact search terms or problem description
    - search_type: 'both' (default), 'tickets_only' (finds specific issues IDs), 'kb_only' (finds how-to guides).
    - search_method: 'hybrid' (vector+keywords), 'vector_only' (conceptual), 'bm25_only' (exact keywords like IDs).
    - use_hyde: Set to True ONLY if the query is vague, non-technical, or conversational. Set to False if the query contains specific IDs, exact error codes, or techinical jargon.
    """
    if not await is_tool_enabled("enable_rag_tool"):
        return "The knowledge base tool is temporarily disabled by the administrator."

    
    if APP_API_KEY is None:
        return "The API key is not configured."

    if not API_BASE_URL:
        return "The API base URL is not configured."
    
    if search_type not in VALID_SEARCH_TYPES:
        return (
            f"Invalid search_type '{search_type}'. "
            f"Accepted values: {', '.join(VALID_SEARCH_TYPES)}."
        )

    if search_method not in VALID_SEARCH_METHODS:
        return (
            f"Invalid search_method '{search_method}'. "
            f"Accepted values: {', '.join(VALID_SEARCH_METHODS)}."
        )

    url = f"{API_BASE_URL}/api/raw_unified_search"
    headers = {"X-API-KEY": APP_API_KEY}
    
    payload = {
        "query": query,
        "search_type": search_type,
        "search_method": search_method,
        "k": 3,  # Limit to top 3 results for brevity
        "use_hyde": use_hyde
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
        
        results = data.get("results", [])
        if not results:
            return "No matching records found. Try changing the search_method to vector_only or removing technical jargon from the query."
            
        result_str = f"Found {len(results)} similar records:\n\n"
        for i, t in enumerate(results):
            content_snippet = str(t.get("content", ""))[:500]  # Limit content snippet to 500 chars
            result_str += f"[{i+1}] ID: {t.get('id')}\nContent: {content_snippet}\n\n --- \n"
        return result_str
    except httpx.HTTPStatusError as e:
        return (
            f"HTTP error during search (status code {e.response.status_code}). "
            "Please try again later or contact an administrator if the problem persists."
        )
    except Exception as e:
        return f"Error executing search: {str(e)}"