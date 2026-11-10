# Plans — RAG Dataset Migration Structure

This folder contains the complete plan for migrating the RAG dataset (from synthetic → real Stack Exchange Q&A) structured as user stories and technical migrations, ready to be replicated as GitHub Issues.

## Meta

- **Goal**: Migrate the RAG system corpus to real Stack Exchange data for a clean evaluation without synthetic Golden Answers bias.
- **Scope**: From corpus EDA to blog republication.
- **Base document**: [`../RAG_DATASET_MIGRATION_PLAN.md`](../RAG_DATASET_MIGRATION_PLAN.md)
- **User decisions**: see section 3 of the base plan.

## How to Use This Folder

1. Create the **labels** defined in [`LABELS.md`](./LABELS.md) on GitHub.
2. Create the **milestones** defined in [`MILESTONES.md`](./MILESTONES.md) with their respective dates.
3. Create **one Issue per file** in the `M0_*`, `M1_*`, `M2_*`, `M3_*` subdirectories.
   - Each file's title is the suggested Issue title.
   - The file body is Markdown content ready to copy-paste into the Issue.
   - The `## Labels` and `## Milestone` sections are applied manually on GitHub.
4. Associate each Issue with its Milestone and apply its Labels.
5. Detect gaps and questions during copying → bring them back to the copilot to refine the plan.

## Structure

```
plans/
├── README.md           <- this file (index)
├── LABELS.md           <- label definitions to create
├── MILESTONES.md       <- milestones with dates (M0-M8)
├── M0_EDA/             <- 2 issues (exploratory phase)
├── M1_Ingestion/       <- 2 user stories (consolidated from 6 micro-issues)
├── M2_Evaluation/      <- 2 issues (#9, #10; #11 deferred to M6)
├── M3_Publication/     <- 2 issues (#12, #13)
├── M5_VectorMigration/ <- 6 issues (#14-#19 — migration + post-migration eval merged)
└── M6_HybridInference/ <- 2 issues (#20, #21 — cost-optimized model routing)
```

> **Note on M4**: Milestone M4 (CI/CD Evaluation Pipeline) is defined in `MILESTONES.md` but does not yet have physical issue files. Issues will be authored when `run_eval.py` is ready from M2.

> **Note on M5**: Milestone M5 (Vector Backend Migration) now includes the post-migration evaluation (formerly M6). The CI/CD pipeline validates the migration automatically.

> **Note on M6**: Milestone M6 (Architectural Improvements) is defined in `MILESTONES.md` but does not yet have an `M6_Architectural/` subfolder. Issues will be authored when M5 is complete.

> **Note on M8**: Milestone M7 (Cost-Optimized Hybrid Inference) builds on the log-normal discovery from the EDA. Issues #20-#21 are ready.

> **Note on M8**: Milestone M8 (Retriever Academic Benchmark) was eliminated — effort reallocated to blog entries and core milestones.

> **Note on M9**: Milestone M9 (Cost-Optimized Hybrid Inference) builds on the log-normal discovery from the EDA notebook. Runs parallel to M8/M8. Issues #31-#32 are ready.

> **Note on M5**: Milestone M5 (Vector Backend Migration) now includes the post-migration evaluation (formerly M6). The CI/CD pipeline validates the migration automatically.

## Issue Listing (14 ready across M0-M3, M5, M8; M4/M6 pending)

Issues' initiatives: M0-M3 `rag-real-data-migration`, M5 `vector-backend-migration` + `post-migration-eval`, M7 `cost-optimized-inference`.

| #  | Milestone | Title | Status |
|----|-----------|-------|--------|
| 1-2 | M0 EDA | EDA + blog draft | ✅ done |
| 3-8 | M1 Ingestion | HU-1: Ingest corpus + HU-2: Post-process (consolidated) | ✅ done |
| 9   | M2 Eval | Build golden QA + `run_eval.py` | ✅ done |
| 10  | M2 Eval | Run DeepEval baseline against real corpus | ready |
| 11  | ~~M2 Eval~~ → **M6** | Embedding comparison (Voyage AI tiers) | deferred |
| 12  | M3 Pub | Write blog: "Diagnosing synthetic-data bias" | ready |
| 13  | M3 Pub | Update README and portfolio entry | ready |
| 14  | **M5** Vector | Spike: MongoDB Atlas + Voyage AI PoC | ready |
| 15  | **M5** Vector | Replace embeddings / vector store with MongoDB | ready |
| 16  | **M5** Vector | Migrate ingestion pipeline (Pinecone → MongoDB) | ready |
| 17  | **M5** Vector | Migrate retrieval + native hybrid ranking | ready |
| 18  | **M5** Post | Re-run DeepEval on MongoDB backend (via CI/CD) | ready |
| 19  | **M5** Post | Blog: "Phase 1.8 — Migrating to MongoDB Atlas" | ready |
| 20  | **M8** Hybrid | Benchmark LLMs by answer complexity bucket | ready |
| 21  | **M8** Hybrid | Implement hybrid model router | ready |

## Naming Convention

Each Issue file follows this format to align with Azure DevOps / Jira:

- The Issue body is in **user story** format (`As a [role], I want [functionality] so that [benefit]`) to reflect business value.
- Acceptance criteria with `- [ ]` checkboxes (GitHub renders them as tasks).
- **References** section with links to affected repo files — help the reviewer.

## Notes

- Estimates (in Story points or time) are indicative. Feel free to adjust them.
- Files in `M0_EDA/02_Decision_filtrado_blog_draft.md` produce a blog draft, not the final blog (that's Issue #12).
- Recommended creation order: labels → milestones → M0 issues → M1 → M2 → M3 (respecting implicit dependencies between issues).
