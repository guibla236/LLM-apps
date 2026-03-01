import httpx
from core.config import get_env_var
from functools import lru_cache
from core.logger import agent_logger, log_background
from prompts.model import PromptFileNames

_API_BASE_URL = get_env_var("API_BASE_URL")
_MAX_CHARS_CONTEXT_THRESHOLD = get_env_var("MAX_CHARS_CONTEXT_THRESHOLD")

async def is_tool_enabled(flag_name: str) -> bool:
    """Helper to check if a specific tool is enabled via feature flags API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{_API_BASE_URL}/api/flags/{flag_name}", timeout=5.0)
            if response.status_code == 200:
                return response.json().get("enabled", True)
    except Exception:
        log_background(
            kind='error',
            user="system",
            path="is_tool_enabled",
            method="GET",
            error_message=f"Failed to fetch feature flag '{flag_name}'. Defaulting to enabled.",
            traceback_data=""
        )
    return False # Default to disabled if API fails

@lru_cache(maxsize=10)    
def get_prompt(prompt_name: PromptFileNames) -> str:
    """Helper to read markdown file with a specific prompt."""
    try:
        with open(f"prompts/{prompt_name}.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        # fire-and-forget; the caller is synchronous now
        log_background(
            kind='error',
            user="system",
            path="get_prompt",
            method="GET",
            error_message=f"Prompt file '{prompt_name}.md' not found.",
            traceback_data=""
        )
        return ""
    except Exception as e:
        log_background(
            kind='error',
            user="system",
            path="get_prompt",
            method="GET",
            error_message=f"Error reading prompt file '{prompt_name}.md'.",
            traceback_data=str(e)
        )
        return ""

_TOOL_NAME_MAP = {
    "advanced_search_tool": "Searching tickets and knowledge base for relevant information",
    "search_web_tool": "Searching the web for relevant information"
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
                    friendly_name = _TOOL_NAME_MAP.get(tool_name, f"Executing tool: {tool_name}")
                    trace.append({
                        "node": "agent",
                        "event": "thought",
                        "tool_id": tool_name, # Added technical ID
                        "description": f"Agent decided to execute: {friendly_name}",
                        "active": True
                    })
            elif msg.content:
                trace.append({
                    "node": "agent",
                    "event": "answer",
                    "description": "Agent has generated a final response.",
                    "active": True
                })
        
        elif msg.type == "tool":
            tool_name = getattr(msg, 'name', None)
            
            # Map tool result descriptions
            RESULT_DESCRIPTIONS = {
                "advanced_search_tool": "Knowledge base search results have been processed.",
                "search_web_tool": "Web search results have been processed."
            }
            friendly_desc = RESULT_DESCRIPTIONS.get(tool_name, "Tool result has been processed.") if tool_name else "Tool result has been processed."
            
            trace.append({
                "node": "tools",
                "event": "result",
                "tool_id": tool_name,
                "description": friendly_desc,
                "active": True
            })
            
    return trace

async def get_chars_context_threshold():
    try:
        if _MAX_CHARS_CONTEXT_THRESHOLD is not None:
            return int(_MAX_CHARS_CONTEXT_THRESHOLD)
        else:
            raise ValueError("MAX_CHARS_CONTEXT_THRESHOLD is not set.")
    except (ValueError, TypeError) as e:
        await agent_logger.log_error(
            user="system",
            path="get_chars_context_threshold",
            method="GET",
            error_message="Invalid MAX_CHARS_CONTEXT_THRESHOLD value. Please ensure it's set to a valid integer.",
            traceback_data=str(e)
        )
