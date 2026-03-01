from langchain.agents import create_agent
from core.utils import get_prompt
from tools.advanced_search import advanced_search_tool
from tools.search_web import search_web_tool
from core.database import get_db, get_checkpointer
from core.config import get_llm
from prompts.model import PromptFileNames
import asyncio

# Get LLM instance
llm = get_llm()

# Initialize memory checkpointer
checkpointer = get_checkpointer()
db = get_db()

# Define the tools list
tools_list = [advanced_search_tool, search_web_tool]

# Create the agent using LangGraph with checkpointer
# get_prompt is async, so build a small coroutine that awaits it and then
# calls create_agent; pass that coroutine to asyncio.run to obtain the
# executor.
async def _build_agent_executor():
	system_prompt = await get_prompt(PromptFileNames.SYSTEM_PROMPT)
	return create_agent(
		llm,
		tools_list,
		system_prompt=system_prompt,
		checkpointer=checkpointer,
	)

agent_executor = asyncio.run(_build_agent_executor())