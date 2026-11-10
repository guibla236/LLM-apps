# Benchmark LLMs for generation quality/cost trade-off

## Meta

- **Milestone**: M6 — Cost-Optimized Hybrid Inference ✅ (completed 2026-08-16)
- **Labels**: `initiative:cost-optimized-inference`, `phase:eval`, `type:research`, `priority:high`, `area:notebooks`
- **Depends on**: M4 complete (retrieval baseline: voyage-4-lite, chunk 1000/100, CP 69.40%)
- **Scope**: Benchmark only. No model router implementation (deferred — not justified by results).

## Description

Benchmark 3 LLMs against the M4 retrieval baseline to determine the optimal generator model for the RAG pipeline. The current model (`deepseek/deepseek-v4-flash-0731`, released Jul 31) was validated empirically: it remains the production generator.

## Candidate models (Aug 4, 2026, OpenRouter)

| # | Modelo | Input $/M | Output $/M | Notas |
|---|--------|:---:|:---:|------|
| B | `deepseek/deepseek-v4-flash-0731` | $0.09 | $0.18 | 13B/284B MoE. **Baseline**. Jul 31. |
| 1 | `inclusionai/ling-2.6-flash` | **$0.01** | **$0.03** | 7.4B/104B MoE. 90% off. 9× más barato. |
| 2 | `google/gemini-3.5-flash-lite` | $0.30 | $2.50 | Google (EEUU). Jul 21. Contrapunto americano. |

## Methodology

1. Sample 75 questions from `golden_se_75_estratificado.json` (25 short ≤ P50, 25 medium P50–P75, 25 long > P75)
2. For each question, run the full RAG pipeline (M4 retrieval + generation) with each LLM
3. Evaluate with DeepEval using `openai/gpt-5.6-luna` judge — **generation-stage metrics only**: Correctness, Faithfulness, AnswerRelevancy. ContextualPrecision/Recall excluded (retriever held constant from M4).
4. Compute cost per query per model (measured via tiktoken, not estimated).
5. Produce recommendation: which model for production.

## Results (final, gpt-5.6-luna, 75 queries)

| Model | Correctness | Faithfulness | AnswerRelevancy | Gen. median | Tokens out | Cost/1K (output) |
|-------|:-----------:|:------------:|:---------------:|:-----------:|:----------:|:-----------------:|
| **deepseek-v4-flash** (baseline) | **0.465** | 0.983 | **0.956** | 11.9s | 259 | $0.047 |
| ling-2.6-flash (0.1×) | 0.412 | **0.997** | 0.788 | 5.5s | 367 | $0.011 |
| gemini-3.5-flash-lite (3.3×) | 0.161 | 0.852 | 0.628 | 2.5s | 65 | $0.173 |

### Key findings

- DeepSeek confirmed as production generator. Global advantage (5.3 pts Correctness) at the edge of judge noise (~5 pts), but clear in long-bucket (8.4 pts).
- Ling on the Pareto frontier of cost-quality — no model dominates it in both dimensions. Faithfulness 0.995-0.999 (safe against hallucination).
- Gemini sets latency standard (P95 ~3s, max 4.1s) — demonstrates deepseek's long tail is a service characteristic, not a physical limit.
- Router implementation deferred — insufficient benefit given current model cost.

## Acceptance criteria — all met ✅

- [x] 75 golden QA pairs (25 per complexity bucket) evaluated against 3 LLMs
- [x] DeepEval metrics: Correctness, Faithfulness, AnswerRelevancy
- [x] Latency and cost measured per query per model
- [x] Recommendation documented: keep deepseek
- [x] Entry 4 (ES) written with analysis. EN translation pending.

## References

- EDA bonus cell (log-normal analysis): `evaluation_notebooks/eda/eda_stackexchange_corpus.ipynb`
- Golden QA: `evaluation_notebooks/goldens/golden_se_75_estratificado.json`
- DeepEval pipeline: `api/scripts/run_eval.py`
- M6 benchmark script: `api/scripts/run_m6_benchmark.sh`
