from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage
from core.config import get_llm
from core.utils import get_prompt, get_chars_context_threshold
from core.logger import agent_logger
from prompts.model import PromptFileNames
from agent.state import AgentState

async def manage_memory_node(state: AgentState):
    existing_messages = state["messages"]
    
    # First we check the size of the messages list
    total_chars = sum(len(msg.content) for msg in existing_messages if hasattr(msg, "content") and isinstance(msg.content, str))
    
    max_chars = await get_chars_context_threshold()
    if max_chars is None:
        max_chars = 4000 # Fallback value
    
    if total_chars > max_chars:
        messages_to_summarize = existing_messages[:-4]
        text_to_summarize = ""
        for msg in messages_to_summarize:
            role = getattr(msg, "type", "unknown")
            content = getattr(msg, "content", "")
            if isinstance(content, str):
                text_to_summarize += f"[{role.upper()}]: {content}\n"
                
        try:
            llm = get_llm()
            summary_response = await llm.ainvoke([
                SystemMessage(content=get_prompt(PromptFileNames.SUMMARY_PROMPT)),
                HumanMessage(content=f"Previous interactions to summarize:\n {text_to_summarize}")
            ])
            
            first_msg_id = getattr(messages_to_summarize[0], "id", None)
            kwargs = {"id": first_msg_id} if first_msg_id else {}
            
            new_summary_msg = SystemMessage(
                content=f"Summary of previous interactions:\n {summary_response.content}",
                name="context_summary",
                **kwargs
            )
            
            # We return a generic RemoveMessage to delete the summarized messages
            to_remove = [RemoveMessage(id=m.id) for m in messages_to_summarize[1:] if getattr(m, "id", None)]
            
            return {
                "messages": [new_summary_msg] + to_remove
            }
        except Exception as e:
            await agent_logger.log_error(
                user="system",
                path="manage_memory_node",
                method="POST",
                error_message="Error during summarization in memory node.",
                traceback_data=str(e)
            )
            return {
                "messages": []
            }
    return {
        "messages": []
    }
                
            