from langchain_core.messages import HumanMessage
import time
from datetime import datetime
from agent import agent_executor
from logger import agent_logger
from motor.motor_asyncio import AsyncIOMotorClient
from core.database import get_db
from services.session_service import generate_session_title

db = get_db()

async def chat_with_agent(message: str, thread_id: str) -> str:
    """
    Handles a conversation with the agent using LangGraph state persistence.
    """
    
    start_time = time.perf_counter()
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # LangGraph rehydrates state from memory based on thread_id
        response = await agent_executor.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config=config
        )
        
        # Robustly find the last AI message with actual content
        solution = "Lo siento, no pude generar una respuesta válida."
        for msg in reversed(response["messages"]):
             if msg.type == "ai" and msg.content and not msg.tool_calls:
                 solution = msg.content
                 break
             # If we find a tool call at the end, it implies the agent got stuck or the LLM decided to stop.
             # We try to get content even if tool_calls exist, as some models output thought+tool_call.
             if msg.type == "ai" and msg.content:
                 solution = msg.content
                 break
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