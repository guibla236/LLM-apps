# EDA: Analyze Stack Exchange corpus and decide on filtering

## Meta

- **Milestone**: M0 — EDA & Decision
- **Labels**: `initiative:rag-real-data-migration`, `phase:eda`, `type:research`, `priority:high`, `area:notebooks`
- **Estimate**: 1-2 days

## Description

As an AI Engineer, I want to explore the Stack Exchange Q&A corpus (`flax-sentence-embeddings/stackexchange_titlebody_best_and_down_voted_answer_jsonl`) across the 12 IT-relevant communities selected to decide whether to apply a technical specificity filter before production ingestion.

The dataset is already pre-curated by its authors (filters: body length ≥20 chars, 100-vote gap between upvoted/downvoted). This means the "lower votes → out" filter is likely redundant. The hypothesis to validate is that the full ~60K can be ingested without quality filtering surgery.

### Technical Context

The current RAG system uses synthetic data. The migration to a real corpus aims to eliminate the hyper-rigid Golden Answer bias. See `RAG_DATASET_MIGRATION_PLAN.md` for full context.

### Communities in Scope

| Community | Expected Pairs | Mapped IT Category |
|-----------|---------------:|--------------------|
| superuser | 17,425 | Hardware / Office |
| askubuntu | 9,975 | OS / General |
| serverfault | 7,969 | DevOps / Infrastructure |
| apple | 6,696 | MDM / Mobility |
| unix | 6,173 | Sysadmin / Linux |
| android | 2,830 | MDM / Mobility |
| security | 3,069 | Cybersecurity |
| dba | 2,502 | Data & SQL |
| webapps | 1,906 | Cloud Collaboration |
| sharepoint | 1,691 | Cloud Collaboration |
| networkengineering | 476 | Networking |
| devops | 53 | DevOps |
| **Total** | **~59,800** | |

### Acceptance Criteria

- [ ] Notebook `eda_stackexchange_corpus.ipynb` created in the repo's `documentation` folder.
- [ ] Download of the 12 communities via `datasets.load_dataset(...)` with local cache management.
- [ ] Distribution of `len(title_body)` per community (histogram + boxplot).
- [ ] Distribution of `len(upvoted_answer)` per community (histogram + boxplot).
- [ ] % of pairs with detected error codes (regex `0x[0-9A-F]+`, `Error \d+`, `ERROR:`).
- [ ] % of pairs with numbered steps in the answer (regex `^\s*\d+\.\s`).
- [ ] Outlier length detection (p95, p99) per community.
- [ ] `community → IT KB category` mapping documented as a table in the notebook.
- [ ] Exploratory spike: are there outliers that justify a hard length filter?
- [ ] Decision documented (filter or not) with quantitative justification at the end of the notebook.
- [ ] If filtering is decided: implement the `score_tech` formula described in `RAG_DATASET_MIGRATION_PLAN.md` and validate score distribution.
- [ ] Commit and PR (or direct push) of the notebook with a conventional commit message (`docs: add EDA notebook for SE corpus`).

### score_tech Definition (Reference)

```
score_tech = (
    1 if regex_code_error.search(title_body) else 0
  + 1 if regex_numbered_steps.search(upvoted_answer) else 0
  + 1 if 50 <= len(title_body) <= 1500 else 0
  + 1 if len(upvoted_answer) >= 200 else 0
  + 1 if regex_tech_terms.search(title_body) else 0
)
# Range [0, 5]
# Keep top-N per community such that total ≤ 80K (20K headroom for experiments).
```

### Pre-EDA Hypothesis

Given the dataset's pre-filtering (100-vote gap), we would expect:
- Length distribution concentrated at 200-2000 chars for `title_body` and 500-5000 for `upvoted_answer`.
- 30-50% of pairs with error codes or numbered steps.
- Likely decision: do not filter by size. Filtering by `score_tech ≥ 2` adds marginal but documentable value for the blog.

### References

- Full plan: [`RAG_DATASET_MIGRATION_PLAN.md`](../../RAG_DATASET_MIGRATION_PLAN.md)
- Dataset card: https://huggingface.co/datasets/flax-sentence-embeddings/stackexchange_titlebody_best_and_down_voted_answer_jsonl
- Previous diagnosis (blog Part 1): [`blog_part1_rag_diagnostics.md`](../../blog_part1_rag_diagnostics.md)

### Notes

- Do not touch production code in this Issue. Only generate evidence.
- The notebook will serve as material for Issue #2 (blog draft) and Issue #12 (final blog).
- If `huggingface datasets` fails due to rate-limiting, download the parquet manually from the dataset card and load with `pd.read_parquet`.
