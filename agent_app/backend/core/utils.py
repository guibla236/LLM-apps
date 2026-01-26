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