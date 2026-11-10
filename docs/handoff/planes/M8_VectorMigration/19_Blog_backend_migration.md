# Write blog: "Phase 1.8 — Migrating from Pinecone to MongoDB Atlas Vector Search"

## Meta

- **Milestone**: M8 — Vector Backend
- **Labels**: `initiative:post-migration-eval`, `phase:docs`, `type:content`, `priority:medium`, `area:blog`
- **Estimate**: 0.5 days
- **Depends on**: Issue #18 (evaluation results)

## Description

As a Technical Writer, I want to write a short blog post documenting the Pinecone → MongoDB Atlas Vector Search migration and its impact on evaluation metrics, positioned as "Phase 1.8" in the series — sitting between Phase 1 (data migration, M3) and Phase 2 (architectural improvements, M6).

### Narrative arc

1. **Why migrate**: Pinecone + OllamaEmbeddings created a local dependency (Ollama) blocking CI/CD; also paying for two infrastructure services (Pinecone + MongoDB) when MongoDB already had vector search.
2. **What changed**: Replaced Pinecone vector store + BM25Retriever + custom RRF with MongoDB `$vectorSearch` + Atlas Search `$search` + `$rankFusion`. Replaced `all-minilm:22m` (384-dim) with `voyage-4-lite` (1024-dim).
3. **The delta**: M2 baseline (Pinecone) vs M5 re-evaluation (Mongo) — side by side.
4. **Cost impact**: Pinecone free tier eliminated entirely; Voyage AI free tier covers the project; no local Ollama needed.
5. **CI/CD unlocked**: The migration removes local Ollama dependency, enabling the planned automated evaluation pipeline (M9, future).

### Acceptance Criteria

- [ ] Blog post created as `blog_part4_backend_migration.md` in repo root.
- [ ] Comparative table from Issue #18 included.
- [ ] Cost comparison table: Pinecone free vs MongoDB free + Voyage AI free (both $0).
- [ ] Technical migration details: `autoEmbed`, `$rankFusion`, `$vectorSearch` aggregation stage.
- [ ] Tone: honest about migration effort (6-8 files changed) and trade-offs (latency increase for auto-embedding vs simplicity gain).
- [ ] Commit with message `docs(blog): add Phase 1.8 - Pinecone to MongoDB migration`.

### References

- Evaluation results (Issue #18): [`plans/M5_VectorMigration/18_Reeval_DeepEval_on_Mongo.md`](./18_Reeval_DeepEval_on_Mongo.md)
- M5 implementation: [`plans/M5_VectorMigration/`](../M5_VectorMigration/)
- Base plan: [`RAG_DATASET_MIGRATION_PLAN.md`](../../RAG_DATASET_MIGRATION_PLAN.md)

### Notes

- This blog is shorter than the main Part 1 rewrite (~300-500 words vs 1500+).
- Position it as a "technical note" in the series, not a full blog entry.
- The cost story is compelling: "went from two free-tier services to one free-tier service, and unlocked CI/CD in the process."
- If the evaluation shows regression in some metrics, be honest about it — the CI/CD unlock may be worth the regression, and M6 will recover it.
