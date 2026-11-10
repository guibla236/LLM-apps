# Issue: Evaluate & Select Best Embedding + Chunking Combo

## Meta

- **Milestone**: M4 — Search Optimization
- **Labels**: `initiative:search-optimization`, `phase:eval`, `type:task`, `priority:high`, `area:notebooks`
- **Depends on**: M4 issue 02 (embeddings integration)

## Description

After ingesting 3 chunking variants with `voyage-4-lite`, run the standardized DeepEval pipeline (`run_eval.py`) against each and produce a comparative analysis that determines which combination to deploy as the new production baseline. Extend to `qwen3-embedding-8b` only if voyage results are inconclusive.

## Experiment plan

### Phase 1: Chunking ablation (voyage-4-lite, all 3 variants)

| Run | Embedding | Chunking | Scenario name |
|-----|-----------|----------|---------------|
| R1 | voyage-4-lite | No chunking | `voyage4lite_nochunk` |
| R2 | voyage-4-lite | Baseline (1000/100) | `voyage4lite_baseline` |
| R3 | voyage-4-lite | Larger (2000/200) | `voyage4lite_larger` |

Each run: **50 golden QA pairs × 1 scenario (vector_only) = 50 evaluations** — hybrid is NOT run per variant (decision 2026-08-03: it confounds the embedding/chunking effect and doubles cost/time). Hybrid runs **only once, with the winning combo**, to compare against the corrected M2 hybrid baseline (31.88% CP).
**Cost**: 3 × $0.84 = $2.52 (ingestion) + ~$0.15 (evaluation, vector_only only)

### Metrics per phase (decision 2026-08-03)

M4 optimizes the **retriever**, so the metrics that answer the research question are the retrieval ones — ContextualPrecision and ContextualRecall. Generation metrics (Correctness, Faithfulness, AnswerRelevancy) depend on the generator LLM, not on embeddings/chunking, and only add cost/time.

| Phase | Metrics | Rationale |
|-------|---------|-----------|
| **P0 (no-chunk)** | All 5 | First variant — full comparison against the corrected M2 baseline (which has all 5) |
| **P1, P2 (chunking variants)** | **CP + CR only** (`--metrics contextual_precision contextual_recall`) | They measure the semantic search — M4's goal. ~60% cheaper/faster per run |
| **Hybrid of the winner** | All 5 | Final comparison against the corrected M2 hybrid baseline (31.88% CP) |

This mirrors the M6 decision (ROADMAP: "ContextualPrecision/Recall excluded — retriever is fixed"): when the retriever is the variable, CP/CR are the metrics; when it's fixed, they're redundant.

### Phase 2: Alternative model (only if needed)

**DECISION 2026-08-04: Phase 2 (qwen3-embedding-8b, P3) is CANCELLED** — and P2 (chunk 2000/200) is also dropped:

1. **Pinecone write-unit budget**: ~1.5M/2M used (ingestions + metadata backfill). P3 at 4096d would cost ~1.6M units (4× per-vector) — impossible. P2 would cost ~400K — too risky.
2. **Evidence**: P0 and P1 already answer the research question (voyage-4-lite > all-minilm by a wide margin). No signal that the embedding model is the bottleneck.
3. **Higher-value lever**: context expansion (below) improves generation metrics without any ingestion cost.

### Context expansion (decision 2026-08-04)

**Problem**: chunking (P1) improves CP but hurts CR — the LLM only sees the matched chunk (±500 chars), losing document context.

**Solution** (implemented in `rag_unified_retriever.py`):
- **Question**: expand the matched chunk to a window of ±1000 chars of the full `title_body` (max 3000 chars), fetched from MongoDB by `ticketId` (1 batch query per request).
- **Answer**: `expected_output` lengthened from 500 → 1000 chars (full `upvoted_answer` from MongoDB, truncated).
- **Zero write units**: no re-ingestion — code-only change.
- **Corpus data**: `title_body` avg 762 / max 4171 chars; `upvoted_answer` avg 766 / max 30141 chars. With k=10: avg prompt ~4.5K tokens, worst case ~18K — well within any judge window.
- **Expected**: CR ↑ toward P0's 26.66% without sacrificing P1's CP 45.33%. Note: CP/CR measure retrieval (unchanged) — the real impact is on generation metrics (Correctness/Faithfulness).

### Judge model (decision 2026-08-04)

**Problem**: judge == generator (`deepseek/deepseek-v4-flash`) → self-evaluation bias (flagged since M2).

**Decision**: final runs use **`openai/gpt-5.6-luna`** (OpenAI family ≠ DeepSeek generator, 50% off promo: $0.10/M in, $0.60/M out, 1.05M context). Cost of 2 final runs (5 metrics vector_only + hybrid): ~$0.7-0.9.

### M4 closure (decision 2026-08-04)

Once the winner is chosen (P0 / P1 / P1+expansion):

1. **5 metrics of the winner (vector_only)** with gpt-5.6-luna — full table for production release.
2. **Hybrid of the winner (5 metrics)** with gpt-5.6-luna — vs corrected M2 hybrid baseline (31.88% CP).
3. Document results; declare M4 done when BM25 moves to MongoDB Atlas (issue 04).

**No re-ingestion of the winner is needed** — experiment indexes (`tickets-m4-exp-a`/`-b`) already hold the vectors; deployment = pointing `PINECONE_INDEX_NAME` at the winner's index (0 write units).

### Success criteria (in priority order, vs corrected 2026-08-03 baseline)

1. **ContextualPrecision > 40%** (from corrected baseline 31.88% Hybrid) — primary target; the old >20% was set against the broken near-zero baseline
2. **ContextualRecall > 25%** (from 17.15%) — secondary
3. **Correctness maintained or improved** (from 36.00%) — tertiary
4. **Faithfulness > 95%** (from 98.47%) — must hold

### Results so far (2026-08-04)

| Experiment | CP | CR | Notes |
|------------|----|----|-------|
| M2 baseline vector_only (all-minilm) | 29.37% | 13.86% | corrected baseline |
| **P0** voyage-4-lite no-chunk | 39.70% | **26.66%** | CR ✅ target (>25%), CP near-miss (40% target) |
| **P1** voyage-4-lite chunk 1000/100 | **45.33%** | 21.22% | CP ✅ target (>40%), CR below |
| P1 + context expansion | 33.80% | 25.19% | ❌ **REJECTED** — CP dropped -11.5pts (window dilutes precision); CR gain (+4pts) not worth it |

**Trade-off**: chunking ↑ CP (45.33 vs 39.70) but ↓ CR (21.22 vs 26.66). Both vastly beat the M2 baseline.

**WINNER (2026-08-04): P1 — voyage-4-lite chunk 1000/100 (no context expansion).** Only variant meeting the primary target (CP > 40%). Context expansion is documented as a failed experiment (dilutes CP more than it gains CR).

### Final results — gpt-5.6-luna judge (2026-08-04)

| Metric | P1 vector_only (luna) | P1 hybrid (luna) | Δ hybrid−vector |
|--------|:---:|:---:|:---:|
| Correctness | **51.00%** | 49.80% | −1.20 |
| Faithfulness | **98.38%** | 98.05% | −0.33 |
| AnswerRelevancy | 95.86% | **95.94%** | +0.08 |
| ContextualPrecision | 69.40% | **69.65%** | +0.25 |
| ContextualRecall | **25.91%** | 23.19% | **−2.72** |

**KEY FINDING — hybrid no longer helps with voyage-4-lite**: the lexical branch (MongoDB Atlas Search) adds ~nothing to CP (+0.25) and *hurts* CR (−2.72). With a strong dense model on a homogeneous corpus, sparse and dense overlap — the naive 50/50 merge gives the lexical side more weight than it deserves (Weaviate's default alpha is 0.75 vector). In M2 (all-minilm), hybrid was *essential* (vector-only was 0%); with voyage-4-lite, **vector_only is the better default**. Hybrid may still help for lexical-heavy queries (error codes, command names) — see M7 agent routing note.

**Recommended production config**: `vector_only` default; keep hybrid available for lexical-heavy queries (M7 agent can route).

### Comparative analysis format

```markdown
| Experiment | Embedding | Chunking | Correctness | Faithfulness | AnswerRel | CtxPrecision | CtxRecall |
|------------|-----------|----------|:-----------:|:------------:|:---------:|:------------:|:---------:|
| M2 baseline (corrected) | all-minilm:22m (384d) | chunk_1000 | 36.00% | 98.47% | 94.76% | 31.88% | 17.15% |
| M2 baseline vector_only | all-minilm:22m (384d) | chunk_1000 | 24.00% | 90.10% | 94.57% | 29.37% | 13.86% |
| **P0** (vector_only, deepseek judge) | voyage-4-lite (1024d) | no_chunk | 28.40% | 97.32% | 94.52% | 39.70% | 26.66% |
| **P1 WINNER vector_only** (luna judge) | voyage-4-lite (1024d) | chunk_1000 | **51.00%** | **98.38%** | 95.86% | **69.40%** | **25.91%** |
| **P1 WINNER hybrid** (luna judge) | voyage-4-lite (1024d) | chunk_1000 | 49.80% | 98.05% | **95.94%** | **69.65%** | 23.19% |
```

*Note: M2 baseline used deepseek-v4-flash as judge; final P1 runs use gpt-5.6-luna — cross-judge comparison is directional, not exact.*

### Debugging if results are unexpectedly poor

If ContextualPrecision remains < 10% even with voyage-4-lite:

1. **Verify ingestion**: spot-check 5-10 golden questions manually against Pinecone
2. **Check dimensionality mismatch**: Pinecone index must accept 1024-dim vectors
3. **Check retrieval code**: confirm `search_tickets` is querying the correct namespace
4. **Test with golden IDs INCLUDED**: temporarily ingest 5 golden pairs and verify they're retrieved for their own questions (sanity check)
5. **Check OpenRouter rate limiting**: embedding API may throttle

## Acceptance criteria

- [ ] All 3 (or 4) experiments executed and CSV files saved to `evaluation_notebooks/raw_results/`
- [ ] JSON aggregates computed for each experiment
- [ ] Comparative table produced with M2 baseline as control
- [ ] Clear winner identified with documented rationale
- [ ] Winner deployed to production `kb-se-all` namespace
- [ ] `M4_results.md` committed with full analysis
- [ ] If no variant reaches success criteria, root cause analysis documented
