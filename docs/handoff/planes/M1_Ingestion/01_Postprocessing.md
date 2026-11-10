# HU-2: Post-process the corpus for English operation

## Meta

- **Milestone**: M1 — Real Corpus Ingestion (✅ completed 2026-07-21)
- **Labels**: `initiative:rag-real-data-migration`, `phase:ingestion`, `type:story`, `priority:medium`, `area:backend`, `area:prompts`
- **Original issues**: #6, #7 (consolidated)

## Description

As an AI Engineer, I want to translate the system prompts to English and enrich the context sent to the LLM with the retrieved canonical answer, so that the system operates consistently with the English corpus and generates better-informed responses.

### Absorbed components

| Original issue | Title | Status |
|---|---|---|
| #6 | Translate HyDE prompt and KB categories to English | ✅ Completed |
| #7 | Enrich `context_retriever` with `expected_output` | ✅ Completed |

### Acceptance criteria

- [x] `hyde_ticket.md` reviewed and 100% in English
- [x] `KB_CATEGORIES` in `rag_kb_ingestor.py` with English values (for legacy namespace)
- [x] `extract_kb_category` regex with English keywords + Spanish fallback
- [x] `rag_system_prompt.md` already in English — no changes needed
- [x] `context_retriever_for_unified_search` modified to use `metadata.expected_output` when present
- [x] Legacy fallback path (actions + owner) when `expected_output` is empty
- [x] Canonical answer truncated to 600 chars to avoid context inflation
- [x] Tests: SE queries use `expected_output`; legacy queries use fallback

### References

- HyDE prompt: `api/prompts/hyde_ticket.md`
- KB ingestor: `api/modules/rag_kb_ingestor.py`
- Retriever: `api/modules/rag_unified_retriever.py`

### Referencias

- Prompt HyDE: `api/prompts/hyde_ticket.md`
- KB ingestor: `api/modules/rag_kb_ingestor.py`
- Retriever: `api/modules/rag_unified_retriever.py`
