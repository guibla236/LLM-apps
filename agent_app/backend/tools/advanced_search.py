from typing import Literal
from langchain_core.tools import tool
from core.config import get_env_var
from core.utils import is_tool_enabled
import httpx

_API_BASE_URL = get_env_var("API_BASE_URL")
_APP_API_KEY = get_env_var("APP_API_KEY")

_VALID_SEARCH_TYPES = ("both", "tickets_only", "kb_only")
_VALID_SEARCH_METHODS = ("hybrid", "vector_only", "bm25_only")

DEFAULT_SEARCH_K = 3


def _search_k() -> int:
    """Top-k for the RAG call.

    Defaults to 3 for production brevity. Set AGENT_SEARCH_K=10 to match the
    M4/M6 evaluation protocol when benchmarking the agent against the RAG.
    """
    raw = get_env_var("AGENT_SEARCH_K")
    try:
        value = int(raw) if raw is not None else DEFAULT_SEARCH_K
    except (TypeError, ValueError):
        return DEFAULT_SEARCH_K
    return value if value > 0 else DEFAULT_SEARCH_K

@tool
async def advanced_search_tool(
    query: str,
    search_type: Literal["both", "tickets_only", "kb_only"] = "both",
    search_method: Literal["hybrid", "vector_only", "bm25_only"] = "hybrid",
    use_hyde: bool = False
) -> str:
    """
    Searches the IT knowledge base and tickets database.

    Parameters:
    - query: Exact search terms or problem description
    - search_type: 'both' (default), 'tickets_only' (finds specific issues IDs), 'kb_only' (finds how-to guides).
    - search_method: 'hybrid' (vector+keywords), 'vector_only' (conceptual), 'bm25_only' (exact keywords like IDs).
    - use_hyde: Set to True ONLY if the query is vague, non-technical, or conversational. Set to False if the query contains specific IDs, exact error codes, or technical jargon.
    """
    if not await is_tool_enabled("enable_rag_tool"):
        return "The knowledge base tool is temporarily disabled by the administrator."

    
    if _APP_API_KEY is None:
        return "The API key is not configured."

    if not _API_BASE_URL:
        return "The API base URL is not configured."
    
    model_name = get_env_var("AGENT_MODEL")
    if model_name is None:
        return "The AGENT_MODEL env var is not set. The environment variable AGENT_MODEL is not configured. Nothing can be done."
    
    if search_type not in _VALID_SEARCH_TYPES:
        return (
            f"Invalid search_type '{search_type}'. "
            f"Accepted values: {', '.join(_VALID_SEARCH_TYPES)}."
        )

    if search_method not in _VALID_SEARCH_METHODS:
        return (
            f"Invalid search_method '{search_method}'. "
            f"Accepted values: {', '.join(_VALID_SEARCH_METHODS)}."
        )

    url = f"{_API_BASE_URL}/api/raw_unified_search"
    headers = {"X-API-KEY": _APP_API_KEY}
    
    payload = {
        "query": query,
        "search_type": search_type,
        "search_method": search_method,
        "k": _search_k(),
        "use_hyde": use_hyde,
        "model_name": model_name
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
        
        # /api/raw_unified_search returns a plain list of rendered context
        # strings. Accept the legacy {"results": [...]} envelope too, so the
        # tool keeps working if the endpoint shape changes back.
        if isinstance(data, dict):
            results = data.get("results", [])
        elif isinstance(data, list):
            results = data
        else:
            return f"Unexpected search response format: {type(data).__name__}"

        if not results:
            return "No matching records found. Try changing the search_method to vector_only or removing technical jargon from the query."

        if all(isinstance(r, str) for r in results):
            result_str = f"Found {len(results)} similar records:\n\n" + "\n\n --- \n".join(
                r[:2000] for r in results
            )
            return result_str

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