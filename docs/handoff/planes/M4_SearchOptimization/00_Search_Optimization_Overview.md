# M4 — Search Optimization: Embedding Model & Chunking Strategy

## Meta

- **Milestone**: M4 — Search Optimization ✅ (completed 2026-08-16)
- **Initiative**: `initiative:search-optimization`
- **Depends on**: M2 (retrieval baseline: CP 29.37% vector-only / 31.88% hybrid, deepseek judge; luna: 60.33% / 64.54%)
- **Feeds**: M3 (updated blog with improved numbers), M5 (CI/CD will measure the new baseline), M6 (Hybrid Inference needs a working retriever)

## Problem Statement

M2 established that the generation pipeline works (98.47% Faithfulness, 94.76% AnswerRelevancy, deepseek judge; 98.91% / 96.77% with luna) but the retrieval pipeline is the bottleneck (31.88% ContextualPrecision hybrid / 29.37% vector_only with deepseek judge; 64.54% / 60.33% with luna). The root cause is the embedding model: `all-minilm:22m` at 384 dimensions cannot capture the semantic complexity of the StackExchange technical Q&A domain. Chunking strategy — currently `RecursiveCharacterTextSplitter(chunk_size=1000, overlap=100)` — fragments 25% of documents without semantic benefit. Additionally, the local BM25 index (125 MB) is broken in production (cannot load on Vercel).

## EDA-Driven Chunking Strategy Selection

Key findings from `eda_stackexchange_corpus_v2.ipynb`:

| Metric | Value | Implication |
|--------|-------|-------------|
| Question P75 length | 928 chars | 75% of questions fit in 1 chunk at baseline |
| Question max length | 4,199 chars | Longest doc is 4× baseline chunk size |
| Content format | Plain text Q&A | No markdown headers, no section structure → semantic/markdown chunking is invalid |
| Doc structure | Title + body → answer | Self-contained units; splitting mid-question destroys semantic intent |
| Voyage-4 token limit | 32K tokens (~120K chars) | Even the longest doc (4,199 chars) fits in a single embedding |

**Decision**: Test 3 chunking strategies. Semantic, markdown, and sentence-level chunking are excluded — the corpus structure doesn't support them.

### Why chunking matters more than model selection

The gap between `all-minilm:22m` (384-dim, 2023, MTEB ~56) and any 2025+ embedding model is massive (~30 MTEB points, 3× dimensions). The gap *between* modern models (voyage-4-lite vs qwen3-embedding-8b vs voyage-4) is marginal (~2-4 MTEB points). Therefore M4 fixes the embedding model to `voyage-4-lite` (best quality/cost ratio at $0.02/M, Matryoshka-capable) and varies chunking — the variable with the highest expected impact per EDA. A second model is only tested if no chunking variant reaches the target.

### Chunking strategies to evaluate

| # | Strategy | Config | Rationale |
|---|----------|--------|-----------|
| 1 | **No chunking** | Full `title_body` as one vector | 100% of docs fit. Zero context loss. EDA max = 4,199 chars ≪ 32K token limit. |
| 2 | **Baseline (control)** | `RecursiveCharacterTextSplitter(chunk_size=1000, overlap=100)` | Current production config. 75% in 1 chunk, 25% fragmented. |
| 3 | **Larger chunks** | `RecursiveCharacterTextSplitter(chunk_size=2000, overlap=200)` | Intermediate. Reduces fragmentation from 25% to ~5% of docs. |

### Embedding models

| Model | Provider | Dims | Cost/1M tokens | MTEB | Role |
|-------|----------|------|---------------|------|------|
| `voyage-4-lite` | OpenRouter (VoyageAI) | 1024 (Matryoshka: 256/512/2048) | $0.02 | ~65 | **Primary** — fixed for P0-P2 |
| `qwen3-embedding-8b` | OpenRouter (Qwen) | 4096 (native) | $0.01 | ~66-68 | **Fallback** — P3 only if target not met |

### Experiment matrix

| Priority | Embedding | Chunking | Est. cost | Note |
|----------|-----------|----------|-----------|------|
| **P0** ✅ | voyage-4-lite (1024d) | No chunking | $0.84 | CP 64.01% / CR 23.92% (luna, vector_only) |
| **P1** ✅ | voyage-4-lite (1024d) | Baseline (1000/100) | $0.84 | **WINNER**: CP 69.40% / CR 25.91% (luna, vector_only) |
| **P2** ❌ | voyage-4-lite (1024d) | Larger (2000/200) | — | **Cancelled 2026-08-04** (Pinecone write-unit budget) |
| P3 ❌ | qwen3-embedding-8b | Best chunking | — | **Cancelled 2026-08-04** (4096d = ~1.6M write units, impossible) |
| **P1+expansion** ✅ | voyage-4-lite (1024d) | chunk 1000/100 + context window | $0 (code only) | **Accepted**: CP 74.41% / CR 27.35% (luna, code-only change) |

**Total cost**: ~$1.7 (2 ingestions + evals — P2/P3 cancelled)
**Actual time**: ~8h (2 × 3h ingestion + 2 × 1h eval)

### Success criteria (actualized — gpt-5.6-luna judge)

- ContextualPrecision > 40% (from corrected baseline 31.88% hybrid / 60.33% vector-only luna) — **P1 hits 69.40%** ✅
- ContextualRecall > 25% (from 17.15%) — **P1 hits 25.91%** ✅
- Faithfulness and AnswerRelevancy maintained or improved — **both hold** ✅
- **WINNER: P1 (voyage-4-lite chunk 1000/100)** — CP 69.40%, CR 25.91%, C 51.00%, F 98.38%, AR 95.86%

### Results summary (final, gpt-5.6-luna)

| Variant | CP | CR | Notes |
|---------|:---:|:---:|-------|
| Baseline (all-minilm, vector_only) | 60.33% | 23.66% | Previous production config |
| Baseline (all-minilm, hybrid) | 64.54% | 22.20% | Hybrid with atlas search |
| **P0** (no-chunk, vector_only) | 64.01% | 23.92% | Embedding upgrade only |
| **P1** (1000/100, vector_only) | **69.40%** | **25.91%** | **WINNER** |
| P1 hybrid | 69.65% | 23.19% | Hybrid no longer contributes |
| P1 + expansion (code only) | 74.41% | 27.35% | Context window expansion |

**Conclusion**: No classic precision/recall trade-off — P1 improves both CP (+9.07) and CR (+2.25) simultaneously. Hybrid no longer helps on average (overlaps with strong semantic retrieval).

## What is explicitly OUT of scope

- **RRF**: Deferred to M8 — MongoDB's native `$rankFusion` in M7 makes custom RRF redundant
- **k-tuning**: Retrieving more docs won't help if none are relevant. Re-evaluate post-M4.
- **Query expansion / HyDE refinement**: Deferred to M8
- **Metadata filters**: Already invalidated by EDA (cross-community overlap)
- **MongoDB Atlas Vector Search**: That's M8. M4 uses Pinecone for vectors, MongoDB Atlas Search for lexical only.

## Production blocker: BM25 index (RESOLVED in this milestone)

The local BM25 index (`bm25_index.json`) grew from ~400 KB to **125 MB** with the real corpus. Vercel's serverless runtime cannot load it — cold start timeout exceeded, RAM limit hit. **Hybrid search does not work in production.** The only retrieval mode available to production users is Vector Only, which has 0% ContextualPrecision.

M4 resolves this via issue `04_MongoDB_Lexical_Search.md`: MongoDB Atlas Search replaces the local BM25 index. Atlas Search is included in M0 free tier, is already provisioned (the `qa_pairs` collection exists), and requires only a search index definition + ~30 lines of code change.

## Pinecone namespace management

See `plans/M4_SearchOptimization/01_Namespace_Management.md` for the rotation strategy.

## Latency impact

Switching from local `Ollama (all-minilm:22m)` to `OpenRouter API (voyage-4-lite)` introduces a network round-trip per embedding call:

| Stage | Before (Ollama local) | After (OpenRouter API) | Delta |
|-------|----------------------|------------------------|-------|
| Embedding (per doc) | ~50ms (local GPU) | ~200-500ms (network) | +150-450ms |
| Ingestion (60K docs) | ~4h (bottleneck: Ollama throughput) | ~2-3h (bottleneck: API rate limit) | Faster overall |
| Query embedding (single) | ~50ms | ~200-500ms | Slower per query |
| Pinecone search (384→1024d) | Sub-10ms | Sub-15ms | Negligible |

Ingestion is paradoxically *faster* with the API because Ollama's local throughput is the real bottleneck. Per-query latency increases by ~150-450ms — noticeable but acceptable for a support ticket system. M4 will measure and document both.

Matryoshka dimensionality (voyage-4-lite supports 256/512/1024/2048) affects Pinecone search speed linearly per dimension. In practice the difference is negligible (sub-10ms for any dimensionality below 2048). Not a decision factor.

## Definition of Done

- [ ] `voyage-4-lite` integrated into `third_party_clients.py` via OpenRouter embeddings endpoint
- [ ] Embedding model selectable via env var (`EMBEDDINGS_MODEL`), fallback to Ollama for backward compat
- [ ] Ingest script supports `--no-chunk` flag for whole-document embedding
- [ ] 3 chunking variants ingested and evaluated against golden QA (50 or 200 pairs)
- [ ] Comparative CSV: chunking × metrics
- [ ] Embedding latency measured: OpenRouter API vs local Ollama (per-call and per-batch)
- [ ] Clear recommendation documented in `M4_results.md`
- [ ] Best combo deployed as production `kb-se-all` namespace
- [ ] Baseline namespace `kb-se-all-v1-baseline` preserved for rollback
- [ ] Vector backup/export strategy documented (see `01_Namespace_Management.md`)
