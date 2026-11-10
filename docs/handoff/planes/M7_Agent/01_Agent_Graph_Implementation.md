# Issue: Implement Multi-Step Diagnosis Graph

## Meta

- **Milestone**: M7 — Multi-Step Diagnosis Agent
- **Labels**: `initiative:agentic-diagnosis`, `phase:ingestion`, `type:story`, `priority:high`, `area:backend`
- **Depends on**: M4 (working RAG retrieval)
- **Estimate**: 2-3 days

## Description

Replace the single-pass ReAct agent (`agent_app/backend/agent/graph.py`) with a multi-step diagnosis graph that iterates on retrieval until it has sufficient information. The new graph has 5 nodes: `analyze_query`, `search_rag`, `evaluate_sufficiency`, `refine_query`, and `generate_answer`.

### Files to modify

| File | Change |
|------|--------|
| `agent_app/backend/core/config.py` | **Prerequisite**: migrate `ChatGroq` → `ChatOpenAI` + OpenRouter (same as `api/` did in M2). `AGENT_MODEL` env var for model selection. |
| `agent_app/backend/agent/graph.py` | Replace ReAct graph with 5-node iterative graph |
| `agent_app/backend/agent/state.py` | Extend `AgentState` with `accumulated_context`, `iteration_count`, `query_history`, `sufficient`, `search_strategy` |
| `agent_app/backend/agent/nodes/` | Add `analyze.py`, `evaluate.py`, `refine.py`, `generate.py`; keep `search.py` (reuse existing tool) |
| `agent_app/backend/tools/advanced_search.py` | Ensure search tool accepts `search_method` param (`vector_only` / `hybrid`) and returns structured results with `ticketId` for citation |
| `agent_app/backend/prompts/` | System prompt updated for multi-step diagnosis persona |

### Node design

#### analyze_query
- Prompt: classify query type, extract key entities (OS, hardware, error codes), suggest initial search strategy
- **Search strategy routing**: regex signals for lexical-heavy queries (error codes `0x[0-9a-f]+`, command names, version patterns) → `hybrid`; otherwise `vector_only` (M4 winner)
- Output: structured analysis + first search query + `search_strategy`

#### search_rag (reuses existing `advanced_search_tool`)
- Calls `POST /api/raw_unified_search` with the current query
- Appends results to `accumulated_context` (deduplicated by `ticketId`)

#### evaluate_sufficiency
- Prompt: given accumulated context, can we answer the user's question fully?
- Output: `{sufficient: bool, gaps: list[str], confidence: 0-1}`
- If sufficient OR iteration_count >= max_iterations: route to generate
- If insufficient: route to refine

#### refine_query
- Prompt: given original query + accumulated context + identified gaps, reformulate a more specific search query
- Examples: "Windows 11 impresora no funciona" → "HP LaserJet P1102w driver error Windows 11 23H2"
- Output: refined query string

#### generate_answer
- Prompt: synthesize answer from all accumulated context, cite sources by ticketId
- Output: final answer with citations

### Acceptance criteria

- [ ] `agent_app` migrated from Groq to OpenRouter (`ChatOpenAI` + OpenRouter base URL, `AGENT_MODEL` env var)
- [ ] Graph compiled with 5 nodes: analyze → search → evaluate → [refine → search]* → generate
- [ ] Hard stop at 3 iterations
- [ ] `accumulated_context` deduplicated by `ticketId`
- [ ] Generated answers include source citations (ticketId references)
- [ ] `analyze_query` routes search strategy: `vector_only` default, `hybrid` when lexical-heavy signals detected (regex: error codes, commands, versions)
- [ ] `advanced_search_tool` accepts and honors `search_method` param
- [ ] Existing ReAct agent preserved behind feature flag `use_legacy_agent`
- [ ] Agent works with existing Streamlit frontend (unchanged)
- [ ] Endpoint `/chat/` unchanged — same request/response schema
- [ ] Model per node configurable via env var (`AGENT_MODEL`) — actual per-node splitting conditional on M6 results

## References

- Current graph: `agent_app/backend/agent/graph.py`
- Current tools: `agent_app/backend/tools/advanced_search.py`
- System prompt: `agent_app/backend/prompts/system_prompt.md`
- Overview: `plans/M7_Agent/00_Agent_Overview.md`
