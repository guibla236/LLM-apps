# HU-4: Realign HyDE prompt from ticket generation to query reformulation

## Meta

- **Milestone**: M1 — Real Corpus Ingestion
- **Labels**: `initiative:rag-real-data-migration`, `phase:ingestion`, `type:story`, `priority:medium`, `area:backend`, `area:prompts`
- **Original issues**: TBD

## Description

As an AI Engineer, I want to adapt the HyDE (Hypothetical Document Embeddings) prompt from generating a synthetic IT support ticket to generating a technical query reformulation, so that the expanded query is semantically closer to the StackExchange Q&A content in the vector index and improves retrieval precision.

The current HyDE prompt (`hyde_ticket.md`) instructs the LLM to produce a JSON-formatted hypothetical support ticket with fields like `ticketId`, `priority`, `impact`, `root_cause`, and `actions`. This ticket structure was designed for a synthetic IT support corpus where tickets contained diagnostic workflows and resolution steps. The StackExchange corpus contains **technical questions with direct answers** — a fundamentally different content shape.

A query reformulation approach (expanding the user's question with technical synonyms, alternative phrasings, and domain terminology) is better aligned with the retrieval target than generating a ticket JSON that doesn't resemble any document in the index.

### Scope

| File | Change |
|---|---|
| `api/prompts/hyde_ticket.md` | Replace ticket JSON generation with query reformulation |
| `api/modules/rag_unified_retriever.py` | Update `generate_hypothetical_ticket` to use new prompt; rename to `generate_query_reformulation` |

### Acceptance criteria

- [ ] `hyde_ticket.md` rewritten: output is a reformulated technical question (1-3 sentences), not a JSON ticket
- [ ] Reformulation includes: domain synonyms, alternative phrasings, relevant technical terminology
- [ ] Prompt explicitly avoids introducing information not present in the original query (no hallucination of ticket IDs, owners, actions)
- [ ] `generate_hypothetical_ticket` renamed to `generate_query_reformulation` or aliased for backwards compatibility
- [ ] Reformulated query used as the vector search input (same pipeline position, different content shape)
- [ ] HyDE flag (`use_hyde`) toggleable for ablation testing via `run_eval.py`

### References

- Current HyDE prompt: `api/prompts/hyde_ticket.md`
- Golden QA: `evaluation_notebooks/goldens/golden_se_200.json`
- EDA: corpus consists of question title + body → upvoted answer pairs, not tickets
- Query reformulation literature: HyDE paper (Gao et al., 2022) supports this approach — the key is generating a document-like embedding, not necessarily a ticket
