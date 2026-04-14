from core.config import get_llm
from core.utils import get_prompt
from prompts.model import PromptFileNames
from langchain_core.messages import SystemMessage
from tools.advanced_search import advanced_search_tool
from tools.search_web import search_web_tool
from core.logger import agent_logger
from agent.state import AgentState

tools_list = [advanced_search_tool, search_web_tool]
llm = get_llm().bind_tools(tools_list)

async def call_model_node(state: AgentState):
    messages = state["messages"]
    
    # Injecting sys prompt
    sys_prompt = SystemMessage(
        content=get_prompt(PromptFileNames.SYSTEM_PROMPT)
    )
    
    try:
        # LLM to decide if it needs to call a tool or generate a final response based on the messages and system prompt
        response = await llm.ainvoke([sys_prompt] + messages)
        return {
            "messages": [response]
        }
    except Exception as e:
        await agent_logger.log_error(error_message="Error during LLM invocation in call_model_node.", traceback_data=str(e), user="system", path="call_model_node", method="POST")
        return {
            "messages": [SystemMessage(content="Sorry, there was an error processing your request.")]
        }