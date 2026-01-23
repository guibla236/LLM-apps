
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
import os
import requests
import json
from dotenv import load_dotenv
from schema.ticket import TicketModel
from logger import agent_logger
from utils import get_system_prompt
import httpx
from datetime import datetime
import time
from tools.get_similar_tickets import get_similar_tickets_tool
from tools.search_web import search_web_tool
from core.database import get_checkpointer, get_db
from core.config import get_llm

load_dotenv()

# --- Configuration ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
CHAT_MODEL_NAME = os.getenv("CHAT_MODEL_NAME", "llama-3.1-8b-instant")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
APP_API_KEY = os.getenv("APP_API_KEY")

# Get LLM instance
llm = get_llm()

# Initialize memory checkpointer
checkpointer = get_checkpointer()
db = get_db()

# Define the tools list
tools_list = [get_similar_tickets_tool, search_web_tool]

# Create the agent using LangGraph with checkpointer
agent_executor = create_react_agent(llm, tools_list, prompt=get_system_prompt(), checkpointer=checkpointer)

async def solve_ticket(ticket_to_resolve: TicketModel, username: str = "anonymous") -> str:
    """
    Main entry point for the agent (Legacy/Ticket mode).
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
    
    start_time = time.perf_counter()
    try:
        response = await agent_executor.ainvoke({"messages": [HumanMessage(content=query)]})
        solution = response["messages"][-1].content
        duration = round(time.perf_counter() - start_time, 2)
        
        await agent_logger.log_execution(
            ticket_id=ticket_to_resolve.ticketId,
            user=username,
            input_data=description,
            solution=solution,
            execution_time=duration
        )
        return solution
    except Exception as e:
        duration = round(time.perf_counter() - start_time, 2)
        error_msg = str(e)
        await agent_logger.log_execution(
            ticket_id=ticket_to_resolve.ticketId,
            user=username,
            input_data=description,
            solution=None,
            execution_time=duration,
            status="error",
            error_message=error_msg
        )
        return f"Error running agent: {error_msg}"
