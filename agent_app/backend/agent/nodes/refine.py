"""refine_query node: reformulate a more specific search query from gaps.

Working memory only: appends to ``query_history`` (read-modify-write on the
plain field) and records a trace event.
"""
from langchain_core.messages import SystemMessage, HumanMessage

from core.config import get_llm
from core.utils import get_prompt
from prompts.model import PromptFileNames
from agent.nodes.utils import last_human_message


async def refine_node(state):
    user_query = last_human_message(state.get("messages") or [])
    gaps = state.get("gaps") or []
    accumulated = state.get("accumulated_context") or []
    # Only the most recent blocks, to keep the prompt bounded
    recent_context = "\n\n".join(accumulated[-3:]) if accumulated else "(no context)"
    llm = get_llm()

    response = await llm.ainvoke(
        [
            SystemMessage(content=get_prompt(PromptFileNames.REFINE_PROMPT)),
            HumanMessage(
                content=(
                    f"Original question:\n{user_query}\n\n"
                    f"Identified gaps:\n{', '.join(str(g) for g in gaps) if gaps else 'unspecified'}\n\n"
                    f"Context already retrieved (last blocks):\n{recent_context}"
                )
            ),
        ]
    )

    new_query = str(response.content).strip().strip('"').strip("'")
    if not new_query:
        new_query = user_query

    query_history = list(state.get("query_history") or [])
    query_history.append(new_query)

    trace_events = list(state.get("trace_events") or [])
    trace_events.append(
        {
            "node": "refine",
            "event": "thought",
            "description": "Reformulated the search query to target the identified gaps",
            "active": True,
        }
    )

    return {
        "query_history": query_history,
        "iteration_count": (state.get("iteration_count") or 1) + 1,
        "trace_events": trace_events,
    }
