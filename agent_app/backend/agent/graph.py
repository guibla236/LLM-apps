"""Multi-step diagnosis agent graph (M7).

manage_memory -> analyze_query -> search_rag -> evaluate_sufficiency
             -> [refine_query -> search_rag]* -> generate_answer

- `manage_memory` reuses the legacy summarization node: long conversations
  are summarized before each turn, exactly as the old ReAct graph did.
- Hard stop at `max_iterations` (3) enforced by the evaluate router.
- Search strategy (vector_only / hybrid) is decided per-query by analyze_node.
- The legacy ReAct graph remains available behind USE_LEGACY_AGENT=true.
"""
import os

from langgraph.graph import StateGraph, START, END

from agent.state import AgentState
from agent.nodes.memory import manage_memory_node
from agent.nodes.analyze import analyze_node
from agent.nodes.search import search_node
from agent.nodes.evaluate import evaluate_node
from agent.nodes.refine import refine_node
from agent.nodes.generate import generate_node
from core.database import get_checkpointer

USE_LEGACY_AGENT = os.getenv("USE_LEGACY_AGENT", "false").lower() == "true"


def _route_after_evaluate(state):
    """Route to generate when context is sufficient or iteration budget is spent."""
    iteration_count = state.get("iteration_count") or 1
    max_iterations = state.get("max_iterations") or 3
    if state.get("sufficient") or iteration_count >= max_iterations:
        return "generate"
    return "refine"


def _build_legacy_graph() -> StateGraph:
    """Original ReAct graph (manage_memory -> agent -> tools)."""
    from langgraph.prebuilt import ToolNode, tools_condition
    from agent.nodes.memory import manage_memory_node
    from agent.nodes.model import call_model_node, tools_list

    wf = StateGraph(AgentState)
    wf.add_node("manage_memory", manage_memory_node)
    wf.add_node("agent", call_model_node)
    wf.add_node("tools", ToolNode(tools_list))

    wf.add_edge(START, "manage_memory")
    wf.add_edge("manage_memory", "agent")
    wf.add_conditional_edges("agent", tools_condition)
    wf.add_edge("tools", "agent")
    return wf


def _build_diagnosis_graph() -> StateGraph:
    """Multi-step diagnosis graph: manage_memory -> analyze -> search -> evaluate -> (refine)* -> generate."""
    wf = StateGraph(AgentState)

    # Reuses the legacy summarization node: keeps long conversations bounded
    wf.add_node("manage_memory", manage_memory_node)
    wf.add_node("analyze", analyze_node)
    wf.add_node("search", search_node)
    wf.add_node("evaluate", evaluate_node)
    wf.add_node("refine", refine_node)
    wf.add_node("generate", generate_node)

    wf.add_edge(START, "manage_memory")
    wf.add_edge("manage_memory", "analyze")
    wf.add_edge("analyze", "search")
    wf.add_edge("search", "evaluate")
    wf.add_conditional_edges(
        "evaluate",
        _route_after_evaluate,
        {"refine": "refine", "generate": "generate"},
    )
    wf.add_edge("refine", "search")
    wf.add_edge("generate", END)
    return wf


workflow = _build_legacy_graph() if USE_LEGACY_AGENT else _build_diagnosis_graph()

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