# Spike: MongoDB Atlas Vector Search + Voyage AI proof-of-concept

## Meta

- **Milestone**: M8 — Vector Backend Migration (Pinecone → MongoDB + Voyage AI)
- **Labels**: `initiative:vector-backend-migration`, `phase:spike`, `type:research`, `priority:high`, `area:notebooks`, `area:mongodb`
- **Estimate**: 0.5-1 day
- **Depends on**: M0 complete (EDA decision available)

## Description

As an AI Engineer, I want to validate that MongoDB Atlas Vector Search with `autoEmbed` + `voyage-4-lite` can replace Pinecone + OllamaEmbeddings in our RAG system **before** committing to a full migration, by ingesting 100 sample pairs and benchmarking latency, retrieval quality, and developer ergonomics.

### Why a spike first

Eliminating Pinecone and Ollama touches 6-8 files in the API. Before doing that, we need to verify:
1. `autoEmbed` preview actually works as documented (it's labeled "preview" by MongoDB).
2. Latency is acceptable (queries should be < 500ms end-to-end).
3. `voyage-4-lite` produces better retrieval than `all-minilm:22m` on our corpus (sanity check, not full eval).
4. MongoDB Atlas M0 free tier (512MB) can hold the 100-pair PoC without issues.

### Scope

- Create a new MongoDB collection `spike_qa_pairs` in the existing Atlas cluster.
- Insert 100 sample pairs from the Stack Exchange corpus (sampled from devops + networkengineering — smallest communities).
- Create a Vector Search index with `autoEmbed` type, model `voyage-4-lite`, on the `title_body` field.
- Run 10 test queries and measure: embedding latency, ANN search latency, retrieval relevance (subjective).
- Compare against the same 10 queries run on Pinecone with `all-minilm:22m`.
- **Decision gate**: if latency > 500ms per query OR retrieval quality is visibly worse → abort M8, fall back to HuggingFaceEmbeddings + Pinecone.

### Acceptance Criteria

- [ ] Notebook `evaluation_notebooks/spike_mongo_voyage_poc.ipynb` created.
- [ ] 100 sample pairs inserted into `spike_qa_pairs` collection in Atlas.
- [ ] Vector Search index created with `autoEmbed` + `voyage-4-lite`.
- [ ] 10 test queries executed against MongoDB Vector Search — latency measured.
- [ ] Same 10 queries executed against Pinecone (existing index) — latency measured.
- [ ] Comparison table in the notebook: `query | mongo_latency_ms | pinecone_latency_ms | mongo_top1 | pinecone_top1`.
- [ ] Decision documented: proceed with M8 OR abort and fall back.
- [ ] If proceeding: note any caveats (rate limits, preview tags, Atlas UI quirks).
- [ ] Commit with message `research(spike): MongoDB Atlas Vector Search + Voyage AI PoC`.

### References

- MongoDB Vector Search quick start: https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-tutorial/
- Voyage AI embeddings docs: https://docs.voyageai.com/embeddings/
- Voyage AI pricing: https://docs.voyageai.com/pricing/
- Current embedding client: [`api/modules/third_party_clients.py`](../../api/modules/third_party_clients.py)
- Base plan: [`RAG_DATASET_MIGRATION_PLAN.md`](../../RAG_DATASET_MIGRATION_PLAN.md)

### Notes

- This spike uses the **existing** MongoDB Atlas cluster (the one already configured for `MONGODB_URI`). No new account needed.
- `voyage-4-lite` costs $0.02/1M tokens after the 200M free tier. 100 pairs × ~200 tokens = ~20K tokens. **Cost: $0**.
- If `autoEmbed` fails or is too flaky, try manual embedding via `voyageai.Client.embed()` as fallback within the same spike notebook.
- This spike does NOT touch production code. It's a standalone notebook.