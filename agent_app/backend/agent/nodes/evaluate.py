"""evaluate_sufficiency node: judge whether accumulated context is enough.

Working memory only: writes ``sufficient``/``gaps`` and a trace event.
"""
from langchain_core.messages import SystemMessage, HumanMessage

from core.config import get_llm
from core.utils import get_prompt
from prompts.model import PromptFileNames
from agent.nodes.utils import extract_json, last_human_message


async def evaluate_node(state):
    user_query = last_human_message(state.get("messages") or [])
    accumulated = state.get("accumulated_context") or []
    context = "\n\n".join(accumulated) if accumulated else "(no context retrieved yet)"
    llm = get_llm()

    response = await llm.ainvoke(
        [
            SystemMessage(content=get_prompt(PromptFileNames.EVALUATE_PROMPT)),
            HumanMessage(content=f"User question:\n{user_query}\n\nRetrieved context:\n{context}"),
        ]
    )

    data = extract_json(str(response.content))
    sufficient = bool(data.get("sufficient", False))
    gaps = data.get("gaps") or []
    if not isinstance(gaps, list):
        gaps = []

    trace_events = list(state.get("trace_events") or [])
    trace_events.append(
        {
            "node": "evaluate",
            "event": "thought",
            "description": (
                f"Evaluated retrieved context: sufficient={sufficient}"
                + (f", gaps identified ({len(gaps)})" if not sufficient and gaps else "")
            ),
            "active": True,
        }
    )

    return {
        "sufficient": sufficient,
        "gaps": gaps,
        "trace_events": trace_events,
    }
