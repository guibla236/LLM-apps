# Build 200-pair stratified golden QA (single dataset)

## Meta

- **Milestone**: M2 — Golden QA & Re-evaluation
- **Labels**: `initiative:rag-real-data-migration`, `phase:eval`, `type:feature`, `priority:high`, `area:backend`, `area:notebooks`
- **Estimate**: 0.5 days
- **Depends on**: Issue #4 (Mongo ingestion), Issue #8 (`qa_pairs` indexes)
- **Design decision (2026-07-23)**: Merged Expert/Operational split into a single `golden_se_200.json`. The original distinction (inherited from synthetic dataset) had no data-driven basis in the StackExchange corpus — community is not a proxy for question difficulty. A single stratified 200-pair file with per-ticket community provenance is methodologically honest and simpler.

## Description

As an AI Engineer, I want to build a 200-pair question-answer evaluation dataset stratified from the `qa_pairs` MongoDB collection, so that the next DeepEval run has a statistically significant ground truth instead of the current ~20 pairs with synthetic answers.

### Technical Context

The current golden datasets are:
- `evaluation_notebooks/goldens/golden_expert.json` (synthetic, Spanish)
- `evaluation_notebooks/goldens/golden_operational.json` (synthetic, Spanish)

Both contain `{question, answer, kb}` pairs where `answer` is an LLM-generated synthetic Golden Answer (with the bias already diagnosed in blog Part 1). They are replaced by a single file `golden_se_200.json` with pairs from the real Stack Exchange corpus, where `answer` is the community-validated `upvoted_answer`.

### Why a single dataset?

The original Expert/Operational split was inherited from the synthetic golden era where it reflected a real distinction: Expert had long technical LLM-written answers, Operational had shorter answers with "Riesgo si no se aplica:" / "Punto clave:" templates. On the real StackExchange corpus, community membership is not a reliable proxy for question difficulty (a superuser question about kernel panic is more technical than a dba question about SELECT syntax). Stratifying by community and preserving community provenance in `ticketId` is sufficient for evaluation.

### Proposed Stratification (200 pairs)

| Community | Pairs | IT Category |
|-----------|------:|-------------|
| superuser | 50 | Hardware & Office |
| askubuntu | 50 | OS & General |
| serverfault | 15 | DevOps & Infrastructure |
| apple | 25 | MDM & Mobility |
| android | 25 | MDM & Mobility |
| dba | 10 | Data & SQL |
| networkengineering | 10 | Networking |
| security | 10 | Cybersecurity |
| devops | 5 | DevOps & Infrastructure |

**Total**: 200 pairs, 9 communities.

**Rationale for serverfault vs devops**: The EDA's cross-community overlap analysis (Section 3 of `eda_stackexchange_corpus_v2.ipynb`) shows that `serverfault` is the de-facto DevOps Q&A site with 7,969 pairs, while `devops` has only 53. Sampling 15 from serverfault ensures representative coverage.

**Fallback strategy**: If a community has fewer pairs than its quota (e.g., `devops` only has 53 pairs total), the deficit is compensated from superuser (largest community). The compensation yields indistinguishable questions — confirming there's no objective Expert/Operational boundary.

### New Script: `api/scripts/build_golden_qa.py`

```python
# Expected pseudocode:
def build_golden_qa():
    random_seed = 42  # reproducibility
    quotas = {"dba": 10, "networkengineering": 10, "serverfault": 15,
              "security": 10, "devops": 5, "superuser": 50, "askubuntu": 50,
              "apple": 25, "android": 25}
    
    pairs = sample_stratified(mongo.qa_pairs, quotas, seed)
    write_golden(pairs, "evaluation_notebooks/goldens/golden_se_200.json")

def write_golden(pairs, path):
    items = [{
        "question": p["title_body"],
        "answer": p["upvoted_answer"],
        "ticketId": p["ticketId"],
        "kb": p["ticketId"]
    } for p in pairs]
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
```

### Golden Exclusion from Index

The 200 golden pairs are **excluded from the vector index** and BM25 at generation time. The script:
1. Computes Pinecone chunk IDs for each pair (matching ingestion chunking rules)
2. Deletes those chunk vectors from namespace `kb-se-all`
3. Rebuilds `bm25_index.json` excluding the 200 `ticketId` values

This measures **generalization** — the retriever must find similar-but-not-identical tickets, replicating production behavior where a new ticket arrives that was never in the historical corpus.

### Acceptance Criteria

- [ ] Script `api/scripts/build_golden_qa.py` created.
- [ ] Stratified sampling with `random_seed = 42` for reproducibility.
- [ ] Exact quotas: 200 pairs across 9 communities as defined above.
- [ ] Output: single file `evaluation_notebooks/goldens/golden_se_200.json`.
- [ ] Previous golden files (`golden_expert.json`, `golden_operational.json`) backed up with `.bak`.
- [ ] Each JSON item follows the DeepEval-compatible schema: `{question, answer, ticketId, kb}`.
- [ ] `kb` = `ticketId` (SE has no separate "KB").
- [ ] No `category` field (no data-driven basis for Expert/Operational classification).
- [ ] Validation: 200 total items, no duplicate `ticketId`.
- [ ] Pinecone exclusion: chunks of all 200 pairs deleted from namespace `kb-se-all`.
- [ ] BM25 rebuild: `bm25_index.json` excludes all golden `ticketId`s.
- [ ] Script `api/scripts/run_eval.py` created with: CLI flags (`--api-url`, `--golden-json`, `--output-dir`), support for all 5 DeepEval metrics, CSV + JSON output.
- [ ] `run_eval.py` tested locally: `python scripts/run_eval.py --api-url http://localhost:8000 --golden-json ../evaluation_notebooks/goldens/golden_se_200.json --output-dir ../evaluation_notebooks/raw_results/` produces a valid CSV.
- [ ] `run_eval.py` is idempotent (re-running appends with timestamp, does not overwrite).
- [ ] `run_eval.py` has no notebook dependency — only `pip install deepeval langchain-groq` needed.
- [ ] Commit with message `feat(eval): build 200-pair golden QA from SE corpus and standalone evaluator`.

### Post-Build Validation

Run a quick sanity check in Python:
```python
import json
data = json.load(open("evaluation_notebooks/goldens/golden_se_200.json"))
assert len(data) == 200
assert all("question" in x and "answer" in x and "ticketId" in x for x in data)
assert len(set(x["ticketId"] for x in data)) == 200  # no dups
```

### References

- Source collection (Issue #8): [`plans/M1_Ingestion/08_Coleccion_qa_pairs_MongoDB.md`](../M1_Ingestion/08_Coleccion_qa_pairs_MongoDB.md) — consolidated into HU-1
- Files to replace: `evaluation_notebooks/goldens/golden_se_200.json`
- Files preserved (.bak): `evaluation_notebooks/goldens/golden_expert.json.bak`, `evaluation_notebooks/goldens/golden_operational.json.bak`
- Orchestrator consuming it: `api/scripts/run_scenario_matrix.py`
- Base plan: [`RAG_DATASET_MIGRATION_PLAN.md`](../../RAG_DATASET_MIGRATION_PLAN.md)

### Notes

- Backup the current golden JSONs with `.bak` before overwriting — they serve as historical comparison.
- Do not mix synthetic legacy pairs with SE pairs in the new golden file. They are different sources and mixing them contaminates the metric.
- If a community has fewer pairs than the quota (e.g., `devops` only has 53 pairs total), adjust to what's available and compensate from another community.
- The `random_seed` guarantees two script runs produce the same output — vital for portfolio reproducibility.

### Bonus: Standalone evaluation runner

This Issue also builds `api/scripts/run_eval.py`, a reusable CLI evaluator that:
- Loads a golden QA JSON and an API endpoint URL
- Queries the endpoint for each question, collects answers + context
- Runs DeepEval metrics (Correctness, Faithfulness, AnswerRelevancy, ContextualPrecision, ContextualRecall)
- Saves results as CSV and JSON
- Is designed to run both locally and inside a GitHub Actions workflow (no notebook dependency)

This script is used immediately in M2 for the manual baseline run, and later adopted by the M5 CI/CD pipeline for automated evaluation.
