# Issue: MongoDB Atlas Search as Lexical Retriever (replaces local BM25)

## Meta

- **Milestone**: M4 — Search Optimization
- **Labels**: `initiative:search-optimization`, `phase:ingestion`, `type:task`, `priority:critical`, `area:mongodb`, `area:backend`
- **Depends on**: M1 (qa_pairs collection exists in MongoDB with `title_body` field)

## Problem Statement

The BM25 index grew from ~400 KB (807 synthetic docs) to **125 MB** (60K StackExchange docs). Vercel's serverless runtime cannot load it — the cold start timeout is exceeded and RAM limits are hit. **Hybrid search, the only retrieval mode with non-zero ContextualPrecision (7.99%), does not work in production.** Without a lexical search component, production users get Vector Only retrieval (ContextualPrecision = 0%).

MongoDB Atlas Search provides a managed full-text search engine over the `qa_pairs` collection. It's included in the M0 free tier, requires zero additional infrastructure, and replaces the local `bm25_index.json` + `BM25Retriever` with a single `$search` aggregation query.

## Approach

Replace `_TICKET_BM25_RETRIEVER` (reads `bm25_index.json` + builds `BM25Retriever.from_documents()` in-memory) with a MongoDB Atlas Search query. The existing `search_tickets()` function already separates vector and lexical retrieval paths — only the lexical branch changes.

### What changes

```python
# Before (local BM25 — breaks in production):
_init_bm25_retrievers()  # loads 125 MB JSON into memory
bm25_results = _TICKET_BM25_RETRIEVER.invoke(query)

# After (MongoDB Atlas Search — works everywhere):
bm25_results = await mongodb_lexical_search(query, k=5)
```

### What stays the same

- The hybrid combination logic: vector results first, then BM25 results deduplicated
- The `search_tickets()` function signature
- The `SearchMethod.HYBRID` enum value
- The API endpoints — zero breaking changes

### MongoDB Atlas Search index setup

A single search index on the `qa_pairs` collection:

```json
{
  "mappings": {
    "dynamic": false,
    "fields": {
      "title_body": {
        "type": "string",
        "analyzer": "lucene.standard"
      }
    }
  }
}
```

This can be created via the MongoDB Atlas UI or via script. The `title_body` field contains the full question text — the same content used for vector embeddings and the same content the old BM25 indexed.

### Implementation outline

```python
# api/modules/rag_unified_retriever.py

async def mongodb_lexical_search(query: str, k: int = 5) -> list[Document]:
    """Full-text search over qa_pairs using MongoDB Atlas Search."""
    collection = await get_database().get_collection("qa_pairs")
    
    pipeline = [
        {
            "$search": {
                "index": "lexical_search",
                "text": {
                    "query": query,
                    "path": "title_body"
                }
            }
        },
        {"$limit": k},
        {"$project": {"title_body": 1, "answer": 1, "ticketId": 1, "community": 1, "score": {"$meta": "searchScore"}}}
    ]
    
    docs = []
    async for doc in collection.aggregate(pipeline):
        docs.append(Document(
            page_content=doc.get("title_body", ""),
            metadata={"ticketId": doc["ticketId"], "community": doc.get("community"), ...}
        ))
    return docs
```

## Acceptance criteria

- [ ] MongoDB Atlas Search index created on `qa_pairs.title_body` (standard analyzer)
- [ ] `mongodb_lexical_search()` function replaces `_init_bm25_retrievers()` in the lexical branch of `search_tickets()`
- [ ] `search_kb_documents()` updated to use MongoDB lexical search for KB fields (or KB search deprecated — M1 already excluded KBs from evaluation scope)
- [ ] `bm25_index.json` and `BM25Retriever` references removed from codebase
- [ ] `requirements.txt` removes any BM25-specific dependencies no longer needed
- [ ] Hybrid search works in production (Vercel deployment verified)
- [ ] Existing evaluation pipeline (`run_eval.py`) unchanged — it calls the API, not the retriever directly
- [ ] Search latency measured: MongoDB Atlas Search vs local BM25 (cold start + per-query)

## References

- MongoDB Atlas Search docs: https://www.mongodb.com/docs/atlas/atlas-search/
- Current BM25 init: `api/modules/rag_unified_retriever.py` `_init_bm25_retrievers()`
- Blog documenting the problem: `documentation/markdowns/2_post_migration_eval/post_migration_eval_es.md`
