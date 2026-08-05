### M2 — Pure Data Migration Delta (definitive)

**Sample**: 50 stratified pairs (9 communities, shuffled) — representative of the full golden QA.
**Golden pairs excluded from index** (generalization measure).
**Judge & generator**: `deepseek/deepseek-v4-flash` via OpenRouter.

| Scenario | Correctness | Faithfulness | AnswerRelevancy | ContextualPrecision | ContextualRecall |
|----------|:-----------:|:------------:|:---------------:|:-------------------:|:-----------------:|
| 1. Baseline (Vector Only) | 25.20% | 97.30% | 88.32% | 0.00% | 0.00% |
| 2. Hybrid (BM25 + Vector) | **25.80%** | **97.03%** | 85.52% | **7.99%** | **5.71%** |

**Notes:**
- Scenarios 3-4 unavailable — alternate chunking namespaces not created in M1.
- Golden QA pairs excluded from vector index (measures generalization).
- Sample: first 50 pairs of the shuffled `golden_se_200.json` — stratified across 9 communities (superuser 14, askubuntu 8, apple 8, android 7, devops 3, dba 2, networkengineering 2, serverfault 2, security 4).
- Both scenarios scored 50/50 questions (0 total errors; 1 null in Hybrid contextual metrics from a JSON parse retry).
- Files: `baseline_vector_only_golden_se_200_20260731_192818.csv`, `hybrid_no_rrf_golden_se_200_20260731_214733.csv`.
