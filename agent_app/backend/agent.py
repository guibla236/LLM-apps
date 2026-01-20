
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
import time

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
system_message = '''You are an IT Support Agent that helps users resolve technical problems through chat.
You have access to tools to find similar tickets in our knowledge base and search the web for solutions.

Follow these guidelines:
1. Be helpful, professional, and concise.
2. If the user presents a problem, use the `get_similar_tickets_tool` to see if we have historical solutions.
3. If more information is needed or if no similar tickets are found, use the `search_web_tool`.
4. Combine the information found to propose a clear, step-by-step solution.
5. If the user's message is just a greeting or unrelated to a technical problem, respond politely but guide them towards presenting their technical issue.
6. Always check if you have enough information before proposing a solution; ask clarifying questions if necessary.
7. You must never mention the names of your tools or the names of the functions you are using.
8. Do not share raw JSONs or code unless the user asks for it.
9. Respond in the same language as the user.'''

from checkpoint import AsyncMongoDBSaver
from motor.motor_asyncio import AsyncIOMotorClient

# Initialize MongoDB Connection for Checkpointer
MONGODB_URI = os.getenv("MONGODB_URI")
mongo_client = AsyncIOMotorClient(MONGODB_URI)
db_name = os.getenv("MONGODB_DB_NAME", "ticket_system")
db = mongo_client[db_name]

# Initialize memory checkpointer
checkpointer = AsyncMongoDBSaver(db)

# Create the agent using LangGraph with checkpointer
agent_executor = create_react_agent(llm, tools, prompt=system_message, checkpointer=checkpointer)

async def generate_session_title(first_message: str, first_response: str) -> str:
    """Generates a short title (3-5 words) for the chat session using Groq."""
    try:
        # Use a separate invocation or a simple prompt to summarize
        prompt = f"""Summarize the following conversation in 3-5 words for a title. Do not use quotes.
        User: {first_message[:200]}
        AI: {first_response[:200]}
        Title:"""
        
        # We can reuse the same LLM instance
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        title = response.content.strip().replace('"', '')
        return title
    except Exception as e:
        print(f"Error generating title: {e}")
        return "Nueva Conversación"

async def get_user_sessions(username: str):
    """Retrieves all chat sessions for a given username from the sessions collection."""
    # Query the sessions collection directly
    cursor = db["sessions"].find({"username": username}).sort("last_updated", -1)
    
    sessions = []
    async for doc in cursor:
        sessions.append({
            "session_id": doc.get("session_id"), # Stored UUID part
            "thread_id": doc.get("thread_id"),   # Full LangGraph ID
            "title": doc.get("title", "Chat sin título"),
            "last_updated": doc.get("last_updated").isoformat() if doc.get("last_updated") else None
        })
    return sessions

async def get_session_history_messages(thread_id: str):
    """Retrieves the message history for a specific thread."""
    config = {"configurable": {"thread_id": thread_id}}
    # Retrieve the state
    state = await agent_executor.aget_state(config)
    messages = []
    if state and state.values and "messages" in state.values:
        for msg in state.values["messages"]:
            # Serialize for frontend
            role = "unknown"
            if msg.type == "human": role = "user"
            elif msg.type == "ai": role = "assistant"
            elif msg.type == "tool": role = "tool"  # Valid for tool outputs
            
            # We filter out SystemMessages or keep them if needed. Usually frontends hide them.
            if role in ["user", "assistant"]: 
                 messages.append({"role": role, "content": msg.content})
    return messages

async def chat_with_agent(message: str, thread_id: str = "default_user") -> str:
    """
    Handles a conversation with the agent using LangGraph state persistence.
    """
    from langchain_core.messages import HumanMessage
    
    start_time = time.perf_counter()
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # LangGraph rehydrates state from memory based on thread_id
        response = await agent_executor.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config=config
        )
        solution = response["messages"][-1].content
        duration = round(time.perf_counter() - start_time, 2)
        
        # --- Session Management ---
        try:
            # Parse username and session_uuid from thread_id (format: user_uuid)
            parts = thread_id.split("_", 1)
            if len(parts) == 2:
                username, session_uuid = parts
                
                # Check if session exists
                session_doc = await db["sessions"].find_one({"thread_id": thread_id})
                
                update_data = {
                    "last_updated": datetime.utcnow()
                }
                
                if not session_doc:
                    # New session: Generate Title
                    title = await generate_session_title(message, solution)
                    update_data["title"] = title
                    update_data["created_at"] = datetime.utcnow()
                    update_data["thread_id"] = thread_id
                    update_data["session_id"] = session_uuid
                    update_data["username"] = username
                    
                    await db["sessions"].insert_one(update_data)
                else:
                    # Update existing session timestamp
                    await db["sessions"].update_one(
                        {"thread_id": thread_id},
                        {"$set": update_data}
                    )
        except Exception as session_e:
            print(f"Error updating session metadata: {session_e}")
            # Non-blocking error
        
        # Log execution
        await agent_logger.log_execution(
            ticket_id=f"CHAT-{thread_id}",
            user=thread_id,
            input_data=message,
            solution=solution,
            execution_time=duration
        )
        return solution
    except Exception as e:
        import traceback
        print(f"CRITICAL AGENT ERROR: {e}")
        traceback.print_exc()
        duration = round(time.perf_counter() - start_time, 2)
        error_msg = str(e)
        await agent_logger.log_execution(
            ticket_id=f"CHAT-{thread_id}",
            user=thread_id,
            input_data=message,
            solution=None,
            execution_time=duration,
            status="error",
            error_message=error_msg
        )
        return f"Error running agent: {error_msg}"

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
