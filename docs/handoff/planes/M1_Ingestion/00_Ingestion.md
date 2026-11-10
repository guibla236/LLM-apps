# HU-1: Ingest the real Stack Exchange corpus

## Meta

- **Milestone**: M1 — Real Corpus Ingestion (✅ completed 2026-07-21)
- **Labels**: `initiative:rag-real-data-migration`, `phase:ingestion`, `type:story`, `priority:high`, `area:backend`, `area:pinecone`, `area:mongodb`
- **Original issues**: #3, #4, #5, #8 (consolidated)

## Description

As an AI Engineer, I want to ingest the real Stack Exchange corpus into Pinecone and MongoDB, rebuild the BM25 index, and create the necessary indexes, so that the RAG system begins retrieving real data instead of synthetic.

### Absorbed components

| Original issue | Title | Status |
|---|---|---|
| #3 | Extend `TicketModel` with SE fields | ✅ Completed |
| #4 | SE ingestion script → Pinecone + MongoDB | ✅ Completed |
| #5 | Rebuild `bm25_index.json` | ✅ Completed |
| #8 | `qa_pairs` collection in MongoDB | ✅ Completed |

### Acceptance criteria

- [x] `TicketModel` extended with `expected_output` and `community` (optional fields, backwards compatible)
- [x] `ingest_stackexchange_dataset.py` created with `--dry-run`, `--resume`, `--exclude-golden-ids`, `--list-communities` flags
- [x] `run_ingest_pipeline.sh` — automated sequential pipeline with post-community verification
- [x] ~60K pairs loaded into Pinecone `kb-se-all` with `community` metadata
- [x] `bm25_index.json` rebuilt with `page_content_bm25` (title_body + answer[:500])
- [x] `qa_pairs` collection in MongoDB with `ticketId` (unique) and `community` indexes
- [x] Idempotent scripts (safe re-execution)
- [x] Golden QA IDs excluded from the vector index

### Execution results

- **MongoDB**: 60,161 documents inserted
- **Pinecone**: 81,599 vectors (pairs with automatic chunking), 0 duplicates
- **BM25 index**: ~12 MB, lazy-loaded at runtime
- **Total ingestion time**: ~2.5 hours (including Ollama rate limiting)

### References

- EDA notebook: `evaluation_notebooks/eda/eda_stackexchange_corpus_v2.ipynb`
- Scripts: `api/scripts/ingest_stackexchange_dataset.py`, `api/scripts/build_bm25_index.py`, `api/run_ingest_pipeline.sh`
- Models: `api/models/tickets.py`
- Clients: `api/modules/third_party_clients.py`
