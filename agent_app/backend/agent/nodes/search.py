"""search_rag node: run the search tool with the current query and strategy,
accumulate context deduplicated by ticketId.

Working memory only: results live in ``accumulated_context`` (plain field,
so the node returns the complete merged list). Nothing is written to
``messages`` — retrieved context is NOT conversation history.
"""
from tools.advanced_search import advanced_search_tool
from agent.nodes.utils import extract_ticket_ids, parse_search_blocks


def _append_trace(trace_events, description):
    events = list(trace_events or [])
    events.append(
        {"node": "search", "event": "result", "description": description, "active": True}
    )
    return events


async def search_node(state):
    query_history = state.get("query_history") or []
    current_query = query_history[-1] if query_history else ""
    strategy = state.get("search_strategy", "vector_only")

    accumulated = list(state.get("accumulated_context") or [])
    seen_ids = extract_ticket_ids("\n\n".join(accumulated))

    result_str = await advanced_search_tool.ainvoke(
        {
            "query": current_query,
            "search_type": "tickets_only",
            "search_method": strategy,
            "use_hyde": False,
        }
    )

    # Deduplicate new results by ticketId across iterations (read-modify-write)
    fresh_blocks = []
    for ticket_id, block in parse_search_blocks(str(result_str)):
        if ticket_id not in seen_ids:
            seen_ids.add(ticket_id)
            fresh_blocks.append(block)
    accumulated.extend(fresh_blocks)

    return {
        "accumulated_context": accumulated,
        "trace_events": _append_trace(
            state.get("trace_events"),
            (
                f"Searched the knowledge base ({strategy} strategy): "
                f"{len(fresh_blocks)} new results, "
                f"{len(accumulated)} total accumulated"
            ),
        ),
    }
