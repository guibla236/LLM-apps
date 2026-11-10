# Labels to Create on GitHub

Apply these labels to the repo before creating Issues. GitHub doesn't require creating labels beforehand, but doing it first prevents typos when assigning them.

## Labels by Initiative (`initiative:`)

Top-level grouping label that identifies which broader effort (epic-of-epics) an Issue belongs to. Cross-cuts phases and milestones. Necessary when the project has multiple improvement initiatives tracked in parallel — a recruiter filtering by an initiative tag sees the full story of one specific effort (e.g., this migration's 13 issues) without mixing in unrelated future work.

| Label | Suggested Color | Description |
|------|----------------|-------------|
| `initiative:rag-real-data-migration` | `#5319E7` (dark violet) | RAG Real Data Migration — synthetic corpus → Stack Exchange real corpus (M0-M3 cycle) |
| `initiative:search-optimization` | `#FBCA04` (yellow) | Retrieval optimization via embedding model upgrade + chunking strategy selection (M4 cycle) |
| `initiative:ci-cd-evaluation` | `#1D76DB` (blue) | Automated evaluation pipeline with regression detection (M5 cycle, parallel) |
| `initiative:cost-optimized-inference` | `#0E8A16` (green) | Cost-aware hybrid model routing based on answer complexity (M6 cycle) |
| `initiative:agentic-diagnosis` | `#D93F0B` (orange) | Multi-step LangGraph agent that iterates on retrieval to diagnose IT issues (M7 cycle) |
| `initiative:vector-backend-migration` | `#B60205` (red) | Migration from Pinecone+Ollama to MongoDB Atlas Vector Search + Voyage AI (M8 cycle, deferred) |
| `initiative:architectural-improvements` | `#5319E7` | Architectural refinements — RRF, k-tuning, context window management, embedding comparison, MCP (M9 cycle, deferred) |
| _(future)_ `initiative:rag-oriented-fine-tuning` | `#5319E7` | Reserved for the next planned initiative (RAG-oriented Fine-Tuning) — not created now |
| _(future)_ `initiative:real-ms-docs-ingestion` | `#5319E7` | Reserved for future real Microsoft/Azure docs ingestion as KB |

**Rule**: every Issue in this plan MUST carry exactly ONE `initiative:` label. When future initiatives arrive, they will have their own `initiative:` label and you can distinguish them at a glance on the GitHub Issues list.

## Labels by Phase (`phase:`)

Indicate which plan phase the Issue belongs to. Equivalent to "Iteration Path" in Azure DevOps.

| Label | Suggested Color | Description |
|------|----------------|-------------|
| `phase:eda` | `#BFD4F2` (light blue) | Phase 0 — Initial corpus exploration |
| `phase:ingestion` | `#D4C5F9` (violet) | Phase 1 — Ingestion + production code changes |
| `phase:eval` | `#FBCA04` (yellow) | Phase 2 — Golden QA + re-evaluation |
| `phase:docs` | `#84B6EB` (medium blue) | Phase 3 — Documentation and publication |
| `phase:spike` | `#FBCA04` (yellow) | Research spike / proof-of-concept (time-boxed investigation) |
| `phase:migration` | `#D4C5F9` (violet) | Backend migration (Pinecone → MongoDB) |

## Labels by Type (`type:`)

Equivalent to "Work Item Type" in Azure DevOps. Models PBI/Story/Bug/Task within GitHub's single "Issue" type.

| Label | Suggested Color | Description |
|------|----------------|-------------|
| `type:story` | `#0E8A16` (green) | User Story with explicit business value |
| `type:task` | `#1D76DB` (blue) | Atomic technical task (refactor, script) |
| `type:research` | `#5319E7` (dark violet) | Analysis / spike / experiment |
| `type:content` | `#FEF2C0` (cream) | Blog or documentation writing |
| `type:bug` | `#B60205` (red) | Defect detected during execution |
| `type:enhancement` | `#A2EEEF` (cyan) | Improvement to existing code |

## Labels by Priority (`priority:`)

| Label | Suggested Color | Description |
|------|----------------|-------------|
| `priority:high` | `#B60205` | Blocks subsequent milestone progress |
| `priority:medium` | `#FBCA04` | Important, but with slack |
| `priority:low` | `#0E8A16` | Optional improvements |

## Labels by Area (`area:`)

Affected system component. Equivalent to "Component" in Jira.

| Label | Suggested Color | Description |
|------|----------------|-------------|
| `area:backend` | `#E4E669` | Python API (FastAPI, `api/` modules) |
| `area:pinecone` | `#84B6EB` | Pinecone index/namespace changes |
| `area:mongodb` | `#006B75` | MongoDB collection changes |
| `area:prompts` | `#D93F0B` | `.md` files in `api/prompts/` |
| `area:notebooks` | `#1D76DB` | Evaluation/EDA notebooks |
| `area:blog` | `#FEF2C0` | Blog posts in `blog_*.md` |
| `area:docs` | `#84B6EB` | README, general documentation |

## Visual Summary After Application

A typical ingestion Issue should look like:
```
[ #4 ] Stack Exchange ingestion script → Pinecone + MongoDB
Labels: initiative:rag-real-data-migration, phase:ingestion, type:task, priority:high, area:pinecone, area:backend
Milestone: M1 - Real Corpus Ingestion
```
