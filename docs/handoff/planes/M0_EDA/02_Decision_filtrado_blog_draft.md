# Write blog draft: EDA findings and filtering decision

## Meta

- **Milestone**: M0 — EDA & Decision
- **Labels**: `initiative:rag-real-data-migration`, `phase:eda`, `type:content`, `priority:medium`, `area:blog`
- **Estimate**: 0.5 days
- **Depends on**: Issue #1 (EDA)

## Description

Write an initial draft in Markdown format for the upcoming blog post that documents the EDA findings and the filtering decision. This draft will feed into the full blog rewrite (Issue #12).

### Narrative Context

The original blog Part 1 ends with: "The system is already built and running end-to-end. The low initial numbers are not a failure, but a measurable baseline." The new narrative arc continues it as follows:

1. Diagnosis (preserved, status quo).
2. Hypothesis: the problem is the synthetic data.
3. Real corpus EDA (this Issue).
4. Filtering decision with evidence.
5. *(Later: Migration + Reevaluation — Issue #12)*

### Acceptance Criteria

- [ ] Create file `blog_part1_draft_migration_section.md` in the repo root (do not overwrite `blog_part1_rag_diagnostics.md` yet).
- [ ] Section "Migration to Real Corpus: The EDA" written with:
  - Context: why we abandoned synthetic data.
  - Description of the chosen Stack Exchange dataset + selected communities.
  - Quantitative EDA findings (tables and refs to figures from notebook #1).
- [ ] Section "Filtering Decision" written with:
  - `score_tech` criteria defined.
  - Score distribution (figure from notebook #1).
  - Final argued decision (filter or not) with data.
  - Trade-offs considered.
- [ ] Professional tone, first person, technical blog writing style.
- [ ] Include placeholders for figures generated in the EDA notebook: `*([Placeholder: Insert length distribution chart])*`.
- [ ] Explicit mention of technical decisions as trade-offs (not as absolute truths).
- [ ] Commit with message `docs: add draft blog section for migration EDA`.

### Draft Questions to Answer

- Why 12 communities and not all? (IT-relevant mapping, Pinecone Free budget).
- Why not use the full 210K corpus? (non-IT community noise, embedding costs, search latency).
- Why trust the original dataset's pre-filtering? (100-vote gap).
- Why (not) apply `score_tech`? (quantitative EDA argument).

### References

- EDA notebook (deliverable Issue #1): `evaluation_notebooks/eda/eda_stackexchange_corpus.ipynb`
- Base plan: [`RAG_DATASET_MIGRATION_PLAN.md`](../../RAG_DATASET_MIGRATION_PLAN.md)
- Original blog to continue: [`blog_part1_rag_diagnostics.md`](../../blog_part1_rag_diagnostics.md)

### Notes

- This Issue's draft is NOT the final blog. Issue #12 integrates this draft with M1 and M2 results.
- Maintain an honest tone: real numbers may show the RAG was even worse than we diagnosed. That honesty makes for a stronger technical narrative.
