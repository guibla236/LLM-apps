from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from agent.state import AgentState
from agent.nodes.memory import manage_memory_node
from agent.nodes.model import call_model_node, tools_list
from core.database import get_checkpointer

# Flow instantiation
workflow = StateGraph(AgentState)

# Nodes definition
workflow.add_node("manage_memory", manage_memory_node)
workflow.add_node("agent", call_model_node)
workflow.add_node("tools", ToolNode(tools_list))

# Edges definition (node's connections)
workflow.add_edge(START, "manage_memory")
workflow.add_edge("manage_memory", "agent")

# Conditional Edge
workflow.add_conditional_edges("agent", tools_condition)

# Final Edge
workflow.add_edge("tools", "agent")

# Checkpointer integration
checkpointer = get_checkpointer()
app_graph = workflow.compile(checkpointer=checkpointer)
