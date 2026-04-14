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

# Export agent graph image to a file
try:
    graph_image_data = app_graph.get_graph().draw_mermaid_png()
    with open("agent_graph.png", "wb") as f:
        f.write(graph_image_data)
    print("Agent graph image successfully saved to agent_graph.png")
except Exception as e:
    print(f"Notice: Could not generate agent graph image: {e}")
    # Note: draw_mermaid_png may require 'pyppeteer' or 'graphviz' depending on the environment context