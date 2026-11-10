# Update README and portfolio entry: "Diagnosing the synthetic-data bias" narrative

## Meta

- **Milestone**: M3 — Publication
- **Labels**: `initiative:rag-real-data-migration`, `phase:docs`, `type:content`, `priority:medium`, `area:docs`, `area:blog`
- **Estimate**: 0.5 days
- **Depends on**: Issue #12 (blog rewritten)

## Description

As an AI Engineer aspiring to Senior, I want to update the repo README and the portfolio entry (`portfolio/src/content/blog/rag-initial-evaluation.es.mdx` and `.en.mdx`) under the methodological angle **"Diagnosing the synthetic-data bias in a RAG evaluation pipeline"** rather than the generic "RAG with real data" framing — so that any recruiter landing on the repo or portfolio immediately sees the engineering rigor (diagnosis → ablation → measurement) and the project-management discipline (milestones, issues, plan document).

### Concrete Changes

#### 1. `Tarea_2/README.md`

Add at the top (after the title):

```markdown
# GenAI-Powered Technical Support System

[![GitHub Milestones](https://img.shields.io/github/milestones/progress/<user>/<repo>?milestone=0)](...)
[![GitHub Issues](https://img.shields.io/github/issues/<user>/<repo>)](...)
[![License](https://img.shields.io/github/license/<user>/<repo>)](...)

## Process — Dataset Migration (2026-07)

This project underwent a structured migration from synthetic data to a real Stack Exchange Q&A corpus (~60K pairs). The full plan, milestones, and issues are tracked on GitHub:

- 📋 [Plan document](RAG_DATASET_MIGRATION_PLAN.md)
- 🎯 [Milestones](https://github.com/<user>/<repo>/milestones)
- 📊 [GitHub Projects board](https://github.com/<user>/<repo>/projects/1)

### Results

| Metric | Synthetic (baseline) | Real (SE) | Δ |
|--------|--------------------:|----------:|--:|
| Correctness | 22% | ?% | +? pts |
| Faithfulness | 84% | ?% | ? pts |
| Contextual Precision | 10% | ?% | +? pts |

Full analysis in [blog_part1_rag_diagnostics.md](blog_part1_rag_diagnostics.md).

---
(existing content...)
```

#### 2. `portfolio/src/content/blog/rag-initial-evaluation.es.mdx`

Update the front-matter and body with:
- Executive summary of the migration (1 paragraph).
- Link to the full blog in the repo.
- Screenshot of the GitHub Projects board as featured image.
- Simplified results table (similar to the README one).

#### 3. `portfolio/src/content/blog/rag-initial-evaluation.en.mdx`

English translation of the same changes.

#### 4. GitHub Projects Board Screenshot

Take manually:
- Go to GitHub Projects of the repo.
- "View as Board" view with Backlog / In Progress / Done columns.
- Screenshot with the 13 issues distributed after completing M0-M2.
- Save as `portfolio/public/images/blog/040926/github-projects-board.png`.

### Acceptance Criteria

- [ ] `Tarea_2/README.md` updated with milestone badges and "Process" section.
- [ ] Results table with actual numbers from Issue #10 (not placeholder).
- [ ] `portfolio/src/content/blog/rag-initial-evaluation.es.mdx` updated with migration summary and link to the full blog.
- [ ] `portfolio/src/content/blog/rag-initial-evaluation.en.mdx` updated (translation of `.es.mdx`).
- [ ] GitHub Projects board screenshot saved in `portfolio/public/images/blog/040926/github-projects-board.png`.
- [ ] Screenshot referenced in `.es.mdx` and `.en.mdx` with `![GitHub Projects board](/images/blog/040926/github-projects-board.png)`.
- [ ] Portfolio validation: `npm run build` in `portfolio/` does not break.
- [ ] Portfolio validation: `npm run check-translations` passes without errors.
- [ ] Commit with message `docs: update README and portfolio with migration results`.

### Executive Summary Template (ES)

> "Este proyecto migró su corpus RAG de datos sintéticos a un corpus real de ~60K pares Q&A de Stack Exchange. La migración fue planificada como 4 milestones con 13 issues tracking en GitHub Projects, permitiendo medir el impacto de datos reales vs sintéticos en métricas como Correctness, Faithfulness y Contextual Precision. Los resultados completos están en el repo."

### Executive Summary Template (EN)

> "This project migrated its RAG corpus from synthetic data to a real ~60K-pair Q&A corpus from Stack Exchange. The migration was structured as 4 milestones with 13 GitHub-tracked issues, allowing measurement of real vs synthetic data impact on metrics like Correctness, Faithfulness, and Contextual Precision. Full results are in the repo."

### References

- README to update: [`README.md`](../../README.md)
- Blog in portfolio: [`portfolio/src/content/blog/rag-initial-evaluation.es.mdx`](../../../portfolio/src/content/blog/rag-initial-evaluation.es.mdx)
- i18n validation script: [`portfolio/scripts/check-translations.mjs`](../../../portfolio/scripts/check-translations.mjs)
- Source blog (Issue #12): [`blog_part1_rag_diagnostics.md`](../../blog_part1_rag_diagnostics.md)
- Base plan: [`RAG_DATASET_MIGRATION_PLAN.md`](../../RAG_DATASET_MIGRATION_PLAN.md)

### Notes

- GitHub badges require the repo to be public. If it's private, the badges won't render — but you still have the Projects board link.
- The GitHub Projects board screenshot is **manual** — not automatable. Take it just before the final commit, with the board in its most visually complete state (M0 done, M1 in progress or done).
- If you don't want to expose the GitHub Projects board (e.g., sensitive internal discussions), crop it or use a mockup. But for portfolio, transparency is value.
- The `.mdx` English translation must maintain the same front-matter (slug, title, date) for portfolio routing to work.
