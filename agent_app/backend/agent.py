
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
import os
import requests
import json
from dotenv import load_dotenv
from model import TicketModel
from logger import agent_logger
import httpx
from datetime import datetime

load_dotenv()

# --- Configuration ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
CHAT_MODEL_NAME = os.getenv("CHAT_MODEL_NAME", "llama-3.1-8b-instant")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
APP_API_KEY = os.getenv("APP_API_KEY")

# Initialize LLM
llm = ChatGroq(
    temperature=0,
    model_name=CHAT_MODEL_NAME,
    api_key=GROQ_API_KEY
)

async def is_tool_enabled(flag_name: str) -> bool:
    """Helper to check if a specific tool is enabled via feature flags API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/api/flags/{flag_name}", timeout=5.0)
            if response.status_code == 200:
                return response.json().get("enabled", True)
    except Exception:
        pass
    return True # Default to enabled if API fails

# --- Tools ---

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

# Tavily Tool wrapped to avoid schema complexity / type errors
# LLMs sometimes struggle with the complex schema of TavilySearch (sending strings for lists)
# So we expose a simpler interface.
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

tools = [get_similar_tickets_tool, search_web_tool]

# --- Agent Definition ---

system_message = '''You are an IT Support Agent that must resolve support tickets with the help of previous tickets and web search.
You have access to tools to find similar tickets and search the web.
You must always first check for similar tickets and based on that, you can search the web for more details on the actions to take if needed.
Propose a complete solution based on the findings.'''

# Create the agent using LangGraph
agent_executor = create_react_agent(llm, tools, prompt=system_message)

async def solve_ticket(ticket_to_resolve: TicketModel, username: str = "anonymous") -> str:
    """
    Main entry point for the agent.
    """
    description = ticket_to_resolve.description
    if not description:
        return "Error: Ticket has no description."

    query = f"""
    I have a support ticket with the following description:
    "{description}"
    
    Please help me resolve it by following these steps:
    1. First, search for similar tickets in our database to see if this has happened before and what actions were taken.
    2. Then, use the web search to find public information or documentation about this error.
    3. Finally, combine the information to propose a step-by-step solution.
    4. The solution must match the language of the ticket description; please translate it if necessary but do not inform the user about the translation.
    """
    
    execution_id = None
    try:
        # LangGraph ainvoke for async execution
        response = await agent_executor.ainvoke({"messages": [HumanMessage(content=query)]})
        solution = response["messages"][-1].content
        
        # Log successful execution
        execution_id = await agent_logger.log_execution(
            ticket_id=ticket_to_resolve.ticketId,
            user=username,
            input_data=description,
            solution=solution
        )
        return solution
    except Exception as e:
        error_msg = str(e)
        # Log failed execution
        execution_id = await agent_logger.log_execution(
            ticket_id=ticket_to_resolve.ticketId,
            user=username,
            input_data=description,
            solution=None,
            status="error",
            error_message=error_msg
        )
        return f"Error running agent (ID: {execution_id}): {error_msg}"
