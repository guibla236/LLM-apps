
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

load_dotenv()

# --- Configuration ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
CHAT_MODEL_NAME = os.getenv("CHAT_MODEL_NAME", "llama-3.1-8b-instant")

# Initialize LLM
llm = ChatGroq(
    temperature=0,
    model_name=CHAT_MODEL_NAME,
    api_key=GROQ_API_KEY
)

# --- Tools ---

@tool
def get_similar_tickets_tool(description: str) -> str:
    """
    Useful to find similar support tickets in the database. 
    Input should be a detailed description of the problem.
    Returns a string representation of similar tickets found.
    """
    url = "http://localhost:8000/api/get_similar_tickets"
    
    # Construct a dummy ticket dictionary for the API
    payload = {
        "ticketId": "SEARCH-QUERY",
        "creationDate": "2024-01-01", # Required
        "priority": "Medium", # Default
        "owner": "Agent",
        "description": description,
        "impact": "Unknown",
        "actions": "None"
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        tickets = response.json()
        
        if not tickets:
            return "No similar tickets found."
            
        # Format the output for the LLM
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
def search_web_tool(query: str) -> str:
    """
    Useful to search the internet for solutions, documentation, and logic.
    Input should be a search query string.
    """
    try:
        results = tavily_search.invoke({"query": query})
        # Parse results to string
        output = []
        for res in results:
            output.append(f"Source: {res.get('url')}\nContent: {res.get('content')}")
        return "\n\n".join(output)
    except Exception as e:
        return f"Error searching web: {str(e)}"

tools = [get_similar_tickets_tool, search_web_tool]

# --- Agent Definition ---

system_message = '''Answer the following questions as best you can. You have access to tools to find similar tickets and search the web.
Always first check for similar tickets, then search the web if needed.
Propose a complete solution based on the findings.'''

# Create the agent using LangGraph
agent_executor = create_react_agent(llm, tools, prompt=system_message)

def solve_ticket(ticket_to_resolve: TicketModel) -> str:
    """
    Main entry point for the agent.
    """
    description = ticket_to_resolve.description
    if not description:
        return "Error: Ticket has no description."

    query = f"""
    I have a support ticket with the following description:
    "{description}"
    
    Please help me resolve it.
    1. First, search for similar tickets in our database to see if this has happened before and what actions were taken.
    2. Then, use the web search to find public information or documentation about this error.
    3. Finally, combine the information to propose a step-by-step solution.
    4. The solution must match the language of the ticket description; please translate it if necessary.
    """
    
    try:
        # LangGraph invoke expects "messages"
        response = agent_executor.invoke({"messages": [HumanMessage(content=query)]})
        # The last message is the AI's final answer
        return response["messages"][-1].content
    except Exception as e:
        return f"Error running agent: {str(e)}"
