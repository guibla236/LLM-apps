from agent.graph import app_graph
from langchain_core.runnables.config import RunnableConfig
from core.database import get_db
from langchain_core.messages import HumanMessage
from core.config import get_llm

# Get DB and LLM instances
db = get_db()
llm = get_llm()

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
        if isinstance(response.content, str):
            title = response.content.strip().replace('"', '')
            return title
        return "New Conversation"
    except Exception as e:
        print(f"Error generating title: {e}")
        return "New Conversation"

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

async def delete_user_session(username: str, session_id: str):
    """Deletes a session and all its associated checkpoints."""
    thread_id = f"{username}_{session_id}"
    
    # Delete from sessions metadata
    await db["sessions"].delete_one({"thread_id": thread_id})
    
    # Delete checkpoints
    await db["checkpoints"].delete_many({"thread_id": thread_id})
    
    # Delete writes (intermediate steps)
    await db["checkpoints_writes"].delete_many({"thread_id": thread_id})
    
    return True

async def get_session_history_messages(thread_id: str):
    """Retrieves the message history for a specific thread with context traces."""
    from core.utils import format_trace
    config = RunnableConfig(configurable={"thread_id": thread_id})
    state = await app_graph.aget_state(config)
    
    if not (state and state.values and "messages" in state.values):
        return []

    raw_messages = state.values["messages"]
    processed = []
    
    # Track the messages belonging to the current "turn" (from one Human message to the next)
    current_turn_raw = []
    
    for msg in raw_messages:
        if msg.type == "human":
            # If we were tracking a turn, it means it's finished. 
            # (Though in standard chat, AI/Tools always follow Human).
            current_turn_raw = [msg]
            processed.append({"role": "user", "content": msg.content})
        
        elif msg.type == "ai":
            current_turn_raw.append(msg)
            # If it's a final answer (has content and no tool calls), we attach the trace of the turn up to here
            if msg.content and (not hasattr(msg, 'tool_calls') or not msg.tool_calls):
                trace = format_trace(current_turn_raw)
                processed.append({
                    "role": "assistant", 
                    "content": msg.content,
                    "trace": trace
                })
                # Reset turn raw after final answer to avoid double counting if multiple AI msgs exist
                current_turn_raw = [] 
            
        elif msg.type == "tool":
            current_turn_raw.append(msg)
            
    return processed
