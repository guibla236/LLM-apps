from langchain_core.messages import HumanMessage
import time
from datetime import datetime
from agent.graph import app_graph
from core.logger import agent_logger
from services.session_service import generate_session_title
from langchain_core.runnables.config import RunnableConfig
from core.utils import format_trace

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
        solution = "I'm sorry, but I couldn't generate a valid response."
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