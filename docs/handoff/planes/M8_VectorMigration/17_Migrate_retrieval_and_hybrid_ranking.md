# Migrate retrieval pipeline + implement native hybrid ranking with `$rankFusion`

## Meta

- **Milestone**: M8 — Vector Backend Migration (Pinecone → MongoDB + Voyage AI)
- **Labels**: `initiative:vector-backend-migration`, `phase:ingestion`, `type:refactor`, `priority:high`, `area:backend`, `area:mongodb`
- **Estimate**: 1-2 days
- **Depends on**: Issue #23 (ingestion working)

## Description

As an AI Engineer, I want to migrate the retrieval pipeline from Pinecone vector search + local BM25Retriever + custom RRF to MongoDB Atlas native Vector Search + Atlas Search full-text + `$rankFusion`, eliminating the local BM25 index file and the custom `reciprocal_rank_fusion()` function, replacing them with MongoDB's built-in hybrid search.

### Why replace BM25 + RRF with native Mongo hybrid

Our current hybrid search works like this:

```
Pinecone vector search → results
BM25Retriever (local JSON) → results
Custom RRF function → combined ranking
```

MongoDB Atlas supports **native hybrid search** by combining `$vectorSearch` with `$search` (Atlas Search full-text) and fusing results with `$rankFusion` or a custom merge pipeline:

```
$vectorSearch (Mongo Atlas) → vector results
$search (Atlas Search)     → text results
$rankFusion                → combined ranking
```

This eliminates:
- The `bm25_index.json` file (**125 MB measured on 2026-08-01** — the original plan estimated 10-15 MB; GitHub rejects files >100 MB and Vercel serverless cannot load it in runtime: `json.load` + `BM25Retriever.from_documents()` over ~60K docs exceeds the 10 s timeout and 1 GB RAM of the Hobby plan. The hybrid search effectively works only in local/dev).
- The `_TICKET_BM25_RETRIEVER` and `_KB_BM25_RETRIEVER` in-memory objects.
- The custom `reciprocal_rank_fusion()` function.
- The cold-start latency of loading BM25Retriever from JSON on Vercel serverless.

### Changes needed

#### `api/modules/rag_unified_retriever.py`

| Current | New |
|---------|-----|
| `_init_bm25_retrievers()` loads JSON file | **Deleted** — no local BM25 |
| `_TICKET_BM25_RETRIEVER` / `_KB_BM25_RETRIEVER` | **Deleted** |
| `reciprocal_rank_fusion()` | **Deleted** — use Mongo `$rankFusion` or `$merge` |
| `search_tickets()` calls Pinecone + BM25 + RRF | `search_tickets()` calls Mongo `$vectorSearch` + `$search` + `$rankFusion` |
| `search_kb_documents()` calls Pinecone + BM25 + RRF | `search_kb_documents()` calls Mongo `$vectorSearch` on `qa_pairs` collection (KB collection is deprecated — synthetic KBs not migrated) |
| `metadata_filter` dict passed to Pinecone | MQL `filter` expression in `$vectorSearch` (equivalent, more expressive) |
| `namespace` parameter | **Deleted** — replaced by `collection` selection or `source` field filter |

#### New aggregation pipeline (per query)

```python
pipeline = [
    {
        "$vectorSearch": {
            "index": "qa_pairs_vector_index",
            "path": "title_body",
            "query": user_query,  # text, not vector — autoEmbed handles it
            "numCandidates": 100,
            "limit": 10,
            "filter": {"category": {"$eq": "Cybersecurity"}}  # MQL filter
        }
    },
    {
        "$project": {
            "ticketId": 1,
            "title_body": 1,
            "upvoted_answer": 1,
            "community": 1,
            "category": 1,
            "score": {"$meta": "vectorSearchScore"}
        }
    }
]
```

For hybrid (vector + full-text + fusion):

```python
vector_pipeline = [
    {"$vectorSearch": {"index": "qa_pairs_vector_index", "path": "title_body", "query": query, "numCandidates": 100, "limit": 10}},
    {"$project": {"ticketId": 1, "title_body": 1, "upvoted_answer": 1, "score": {"$meta": "vectorSearchScore"}}}
]

text_pipeline = [
    {"$search": {"index": "qa_pairs_text_index", "text": {"query": query, "path": "title_body"}}},
    {"$limit": 10},
    {"$project": {"ticketId": 1, "title_body": 1, "upvoted_answer": 1, "score": {"$meta": "searchScore"}}}
]

# Merge with $rankFusion
pipeline = [
    {"$rankFusion": {
        "input": {
            "vector": vector_pipeline,
            "text": text_pipeline
        }
    }}
]
```

### Acceptance Criteria

- [ ] `_init_bm25_retrievers()` removed from `rag_unified_retriever.py`.
- [ ] `reciprocal_rank_fusion()` removed.
- [ ] `bm25_index.json` no longer loaded at runtime (can keep as historical artifact).
- [ ] `search_tickets()` updated to use MongoDB `$vectorSearch` aggregation pipeline.
- [ ] `search_kb_documents()` updated to use MongoDB `$vectorSearch` on `kb_docs` collection.
- [ ] `metadata_filter` parameter replaced by MQL `filter` in `$vectorSearch`.
- [ ] `namespace` parameter deprecated (no-op) for backwards compatibility.
- [ ] Hybrid search implemented with `$rankFusion` combining `$vectorSearch` + Atlas Search `$search`.
- [ ] Atlas Search text index created on `qa_pairs.title_body` (separate from the Vector Search index).
- [ ] Manual test: query "DNS server not responding" returns relevant tickets from `serverfault`/`networkengineering`.
- [ ] Manual test: MQL filter `{"category": {"$eq": "Cybersecurity"}}` correctly filters results.
- [ ] Manual test: hybrid search returns different ranking than vector-only — confirming fusion works.
- [ ] `context_retriever_for_unified_search` updated to use the new search functions.
- [ ] `augment_search_results_with_tickets_and_kbs` updated to use the new search functions.
- [ ] Commit with message `refactor(api): migrate retrieval to MongoDB Atlas native hybrid search with $rankFusion`.

### References

- Ingestion migration (Issue #16): [`plans/M5_VectorMigration/16_Migrate_ingestion_pipeline.md`](./16_Migrate_ingestion_pipeline.md)
- Current retriever: [`api/modules/rag_unified_retriever.py`](../../api/modules/rag_unified_retriever.py)
- MongoDB $rankFusion docs: https://www.mongodb.com/docs/atlas/atlas-search/rank-fusion/
- MongoDB $vectorSearch docs: https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-stage/
- Base plan: [`RAG_DATASET_MIGRATION_PLAN.md`](../../RAG_DATASET_MIGRATION_PLAN.md)

### Notes

- Atlas Search (full-text) requires a separate text index from the Vector Search index. Both can coexist on the same collection.
- `$rankFusion` is a MongoDB Atlas feature (not available in community edition). Since we're using Atlas M0 (free tier), it should be available.
- This migration effectively **absorbs the architectural improvements from M4's stash** (RRF, namespaces, metadata filters) into the native Mongo implementation. When M4 runs later, it will be about **evaluating** these features rather than implementing them from scratch.
- The `context_retriever_for_unified_search` enrichment with `expected_output` (Issue #7) stays the same — only the retrieval function changes, not the context formatting.
- If `$rankFusion` is not yet GA or has issues in M0 free tier, fall back to two separate queries (vector + text) merged with a simple Python RRF — keep `reciprocal_rank_fusion()` as a fallback.