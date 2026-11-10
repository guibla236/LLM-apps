# Re-run DeepEval baseline on the new MongoDB backend

## Meta

- **Milestone**: M8 — Vector Backend
- **Labels**: `initiative:post-migration-eval`, `phase:eval`, `type:research`, `priority:high`, `area:notebooks`, `area:mongodb`
- **Estimate**: 1 day
- **Depends on**: M4 complete (Mongo backend operational)

## Description

As an AI Engineer, I want to re-run the complete DeepEval evaluation pipeline (established in M2) on the new MongoDB Atlas Vector Search backend to measure the delta introduced by the vector backend migration — establishing a new baseline for M6 (Architectural Improvements) and M8 (Hybrid Inference) to build on.

### Why re-evaluate

M2 established a clean baseline on Pinecone + OllamaEmbeddings (`all-minilm:22m`, 384-dim). M4 replaces the backend with MongoDB + Voyage AI (`voyage-4-lite`, 1024-dim). This changes:
- **Embedding model**: 22M params → proprietary model, quality difference expected
- **Vector dimensionality**: 384 → 1024 (richer representations)
- **ANN engine**: Pinecone HNSW → MongoDB HNSW (may have different recall behavior)
- **Hybrid search**: BM25Retriever + custom RRF → MongoDB `$rankFusion` native

These are enough changes that the M2 baseline is no longer valid for measuring M6 improvements against. A new baseline on the Mongo backend is needed.

### What to measure

Re-run the exact same configuration as M2:
- Same 4 scenarios (Vector Only, Hybrid, Hybrid+RRF+Semantic, Hybrid+RRF+Markdown)
- Same 200 golden QA pairs (Issues #9)
- Same DeepEval metrics (Correctness, Faithfulness, ContextualPrecision, ContextualRecall, AnswerRelevancy)
- Same judge model (llama-4-scout-17b via Groq)
- Same notebook `rag_experiments_evaluator.ipynb`, only changing the endpoint target

### Acceptance Criteria

- [ ] Notebook `local_evaluation_pipeline/rag_experiments_evaluator.ipynb` re-run pointing at the new MongoDB backend.
- [ ] 4 scenarios × 200 questions = 800 evaluations complete without errors.
- [ ] Results CSV saved as `evaluation_notebooks/raw_results/eval_mongo_baseline_<timestamp>.csv`.
- [ ] Comparative table: `metric | M2 (Pinecone) | M5 (Mongo) | delta`.
- [ ] At least 3 meaningful metrics show improvement (same or better) — if ContextualPrecision drops by more than 5 pts, flag as regression.
- [ ] If regression detected: document possible causes (Voyage model, MongoDB ANN config, `$rankFusion` behavior).
- [ ] Commit with message `research(eval): re-run DeepEval baseline on MongoDB backend`.

### Expected comparison table

```markdown
| Metric | M2 (Pinecone + all-minilm) | M5 (Mongo + voyage-4-lite) | Δ |
|--------|---------------------------:|---------------------------:|---:|
| Correctness | 22% | ?% | ? |
| Faithfulness | 84% | ?% | ? |
| ContextualPrecision | 10% | ?% | ? |
| ContextualRecall | 10% | ?% | ? |
| AnswerRelevancy | 56% | ?% | ? |
```

### References

- M2 evaluation setup: [`plans/M2_Evaluation/10_Extender_matrix_escenarios.md`](../M2_Evaluation/10_Extender_matrix_escenarios.md)
- M5 migration: [`plans/M5_VectorMigration/`](../M5_VectorMigration/)
- Evaluation notebook: [`local_evaluation_pipeline/rag_experiments_evaluator.ipynb`](../../local_evaluation_pipeline/rag_experiments_evaluator.ipynb)
- Base plan: [`RAG_DATASET_MIGRATION_PLAN.md`](../../RAG_DATASET_MIGRATION_PLAN.md)

### Notes

- The endpoint should be the **deployed** API (Vercel) or local instance pointing to MongoDB. Not to Pinecone (which should be disconnected at this point).
- The scenario definitions (chunking, RRF, namespaces) may need adjustment if M4 changed the API schema — update `query_rag_and_context` accordingly.
- The notion of "namespace" no longer exists in MongoDB (removed in M4). The 4 scenarios may need to be reinterpreted: e.g., "Semantic Chunking" vs "Markdown Headers" becomes a metadata filter in Mongo.
- This evaluation feeds directly into the M5 blog post (Issue #19).
