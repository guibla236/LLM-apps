"""generate_answer node: synthesize the final answer with source citations.

The ONLY internal node that writes to ``messages``: the final answer is part
of the conversation history (what gets summarized between turns). It also
records the closing trace event.
"""
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from core.config import get_llm
from core.utils import get_prompt
from prompts.model import PromptFileNames
from agent.nodes.utils import last_human_message


async def generate_node(state):
    user_query = last_human_message(state.get("messages") or [])
    accumulated = state.get("accumulated_context") or []
    context = "\n\n".join(accumulated) if accumulated else "(no context retrieved)"
    llm = get_llm()

    response = await llm.ainvoke(
        [
            SystemMessage(content=get_prompt(PromptFileNames.GENERATE_PROMPT)),
            HumanMessage(content=f"User question:\n{user_query}\n\nRetrieved context:\n{context}"),
        ]
    )

    trace_events = list(state.get("trace_events") or [])
    trace_events.append(
        {
            "node": "generate",
            "event": "answer",
            "description": "Agent has generated a final response.",
            "active": True,
        }
    )

    return {
        "messages": [AIMessage(content=str(response.content))],
        "trace_events": trace_events,
    }
