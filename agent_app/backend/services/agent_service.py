from langchain_core.messages import HumanMessage, SystemMessage, RemoveMessage
import time
from datetime import datetime
from services.agent_executor_service import agent_executor
from core.logger import agent_logger
from schema.ticket import TicketModel
from core.config import get_llm
from services.session_service import generate_session_title
from langchain_core.runnables.config import RunnableConfig
from core.utils import format_trace, get_prompt, get_chars_context_threshold
from prompts.model import PromptFileNames
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
        await _manage_context_window(config)  # Ensure we manage the context window before invoking the agent

        # LangGraph rehydrates state from memory based on thread_id
        response = await agent_executor.ainvoke(
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

    
async def _manage_context_window(config: RunnableConfig):
    state = await agent_executor.aget_state(config)
    existing_messages = state.values.get("messages", []) if state.values else []
    
    # Estimate character length roughly mapping to tokens
    total_chars = sum(len(msg.content) for msg in existing_messages if hasattr(msg, "content") and isinstance(msg.content, str))
    
    # If conversation is getting too long, summarize older parts and keep only recent context
    max_chars = await get_chars_context_threshold()
    if max_chars is None:
        await agent_logger.log_error(
            user="system",
            path="chat_with_agent",
            method="POST",
            error_message="MAX_CHARS_CONTEXT_THRESHOLD is not set. Skipping context management.",
            traceback_data=""
        )
        return "Error: System configuration issue. Please contact support.", []
    if total_chars > max_chars and len(existing_messages) > 4:
        # We preserve the last 4 messages exactly as they are to not lose the immediate conversational flow
        messages_to_summarize = existing_messages[:-4]
        
        # Format text for the LLM to summarize
        text_to_summarize = ""
        for msg in messages_to_summarize:
            role = getattr(msg, "type", "unknown")
            content = getattr(msg, "content", "")
            if isinstance(content, str):
                text_to_summarize += f"[{role.upper()}]: {content}\n"
        try:
            # Call our existing LLM
            llm = get_llm()
            summary_response = await llm.ainvoke([
                SystemMessage(content=get_prompt(PromptFileNames.SUMMARY_PROMPT)),
                HumanMessage(content=f"Previous interactions to summarize: \n{text_to_summarize}")
            ])
            
            # Save space: Reuse the ID of the first message to have LangGraph replace it
            # precisely at the start (head) of our tracked message memory stream.
            first_msg_id = getattr(messages_to_summarize[0], "id", None)
            if first_msg_id is None:
                await agent_logger.log_error(
                    user="system",
                    path="chat_with_agent",
                    method="POST",
                    error_message="First message in context has no ID. The summary is added as last message without replacing the old context.",
                    traceback_data=""
                )
                new_summary_msg = SystemMessage(
                    content=f"=== Summary of past interactions ===\n{summary_response.content}",
                    name="context_summary"
                )
            else:    
                new_summary_msg = SystemMessage(
                    content=f"=== Summary of past interactions ===\n{summary_response.content}",
                    id=first_msg_id,
                    name="context_summary"
                )
        except Exception as e:
            # Log error but continue without summarization to avoid breaking the user experience
            await agent_logger.log_error(
                user="system",
                path="chat_with_agent",
                method="POST",
                error_message="Error during context summarization. Proceeding without summarization.",
                traceback_data=str(e)
            )
        
        # Prepare instructions to destroy the rest of the old messages we summarized
        to_remove = [RemoveMessage(id=m.id) for m in messages_to_summarize[1:] if getattr(m, "id", None)]
        
        # Execute the surgical pruning to the checkpointer database
        await agent_executor.aupdate_state(config, {"messages": [new_summary_msg] + to_remove})


async def solve_ticket(ticket_to_resolve: TicketModel, username: str = "anonymous") -> tuple[str, list]:
    """
    **DEPRECATED** legacy entry point for the agent (Ticket mode).

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