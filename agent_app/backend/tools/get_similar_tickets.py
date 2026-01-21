
from langchain_core.tools import tool
from datetime import datetime
from utils import is_tool_enabled
import httpx

@tool
async def get_similar_tickets_tool(description: str) -> str:
    """
    Useful to find similar support tickets in the database. 
    Input should be a detailed description of the problem.
    Returns a string representation of similar tickets found.
    """
    if not await is_tool_enabled("enable_rag_tool"):
        return "El acceso a la base de datos de tickets similares está temporalmente desactivado por el administrador."

    url = f"{API_BASE_URL}/api/get_similar_tickets"
    headers = {"X-API-KEY": APP_API_KEY}
    
    payload = {
        "ticketId": "SEARCH-QUERY",
        "creationDate": datetime.utcnow().strftime("%Y-%m-%d"),
        "priority": "Medium",
        "owner": "Agent",
        "description": description,
        "impact": "Unknown",
        "actions": "None"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            tickets = response.json()
        
        if not tickets:
            return "No similar tickets found."
            
        result_str = "Found similar tickets:\n"
        for i, t in enumerate(tickets):
            result_str += f"{i+1}. ID: {t.get('ticketId')} - Description: {t.get('description')} - Actions: {t.get('actions')}\n"
        return result_str
        
    except Exception as e:
        return f"Error querying similar tickets: {str(e)}"