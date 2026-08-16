"""Agent state for the multi-step diagnosis agent (M7).

Two kinds of state, deliberately separated:

* CONVERSATION MEMORY — ``messages`` (from MessagesState, reducer add_messages).
  Only user messages and the final assistant answer live here. It is
  persisted by the checkpointer and summarized by ``manage_memory`` between
  turns.

* WORKING MEMORY — the remaining fields. Transient per turn: ``analyze``
  resets them at the start of every turn, and the internal nodes
  (search/evaluate/refine) read and write them without touching ``messages``.
  Plain fields (last-write-wins) are safe here because the graph is
  sequential: each node returns the complete updated value.
"""
from typing import List

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """State for the diagnosis graph.

    Working-memory fields (reset every turn by ``analyze``):
      - accumulated_context: search results across iterations (deduped by ticketId)
      - query_history: original + refined queries
      - iteration_count / max_iterations: hard stop at 3
      - sufficient / gaps: verdict of the evaluate step
      - search_strategy: "vector_only" (default) | "hybrid"
      - trace_events: user-friendly execution trace for the UI
    """

    accumulated_context: List[str]
    query_history: List[str]
    iteration_count: int
    max_iterations: int
    sufficient: bool
    gaps: List[str]
    search_strategy: str
    trace_events: List[dict]
    