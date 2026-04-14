from langchain_core.messages import HumanMessage
import time
from datetime import datetime
from agent.graph import app_graph
from core.logger import agent_logger
from schema.ticket import TicketModel
from services.session_service import generate_session_title
from langchain_core.runnables.config import RunnableConfig
from core.utils import format_trace
import warnings  # used for deprecation notices

async def chat_with_agent(
        message: str, 
        thread_id: str, 
        db
    ) -> tuple[str, list]:
    """
    Handles a conversation with the agent using LangGraph state persistence.
    Includes context window management to avoid reaching LLM token limits
    by dynamically summarizing old messages when needed.
    Returns a tuple (solution, trace).
    """
    
    start_time = time.perf_counter()
    config: RunnableConfig = {
        "configurable": {
            "thread_id": thread_id
        }, 
        "recursion_limit": 10
    }
    
    try:
        # LangGraph rehydrates state from memory based on thread_id
        response = await app_graph.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config=config
        )
        
        # Robustly find the last AI message with actual content
        solution = "Lo siento, no pude generar una respuesta válida."
        all_messages = response["messages"]
        for msg in reversed(all_messages):
             if msg.type == "ai" and msg.content and not msg.tool_calls:
                 solution = msg.content
                 break
             if msg.type == "ai" and msg.content:
                 solution = msg.content
                 break
        
        trace = format_trace(all_messages)
        duration = round(time.perf_counter() - start_time, 2)
        
        # --- Session Management ---
        try:
            # Parse username and session_uuid from thread_id (format: user_uuid)
            parts = thread_id.split("_", 1)
            if len(parts) == 2:
                username, session_uuid = parts
                
                # Check if session exists
                session_doc = await db["sessions"].find_one({"thread_id": thread_id})
                
                update_data: dict = {
                    "last_updated": datetime.now()
                }
                
                if not session_doc:
                    # New session: Generate Title
                    title = await generate_session_title(message, solution)
                    update_data["title"] = title
                    update_data["created_at"] = datetime.now()
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
            await agent_logger.log_error(
                user="system",
                path="chat_with_agent",
                method="POST",
                error_message="Error updating session metadata. This does not affect the agent response but may impact session tracking features.",
                traceback_data=str(session_e)
            )
        
        # Log execution
        await agent_logger.log_execution(
            ticket_id=f"CHAT-{thread_id}",
            user=thread_id,
            input_data=message,
            solution=solution,
            execution_time=duration
        )
        return solution, trace
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
        return f"Error running agent: {error_msg}", []



    This function and the `/solve_ticket` endpoint are planned for removal in a
    future release. Callers should migrate to :func:`chat_with_agent`

    The warning is emitted on every invocation so that automated tests and
    internal code will surface the migration requirement.
    """
    # runtime deprecation notice for developers
    warnings.warn(
        "solve_ticket() is deprecated and will be removed in a future release; "
        "use chat_with_agent() or the new v2 API instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    description = ticket_to_resolve.description
    if not description:
        return "Error: Ticket has no description.", []

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
        all_messages = response["messages"]
        solution = all_messages[-1].content
        trace = format_trace(all_messages)
        duration = round(time.perf_counter() - start_time, 2)
        
        await agent_logger.log_execution(
            ticket_id=ticket_to_resolve.ticketId,
            user=username,
            input_data=description,
            solution=solution,
            execution_time=duration
        )
        return solution, trace
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
        return f"Error running agent: {error_msg}", []