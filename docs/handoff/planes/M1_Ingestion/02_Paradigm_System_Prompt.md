# HU-3: Realign system prompt and response format to Q&A paradigm

## Meta

- **Milestone**: M1 — Real Corpus Ingestion
- **Labels**: `initiative:rag-real-data-migration`, `phase:ingestion`, `type:story`, `priority:high`, `area:backend`, `area:prompts`
- **Original issues**: TBD

## Description

As an AI Engineer, I want to adapt the RAG generation pipeline from an IT ticket resolution paradigm (`summary` + `contacts` + `suggested_actions` in JSON) to a direct technical Q&A answering paradigm, so that the generated answers match the nature of the StackExchange corpus and can be fairly evaluated against golden answers.

The StackExchange corpus consists of technical questions paired with direct, concise answers — not structured ticket resolutions. The current prompts force the LLM to produce JSON with fields (`contacts`, `suggested_actions`) that have no equivalent in the golden answers, creating a structural mismatch between what the generator produces and what DeepEval measures.

### Scope

| File | Change |
|---|---|
| `api/prompts/rag_system_prompt.md` | Replace IT ticket resolution format with direct Q&A answering |
| `api/modules/rag_unified_retriever.py` | Adapt `augment_search_results_with_tickets_and_kbs` response parsing to new format |
| Response format | Generator returns a direct technical answer (plain text), not JSON |

### Acceptance criteria

- [ ] `rag_system_prompt.md` rewritten: role is "expert IT technical assistant", output is a direct answer to the question based on retrieved context, not a JSON ticket summary
- [ ] Removed fields that don't apply: `contacts`, `suggested_actions`, `kb_references`, `ticket_references` (or made optional/documentation-only)
- [ ] Response format: plain text answer, optionally with inlined source citations
- [ ] `augment_search_results_with_tickets_and_kbs` returns `{"answer": "..."}` instead of `{"summary": "...", "contacts": [...], ...}`
- [ ] API endpoint `/api/augment_search_results` compatible with new response shape
- [ ] Existing legacy synthetic evaluation path preserved (configurable via env var or flag) for historical comparison
- [ ] `context_retriever_for_unified_search` updated to format context as Q&A reference material, not ticket log

### References

- Current prompts: `api/prompts/rag_system_prompt.md`, `api/prompts/hyde_ticket.md`
- Golden QA: `evaluation_notebooks/goldens/golden_se_200.json` (200 pairs, direct Q&A)
- Evaluation runner: `api/scripts/run_eval.py` (expects `actual_output` vs `expected_output` as plain text)
- EDA findings: corpus is technical Q&A, not ticket resolution workflows
