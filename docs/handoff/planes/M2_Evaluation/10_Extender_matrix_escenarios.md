# Extend scenario matrix for clean baseline evaluation

## Meta

- **Milestone**: M2 — Golden QA & Re-evaluation
- **Labels**: `initiative:rag-real-data-migration`, `phase:eval`, `type:enhancement`, `priority:high`, `area:notebooks`
- **Estimate**: 0.5 days
- **Depends on**: Issue #9 (new golden QA), Issue #4 (metadata in Pinecone)

## Description

As an AI Engineer, I want to extend the `rag_experiments_evaluator.ipynb` notebook so the existing 4 RAG scenarios run cleanly against the new real Stack Exchange corpus (200 golden QA pairs), producing a **pure data-migration delta** (synthetic vs real) without mixing in architectural improvements. Architectural enhancements (RRF, chunking strategies, metadata filtering) are intentionally deferred to milestone M4 (initiative `initiative:architectural-improvements`) to keep this initiative's narrative isolated and measurable.

### Technical Context

The current notebook (`local_evaluation_pipeline/rag_experiments_evaluator.ipynb`) defines in the "Experiment Matrix" cell:

```python
SCENARIOS = [
    {"name": "1. Baseline (Vector Only, Recursive Chunking)", ...},
    {"name": "2. Hybrid, No RRF (BM25 + Vector)", ...},
    {"name": "3. Hybrid + RRF + Semantic Chunking", ...},
    {"name": "4. Hybrid + RRF + Markdown Headers Chunking", ...}
]
```

The 4 existing scenarios are **preserved unchanged**. They were already configured to point at the synthetic-legacy Pinecone namespaces; this Issue repoints them at the new `kb-se-all` namespace (where Issue #4 ingested the real corpus) and updates `GOLDEN_DATASETS` paths to the new golden JSONs (Issue #9).

### Scope — What This Issue DOES

- Repoints the 4 existing scenarios at the real Stack Exchange corpus namespace (`kb-se-all`).
- Updates `GOLDEN_DATASETS` to the new 200-pair golden QA files.
- Resets the incremental cache (`local_benchmarking_results.json`) with previous `.bak` backup.
- Runs the full 4 scenarios × 200 questions = 800 evaluations.
- Saves the comparative CSV in `evaluation_notebooks/raw_results/` with timestamp for the synthetic-vs-real comparison table (consumed by Issue #12).

### Scope — What This Issue DOES NOT DO (explicitly deferred to M4)

| Deferred capability | Target milestone | Reason |
|---|---|---|
| Scenarios 5 and 6 with Pinecone metadata filters (`category`, `community`) | M4 (initiative `architectural-improvements`) | Requires `RawSearchRequest.metadata_filter` field that doesn't exist on `main` — adding it is itself a stashed architectural improvement (see stash register in `RAG_DATASET_MIGRATION_PLAN.md` Appendix A) |
| Comparison between `all-minilm:22m` and `bge-small-en-v1.5` embeddings | M4 | Embedding swap is orthogonal to data migration; cleaner as an independent delta |

### Acceptance Criteria

- [ ] "Experiment Matrix" cell **preserves** the 4 existing scenarios with their chunking strategy definitions.
- [ ] All 4 scenarios' `namespace` field repointed to `kb-se-all` (or `kb-se-*` variants per scenario).
- [ ] `GOLDEN_DATASETS` paths updated to `evaluation_notebooks/goldens/golden_se_200.json` (single file — Expert/Operational split was removed in Issue #9).
- [ ] Incremental cache (`local_benchmarking_results.json`) backed up with `.bak` suffix prior to reset.
- [ ] Full notebook run: 4 scenarios × 200 questions = 800 evaluations, all successful (or errors documented).
- [ ] Final visualization cell shows side-by-side comparison: synthetic-legacy baseline (referenced from prior CSV) vs real-corpus results (this run).
- [ ] Save results CSV in `evaluation_notebooks/raw_results/eval_real_corp_<timestamp>.csv`.
- [ ] Commit with message `feat(eval): run baseline scenarios against real SE corpus`.

### Success Criteria — Expected Pure Data Migration Delta

Hypothesis to validate with the 4-scenario run:

| Metric | Synthetic (legacy baseline, prior CSV) | Real (SE, this run) | Expected direction |
|--------|----------------------------------------:|--------------------:|--------------------|
| Correctness | 22% | ?% | Marker of the Golden Answer bias — should rise meaningfully |
| Faithfulness | 84% | ?% | Could drop if community answers are less rigid than synthetic |
| Contextual Precision | 10% | ?% | Real corpus has denser, better-distributed vectors — should improve |
| Contextual Recall | 10% | ?% | Same as above |
| Answer Relevancy | 56% | ?% | Harder to predict — community answers may be more conversational |

The strongest published narrative for this Issue's blog section (consumed by Issue #12) is: *"we migrated data, kept architecture constant, and measured the delta"*.

### Methodology note: golden QA exclusion from index

The 200 golden QA pairs were explicitly **excluded from the vector index** during ingestion (see Issue #4 — `--exclude-golden-ids` flag). This means the retriever can never return the exact matching document for a golden question — it must generalize to similar-but-different tickets. This is by design: it replicates the production scenario where a new ticket arrives that was never in the historical corpus.

This evaluation measures **generalization**, not auto-copier accuracy. All metrics (Correctness, Faithfulness, etc.) are computed under this constraint.

### References

- Notebook to modify: [`local_evaluation_pipeline/rag_experiments_evaluator.ipynb`](../../local_evaluation_pipeline/rag_experiments_evaluator.ipynb)
- New golden QA (Issue #9): [`plans/M2_Evaluation/09_Build_golden_QA.md`](./09_Build_golden_QA.md)
- Golden exclusion implementation (Issue #4): [`plans/M1_Ingestion/00_Ingestion.md`](../M1_Ingestion/00_Ingestion.md)
- Stashed architectural improvements deferred to M8: `RAG_DATASET_MIGRATION_PLAN.md` Appendix A
- Base plan: [`RAG_DATASET_MIGRATION_PLAN.md`](../../RAG_DATASET_MIGRATION_PLAN.md)

### Notes

- **Do NOT add new scenarios 5 or 6 in this Issue**. They belong in M8.
- **Do NOT modify the embedding model** in this Issue. That decision is also deferred to M8.
- The 4 existing scenarios must produce **non-regression comparable** numbers — the methodology must be strictly identical to the prior synthetic baseline run, only the corpus and golden dataset change.
- **Golden QA is NOT in the index** — if a scenario returns an exceptionally high score, it may indicate overfitting or leakage; investigate.
- If a scenario fails (e.g., a namespace in Pinecone doesn't exist), the fix is on the ingestion side (Issue #4), not on this Issue. Document the failure and re-run after Issue #4 is corrected.
