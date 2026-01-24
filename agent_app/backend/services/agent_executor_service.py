from langchain.agents import create_agent
from core.utils import get_system_prompt
from tools.get_similar_tickets import get_similar_tickets_tool
from tools.search_web import search_web_tool
from core.database import get_db, get_checkpointer
from core.config import get_llm

# Get LLM instance
llm = get_llm()

# Initialize memory checkpointer
checkpointer = get_checkpointer()
db = get_db()

# Define the tools list
tools_list = [get_similar_tickets_tool, search_web_tool]

# Create the agent using LangGraph with checkpointer
agent_executor = create_agent(llm, tools_list, system_prompt=get_system_prompt(), checkpointer=checkpointer)