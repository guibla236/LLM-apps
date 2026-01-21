

from langchain_tavily import TavilySearch
from utils import is_tool_enabled
from langchain_core.tools import tool

tavily_search = TavilySearch(max_results=3)

@tool
async def search_web_tool(query: str) -> str:
    """
    Useful to search the internet for solutions, documentation, and logic.
    Input should be a search query string.
    """
    if not await is_tool_enabled("enable_web_search"):
        return "La búsqueda web está temporalmente desactivada por el administrador."

    try:
        # We invoke the async version of the tool if available, or just run it in a thread if not.
        # TavilySearch from langchain_tavily has ainvoke.
        response = await tavily_search.ainvoke({"query": query})
        output = []
        for res in response['results']:
            output.append(f"Source: {res['url']}\nContent: {res['content']}")
        return "\n\n".join(output)
    except Exception as e:
        return f"Error searching web: {str(e)}"