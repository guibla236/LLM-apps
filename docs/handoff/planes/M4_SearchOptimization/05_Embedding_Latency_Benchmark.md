# Embedding Latency Benchmark — Results

## Meta

- **Milestone**: M4 — Search Optimization
- **Initiative**: `initiative:search-optimization`
- **Date**: 2026-08-02
- **Artifact**: `evaluation_notebooks/raw_results/embedding_latency_20260802_195723.json`
- **Script**: `api/scripts/benchmark_embeddings.py` (persists JSON automatically, `--output-dir` configurable)

## Context

M4 replaces the local Ollama embedding model (`all-minilm:22m`, 384-dim) with OpenRouter-hosted `voyage-4-lite` (1024-dim). This benchmark quantifies the latency trade-off: per-query latency increases (network round-trip), but batch ingestion throughput improves (Ollama local serializes; the API parallelizes).

## Results (2026-08-02, 10 StackExchange-style technical samples)

| Provider | mean/call | min | max | batch total | per doc |
|----------|----------:|----:|----:|------------:|--------:|
| Ollama local (`all-minilm:22m`) | 164ms | 137ms | 252ms | 1568ms | 157ms |
| OpenRouter (`voyage-4-lite`) | 290ms | 263ms | 383ms | 343ms | **34ms** |

## Interpretation

- **Per-call latency**: OpenRouter is ~77% slower per single call (290ms vs 164ms) — the expected network round-trip cost. Impact on the support system UX: ~+125ms per query, acceptable.
- **Batch throughput**: OpenRouter is **4.6× faster per document** (34ms vs 157ms) — the API processes the 10-doc batch in 343ms vs Ollama's 1568ms. For the ~60K-doc ingestion, this confirms the prediction in `00_Search_Optimization_Overview.md`: **ingestion with the API is significantly faster than local Ollama**, despite the per-call penalty.
- The batch advantage comes from Ollama's serial processing of `embed_documents` vs the API's native batch handling.

## Caveats

- Measurements include warm-up; cold-start (model load / connection pool) is excluded.
- Numbers depend on local hardware (Ollama) and network conditions (API) — re-run the script to reproduce.
- 5-sample run earlier the same day (2026-08-02, 5 samples): Ollama 237ms/call (batch 196ms/doc), OpenRouter 293ms/call (batch 74ms/doc). Same qualitative conclusion.

## Files

- `api/scripts/benchmark_embeddings.py` — benchmark script (persists JSON results automatically)
- `evaluation_notebooks/raw_results/embedding_latency_*.json` — raw persisted results (timestamped)
- This file — human-readable summary (tracked in plans repo)
