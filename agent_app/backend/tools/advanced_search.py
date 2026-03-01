from langchain_core.tools import tool
from core.config import get_env_var
from core.utils import is_tool_enabled
import httpx

API_BASE_URL = get_env_var("API_BASE_URL")
APP_API_KEY = get_env_var("APP_API_KEY")

@tool
async def advanced_search_tool(query: str, search_type: str = "both", search_method: str = "hybrid") -> str:
    """
    Searches the IT knowledge base and tickets database
    Parameters:
    - query: Exact search terms or problem description
    - search_type: 'both' (default), 'tickets_only' (finds specific issues IDs), 'kb_only' (finds how-to guides).
    - search_method: 'hybrid' (vector+keywords), 'vector_only' (conceptual), 'bm25_only' (exact keywords like IDs).
    """
    if not await is_tool_enabled("enable_rag_tool"):
        return "The knowledge base tool is temporarily disabled by the administrator."

    
    if APP_API_KEY is None:
        return "The API key is not configured."

    if not API_BASE_URL:
        return "The API base URL is not configured."
    
    url = f"{API_BASE_URL}/api/raw_unified_search"
    headers = {"X-API-KEY": APP_API_KEY}
    
    payload = {
        "query": query,
        "search_type": search_type,
        "search_method": search_method,
        "k": 5,
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
            result_str += f"[{i+1}] ID: {t.get('id')}\nContent: {t.get('content')}\n\n --- \n"
        return result_str
    except httpx.HTTPStatusError as e:
        return f"HTTP error during search: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error executing search: {str(e)}"