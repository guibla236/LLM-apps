import httpx
from core.config import get_env_var

API_BASE_URL = get_env_var("API_BASE_URL")

async def is_tool_enabled(flag_name: str) -> bool:
    """Helper to check if a specific tool is enabled via feature flags API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/api/flags/{flag_name}", timeout=5.0)
            if response.status_code == 200:
                return response.json().get("enabled", True)
    except Exception:
        pass
    return False # Default to disabled if API fails

def get_system_prompt() -> str:
    """Helper to read markdown file with the system prompt."""
    # TODO: If any other prompts for the future, change this function to be able to retrieve any prompt from the prompts directory.
    try:
        with open("prompts/system_prompt.md", "r") as f:
            return f.read()
    except Exception:
        raise FileNotFoundError("System prompt file not found.")

TOOL_NAME_MAP = {
    "get_similar_tickets_tool": "Consultando la base de conocimientos de tickets similares",
    "search_web_tool": "Buscando información en la web"
}

def format_trace(messages: list) -> list:
    """Reconstructs a user-friendly execution trace from a list of LangChain messages."""
    trace = []
    for msg in messages:
        if msg.type == "human":
            continue
        
        if msg.type == "ai":
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get("name")
                    friendly_name = TOOL_NAME_MAP.get(tool_name, f"Ejecutando herramienta: {tool_name}")
                    trace.append({
                        "node": "agent",
                        "event": "thought",
                        "description": f"El agente decidió: {friendly_name}",
                        "active": True
                    })
            elif msg.content:
                trace.append({
                    "node": "agent",
                    "event": "answer",
                    "description": "El agente ha generado una respuesta final.",
                    "active": True
                })
        
        elif msg.type == "tool":
            trace.append({
                "node": "tools",
                "event": "result",
                "description": "Se ha procesado la información obtenida.",
                "active": True
            })
            
    return trace