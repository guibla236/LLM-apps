# Replace `embeddings_model` and `vector_store_instance` with MongoDB Atlas + Voyage AI

## Meta

- **Milestone**: M8 — Vector Backend Migration (Pinecone → MongoDB + Voyage AI)
- **Labels**: `initiative:vector-backend-migration`, `phase:ingestion`, `type:refactor`, `priority:high`, `area:backend`, `area:mongodb`
- **Estimate**: 1 day
- **Depends on**: Issue #21 (spike decision: proceed)

## Description

As an AI Engineer, I want to replace `OllamaEmbeddings` and `PineconeVectorStore` with MongoDB Atlas Vector Search (auto-embedding via `voyage-4-lite`), eliminating all Pinecone dependencies and the local Ollama requirement, so that the system runs entirely on cloud-hosted services and is CI/CD-friendly.

### What gets removed

| Component | File | Status |
|-----------|------|--------|
| `OllamaEmbeddings` import + instance | `api/modules/third_party_clients.py` | **Deleted** |
| `Pinecone` client + `pinecone_client` | `api/modules/third_party_clients.py` | **Deleted** |
| `PineconeVectorStore` import + instances | `api/modules/third_party_clients.py` | **Deleted** |
| `get_pinecone_index()` | `api/modules/third_party_clients.py` | **Deleted** |
| `get_kb_pinecone_index()` | `api/modules/third_party_clients.py` | **Deleted** |
| `vector_store_instance` | `api/modules/third_party_clients.py` | **Replaced** by MongoDB Atlas Vector Search |
| `kb_vector_store_instance` | `api/modules/third_party_clients.py` | **Replaced** by MongoDB Atlas Vector Search |
| `get_kb_vector_store()` | `api/modules/third_party_clients.py` | **Replaced** |
| `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `PINECONE_KB_INDEX_NAME` | `.env` | **Deleted** |
| `langchain-pinecone` | `requirements.txt` | **Removed** |
| `langchain-ollama` | `requirements.txt` | **Removed** (or kept only for local dev experiments) |

### What gets added

| Component | File | Status |
|-----------|------|--------|
| `MongoDBAtlasVectorSearch` (LangChain integration) | `api/modules/third_party_clients.py` | **New** |
| Vector Search index on `qa_pairs.title_body` | MongoDB Atlas | **New** — created via Atlas UI or `pymongo` script |
| Vector Search index on `kb_docs.content` | MongoDB Atlas | **New** — for KB documents |
| `VOYAGE_API_KEY` | `.env` | **New** (only if manual embedding; with `autoEmbed`, MongoDB handles the key internally) |

### New `third_party_clients.py` (key excerpt)

```python
from langchain_mongodb import MongoDBAtlasVectorSearch
from .database import get_database

# Vector store for tickets/QA pairs
def get_vector_store(collection_name: str = "qa_pairs", index_name: str = "vector_index"):
    """Returns a LangChain MongoDB Atlas Vector Search store."""
    db = get_database()
    return MongoDBAtlasVectorSearch(
        collection=db[collection_name],
        embedding=None,  # autoEmbed handles embeddings server-side
        index_name=index_name,
        relevance_score_fn="cosine",
        text_key="title_body",
    )

vector_store_instance = get_vector_store("qa_pairs", "qa_pairs_vector_index")
kb_vector_store_instance = get_vector_store("kb_docs", "kb_docs_vector_index")
```

### Acceptance Criteria

- [ ] `OllamaEmbeddings` and all Pinecone references removed from `api/modules/third_party_clients.py`.
- [ ] `MongoDBAtlasVectorSearch` used as replacement for both `vector_store_instance` and `kb_vector_store_instance`.
- [ ] `langchain-pinecone` and `langchain-ollama` removed from `requirements.txt` (or moved to `requirements-dev.txt`).
- [ ] `langchain-mongodb` added to `requirements.txt`.
- [ ] Environment variables `PINECONE_*` removed from `.env.example`.
- [ ] Environment variable `VOYAGE_API_KEY` NOT needed (autoEmbed manages it in Atlas UI) — document this.
- [ ] Vector Search indexes created in Atlas UI for `qa_pairs` and `kb_docs` collections.
- [ ] Existing tests in `api/tests/` updated to mock MongoDB instead of Pinecone (if any Pinecone-specific tests exist).
- [ ] Manual test: `python -c "from modules.third_party_clients import vector_store_instance; print(vector_store_instance)"` works without Pinecone or Ollama installed.
- [ ] Commit with message `refactor(api): replace Pinecone+Ollama with MongoDB Atlas Vector Search + Voyage AI`.

### References

- Spike result (Issue #21): `evaluation_notebooks/spike_mongo_voyage_poc.ipynb`
- LangChain MongoDB integration: https://python.langchain.com/docs/integrations/vectorstores/mongodb_atlas/
- Current file to modify: [`api/modules/third_party_clients.py`](../../api/modules/third_party_clients.py)
- Database module: [`api/modules/database.py`](../../api/modules/database.py)
- Base plan: [`RAG_DATASET_MIGRATION_PLAN.md`](../../RAG_DATASET_MIGRATION_PLAN.md)

### Notes

- With `autoEmbed`, MongoDB generates embeddings **server-side** using Voyage AI. Your Python code never calls the embedding model directly — it just inserts documents with text and queries with text.
- This means `embeddings_model` variable disappears entirely from `third_party_clients.py`.
- The `MongoDBAtlasVectorSearch` LangChain integration supports `similarity_search(query, k=5)` with text input — LangChain passes the text to Mongo, which calls Voyage internally via the `autoEmbed` index.
- If the LangChain integration doesn't fully support `autoEmbed` (text-in, text-out), you may need to use `pymongo` directly with `$vectorSearch` aggregation pipeline. The spike (Issue #21) should clarify this.