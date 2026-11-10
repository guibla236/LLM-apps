# Embedding comparison: Voyage AI models (`voyage-4-lite` vs `voyage-4` vs `voyage-4-large`) — DEFERRED to M9

## Meta

- **Status**: ⏸️ **Deferred to milestone M9**
- **Original Milestone**: M2 — Golden QA & Re-evaluation
- **Deferred to**: M9 — Architectural Improvements (Phase 2)
- **Labels**: `initiative:architectural-improvements`, `phase:eval`, `type:research`, `priority:medium`, `area:mongodb`, `area:notebooks`
- **Estimate**: 1-2 days
- **Depends on**: M8 (Vector Backend Migration — Mongo backend operational), M5 (CI/CD pipeline)

## Description

As an AI Engineer, I want to compare Voyage AI embedding models on the MongoDB Atlas backend to determine which tier provides the best cost-performance trade-off for our RAG system, now that the Pinecone + Ollama stack has been replaced.

### Why This Changed From The Original Plan

The original plan called for comparing `all-minilm:22m` vs `bge-small-en-v1.5` on Pinecone. With M4 (Vector Backend Migration), the entire embedding stack changed: Pinecone → MongoDB Atlas, OllamaEmbeddings → Voyage AI autoEmbed. The models to compare are now Voyage's tiers, all available via the same `autoEmbed` index mechanism.

### Models to Compare

| Model | Dims | Cost per 1M tokens | MTEB ranking | Notes |
|-------|------|-------------------|-------------|-------|
| `voyage-4-lite` (current) | 1024 | $0.02 | Lower | Default for M4 migration |
| `voyage-4` | 1024 | $0.06 | SOTA | Better general-purpose retrieval |
| `voyage-4-large` | 1024 | $0.12 | Best | Best quality, 2x cost |

All three share the same dimensional space (1024-dim) and are compatible with each other — embeddings from different models can coexist in the same index.

### Methodology

1. **Ingest** the corpus three times, once per model, into separate MongoDB collections (`qa_pairs_v4lite`, `qa_pairs_v4`, `qa_pairs_v4large`). Each collection has its own `autoEmbed` index with the respective model.
2. **Run the DeepEval pipeline** via the M5 CI/CD against each collection.
3. **Measure**: Correctness, Faithfulness, ContextualPrecision, latency, cost.
4. **Decision matrix**: choose the model that maximizes (quality - cost) for our corpus.

### Key Trade-off

| Model | Cost/mo (est.) | When to choose |
|-------|---------------|----------------|
| `voyage-4-lite` | $0 | Sufficient quality, zero cost (within 200M free tokens) |
| `voyage-4` | ~$3.60/mo | If ContextualPrecision improves >5 pts over lite |
| `voyage-4-large` | ~$7.20/mo | Only if quality-critical and small delta justifies 2× cost |

### Acceptance Criteria

- [ ] Three MongoDB collections created with `autoEmbed` indexes for each model.
- [ ] The corpus ingested once per model.
- [ ] DeepEval run against each collection via CI/CD pipeline.
- [ ] Comparative table: `model | Correctness | Faithfulness | ContextualPrecision | Latency | Cost/1K queries`.
- [ ] Data-driven decision documented: keep `voyage-4-lite`, upgrade to `voyage-4`, or upgrade to `voyage-4-large`.
- [ ] Blog post section or notebook documenting the trade-off analysis.
- [ ] Commit with message `research(eval): compare Voyage AI embedding tiers on MongoDB backend`.

### References

- Voyage AI pricing: https://docs.voyageai.com/pricing/
- M5 Vector Migration: [`plans/M5_VectorMigration/`](../M5_VectorMigration/)
- Base plan: [`RAG_DATASET_MIGRATION_PLAN.md`](../../RAG_DATASET_MIGRATION_PLAN.md)

### Notes

- The 200M free tokens from Voyage AI cover the entire project. This comparison costs $0 in tokens for the first run.
- MongoDB `autoEmbed` charges are based on tokens consumed by Voyage AI, not on MongoDB reads. Monitor in Atlas UI.
- If the quality difference between `voyage-4-lite` and `voyage-4` is negligible (<3 pts in any metric), stay with `voyage-4-lite` and document the decision. Results showing otherwise would justify an upgrade.
