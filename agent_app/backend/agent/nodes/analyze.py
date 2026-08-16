"""analyze_query node: classify the query and decide search strategy.

First node of every turn. Resets the working-memory fields (transient state)
and records the first trace event. Does NOT write to ``messages`` — the
conversation history only gets the user message and the final answer.
"""
from langchain_core.messages import SystemMessage, HumanMessage

from core.config import get_llm
from core.utils import get_prompt
from prompts.model import PromptFileNames
from agent.nodes.utils import extract_json, last_human_message

_VALID_STRATEGIES = ("vector_only", "hybrid")


async def analyze_node(state):
    """Decide search strategy (vector_only default, hybrid on lexical signals)
    and produce the first search query."""
    user_query = last_human_message(state.get("messages") or [])
    llm = get_llm()

    response = await llm.ainvoke(
        [
            SystemMessage(content=get_prompt(PromptFileNames.ANALYZE_PROMPT)),
            HumanMessage(content=user_query),
        ]
    )

    data = extract_json(str(response.content))
    strategy = data.get("search_strategy", "vector_only")
    if strategy not in _VALID_STRATEGIES:
        strategy = "vector_only"
    search_query = data.get("search_query") or user_query
    analysis = data.get("analysis", "")

    return {
        "search_strategy": strategy,
        "query_history": [search_query],
        "iteration_count": 1,
        "max_iterations": 3,
        "sufficient": False,
        "gaps": [],
        "accumulated_context": [],
        "trace_events": [
            {
                "node": "analyze",
                "event": "thought",
                "description": (
                    f"Analyzed the query ({analysis or 'general IT support'}) "
                    f"and selected search strategy: {strategy}"
                ),
                "active": True,
            }
        ],
    }
