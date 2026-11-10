# Roadmap — RAG Real Data Migration & Improvements

Tracking file for milestone progress. Updated at each milestone completion.

---

## M0 — EDA & Decision ✅ (2026-07-19)

**Issues**: #1, #2
**Commits**: EDA notebook + blog articles merged to `feat/rag-real-data-migration`
**Decision**: Ingest all ~60K pairs with one hard filter (`upvoted_answer >= 50 chars`)
**Evidence**: `evaluation_notebooks/eda/eda_stackexchange_corpus_v2.ipynb`, `eda_decision.json`
**Key findings**:
- 91.9% of pairs have `score_tech >= 2` after hard filter — corpus is clean
- Log-normal distribution in answer lengths (KS p=0.04) — hybrid inference opportunity
- 98% of DevOps content lives outside the `devops` community — metadata filters deferred
- 604 pairs dropped (answers < 50 chars)

---

## M1 — Real Corpus Ingestion ✅ (2026-07-21)

**Issues**: Consolidated into 2 user stories: ingesta + postprocesamiento
**Depends on**: M0 decision
**Branch**: `feat/real-corpus-ingestion`
**Total commits**: 9

**Commits**:
- `refactor(api): extend TicketModel with optional SE fields`
- `feat(api): add qa_pairs MongoDB collection with indexes`
- `refactor(api): translate KB categories and metadata patterns to English`
- `feat(api): add stackexchange dataset ingestor script`
- `feat(api): rebuild BM25 index with SE enriched corpus`
- `feat(api): enrich context_retriever with expected_output from SE corpus`
- `fix: align ingestion script with EDA decisions (single kb-se-all namespace, 50-char filter only)`
- `feat: batching for vector upload in pinecone`
- `fix: deterministic IDs via hashlib.md5 + chunk_size=1000 per EDA`

**Files created**:
- `api/scripts/ingest_stackexchange_dataset.py` — ingestor with `--dry-run`, `--resume`, `--exclude-golden-ids`, `--list-communities`
- `api/scripts/build_bm25_index.py` — rebuilds BM25 from MongoDB qa_pairs
- `api/scripts/run_ingest_pipeline.sh` — automated sequential pipeline with per-community verification + logging
- `api/tests/test_ticket_model.py` — 8 unit tests for backwards compatibility

**Files modified**:
- `api/models/tickets.py` — +`expected_output`, `community` optional fields
- `api/modules/database.py` — +`qa_pairs` indexes (`ticketId` unique, `community`)
- `api/modules/rag_kb_ingestor.py` — bilingual KB categories (EN primary, ES fallback)
- `api/modules/rag_unified_retriever.py` — enriched `page_content_bm25` + `expected_output` in context
- `api/requirements.txt` — +`datasets==2.21.0`, +`tqdm`

**Ingestion results** (verified 2026-07-21 20:57):
```
MongoDB qa_pairs:   60,161 documents
Duplicados:          0
Pinecone kb-se-all:  81,599 vectors
Comunidades OK:      12/12
```

| Community | MongoDB | Expected | Δ |
|-----------|--------:|--------:|--:|
| android | 2,783 | 2,830 | 1.7% |
| apple | 6,613 | 6,696 | 1.2% |
| askubuntu | 9,894 | 9,975 | 0.8% |
| dba | 2,491 | 2,502 | 0.4% |
| devops | 52 | 53 | 1.9% |
| networkengineering | 472 | 476 | 0.8% |
| security | 3,066 | 3,069 | 0.1% |
| serverfault | 7,884 | 7,969 | 1.1% |
| sharepoint | 1,675 | 1,691 | 0.9% |
| superuser | 17,256 | 17,425 | 1.0% |
| unix | 6,103 | 6,173 | 1.1% |
| webapps | 1,872 | 1,906 | 1.8% |

**Key decisions applied from EDA**:
- Single Pinecone namespace `kb-se-all` (cross-community content — 98% of DevOps lives outside `devops`)
- Only hard filter: `upvoted_answer >= 50 chars` (score_tech not used as filter — 91.9% already ≥2)
- Community stored in metadata for provenance, not as namespace partition
- Chunking: `RecursiveCharacterTextSplitter(chunk_size=1000, overlap=100)` — 75% of questions fit in 1 chunk
- IDs: deterministic `SE-{COMMUNITY}-{md5[:12]}` (hashlib.md5 to avoid Python hash randomization)
- Golden QA exclusion: `--exclude-golden-ids` flag to prevent golden pairs from being retrievable in vector index
- Legacy synthetic namespace `kb-synthetic-legacy` preserved (namespace `""` with 305 vectors)
- `agent_app/` not touched (consumes API via HTTP, schema unchanged)

**Pipeline automation**:
- `api/scripts/run_ingest_pipeline.sh` processes communities sequentially (smallest first), logs to `api/logs/`, verifies each community + global state after each step, and is reentrant (skips already-complete communities via MongoDB check)
- Elapsed: ~4h for all 12 communities (16:54 → 20:57)

**Technical finding — BM25 index size explosion (2026-08-01)**:
- The rebuilt `bm25_index.json` is **125 MB** (28 MB gzip -9), 8-12x the 10-15 MB estimated in `RAG_DATASET_MIGRATION_PLAN.md`.
- **Deployment to production is impossible**: GitHub rejects files >100 MB (push blocked on `feat/eval_pipeline`), and Vercel serverless cannot load it at runtime (`json.load` + `BM25Retriever.from_documents()` over ~60K docs exceeds the 10 s timeout / 1 GB RAM of the Hobby plan). Hybrid BM25+Vector therefore only works in local/dev.
- **Implication**: the hybrid search must move to MongoDB Atlas Search (`$search` + `$vectorSearch` + `$rankFusion`) — the data already lives in `qa_pairs`. This validates and strengthens the M7 migration plan (see `plans/M7_VectorMigration/17_Migrate_retrieval_and_hybrid_ranking.md`).

**Paradigm realignment** (pending — new issues added 2026-07-29):
- `plans/M1_Ingestion/02_Paradigm_System_Prompt.md` — Realign system prompt and response format from ticket JSON to direct Q&A
- `plans/M1_Ingestion/03_Paradigm_HyDE.md` — Realign HyDE prompt from ticket generation to query reformulation
- **Why**: StackExchange corpus is Q&A format (question → direct answer), but the generator was built for IT ticket resolution (`summary` + `contacts` + `suggested_actions` in JSON). This structural mismatch invalidates M2 evaluation results until the prompts are aligned.

**Next**: Complete paradigm realignment → M2 re-execution → M3 re-execution

---

## M2 — Golden QA & Clean Re-evaluation ✅ (2026-08-03 — definitive)

**Issues**: #9, #10
**Depends on**: M1 (including paradigm realignment)
**Branch**: `feat/eval_pipeline`
**Judge**: DeepSeek V4 Flash (era), GPT-5.6-luna (reference baseline)

### Definitive results (50 stratified pairs × 2 scenarios, deepseek judge)

| Scenario | Correctness | Faithfulness | AnswerRelevancy | ContextualPrecision | ContextualRecall |
|----------|:-----------:|:------------:|:---------------:|:-------------------:|:-----------------:|
| Vector Only | 24.00% | 90.10% | 94.57% | 29.37% | 13.86% |
| Hybrid (BM25+Vector) | **36.00%** | **98.47%** | **94.76%** | **31.88%** | **17.15%** |

### Reference baseline with independent judge (GPT-5.6-luna)

| Scenario | Correctness | Faithfulness | AnswerRelevancy | ContextualPrecision | ContextualRecall |
|----------|:-----------:|:------------:|:---------------:|:-------------------:|:-----------------:|
| Vector Only | **50.40%** | **98.91%** | 96.14% | 60.33% | **23.66%** |
| Hybrid | 46.80% | 98.78% | **96.77%** | **64.54%** | 22.20% |

- **Key finding**: Migration conclusively successful (any judge). Retrieval solid with luna judge (60.33% CP vector-only).
- **Note**: DeepSeek judge numbers are the "era record"; luna numbers are the reference baseline for all subsequent comparisons.

**Next**: M4 — Search Optimization → M6 — Cost Benchmark → M7 — Agent

**Changes from original plan**:
- Expert/Operational split removed — no data-driven basis for difficulty classification. Single `golden_se_200.json`.
- Judge changed 3 times: `llama-4-scout-17b` (Groq, deprecated) → `llama-3.3-70b-versatile` (Groq, quota limit) → `deepseek/deepseek-v4-flash` (OpenRouter, dev) → `openai/gpt-5-nano` (OpenRouter, final portfolio run).
- LLM provider migrated from Groq to OpenRouter for both generation and evaluation.
- `run_eval.py` calls `augment_search_results` (generated answer) instead of raw context — metrics now measure end-to-end RAG quality.
- `third_party_clients.py` migrated from `ChatGroq` to `ChatOpenAI` with OpenRouter base URL.

**Files created**:
- `api/scripts/build_golden_qa.py` — stratified sampling + Pinecone exclusion + BM25 rebuild
- `api/scripts/run_eval.py` — standalone CI/CD-ready evaluator
- `api/scripts/run_scenario_matrix.py` — orchestrator for 4 scenarios
- `api/scripts/scenarios.json` — scenario/config metadata
- `evaluation_notebooks/goldens/golden_se_200.json` — 200 pairs, 9 communities

**Files modified**:
- `api/modules/third_party_clients.py` — Groq → OpenRouter + DeepSeek models
- `api/modules/news_summarizer.py` — import updated for OpenRouter
- `api/modules/rag_tickets_retriever.py` — import updated for OpenRouter
- `api/modules/rag_unified_retriever.py` — import updated for OpenRouter
- `api/modules/async_rag_evaluator.py` — import updated for OpenRouter
- `api/available_models.json` — added DeepSeek V4 Flash, GPT-5 Nano
- `api/app.py` — rate limits disabled for local eval
- `api/modules/security.py` — quota checks disabled for local eval
- `api/static/bm25_index.json` — rebuilt excluding golden IDs

**Synthetic baseline preserved** (for comparison in portfolio blog):
- `evaluation_notebooks/raw_results/*_050426.csv` — 10 CSVs from original Spanish synthetic run

**Commits**:
- `feat(eval): build 200-pair golden QA, standalone evaluator, and scenario orchestrator`
- `fix(api): disable rate/quota limits for local eval runs`
- `chore(eval): clean up smoke test CSVs from raw_results`
- `refactor(api): migrate LLM providers from Groq to OpenRouter, add DeepSeek V4 Flash and GPT-5 Nano models`

**Next**: M3 — Publication (Phase 1 closure)

---

## M3 — Publication ✅ (2026-08-17)

**Issues**: #12 (blog), #13 (portfolio — pending)
**Branch**: `feat/search-optimization`

**Status**: Entries 0, 1 and 2 written and translated to EN. Entry 2 restructured with independent-judge baseline section and judge-comparison analysis (deepseek vs luna). All commits made on `feat/search-optimization`.

**Remaining**: Portfolio update (#13).

**Next**: M4 → M6 → M7

---

## M4 — Search Optimization: Embedding, Chunking & Lexical Search ✅ (2026-08-16)

**Issues**: 4 issues (see `plans/M4_SearchOptimization/`)
**Branch**: `feat/search-optimization` (merged into the integration line on 2026-11-09)
**Winner**: P1 (voyage-4-lite, chunk 1000/100) with gpt-5.6-luna judge

### Final results (gpt-5.6-luna, vector_only)

| Metric | Baseline (all-minilm) | P1 (voyage-4-lite) | Δ |
|--------|:-----------:|:------:|:------:|
| Correctness | 50.40% | 51.00% | +0.6 |
| Faithfulness | 98.91% | 98.38% | −0.53 |
| AnswerRelevancy | 96.14% | 95.86% | −0.28 |
| ContextualPrecision | 60.33% | **69.40%** | **+9.07** |
| ContextualRecall | 23.66% | **25.91%** | **+2.25** |

- BM25 replaced with MongoDB Atlas Search (production hybrid restored).
- Local `bm25_index.json` removed from codebase.
- Entry 3 written and translated (ES+EN). Logs in `3/logs/`.
- Latency benchmark: OpenRouter embedding ~200-500ms per call vs ~50ms local Ollama.

**Next**: M5 (CI/CD — deferred), M6 (Cost Benchmark) ✅ → M7 (Agent) 🚧

---

## M5 — CI/CD Evaluation Pipeline ⏳ (deferred)

**Issues**: (to be authored)
**Depends on**: M2 (`run_eval.py` exists)
**Status**: Infrastructure exists (`run_eval.py`, `run_m2_eval.sh`, `run_m6_benchmark.sh`). GitHub Actions workflow not yet authored. Deferred — not on critical path for portfolio.

---

## M6 — Cost-Optimized Hybrid Inference ✅ CLOSED (2026-11-09)

**Issues**: #20 (benchmark) ✅, #21 (blog — ES published, EN pending)
**Depends on**: M4 ✅
**Scope**: Benchmark only. No router implementation (deferred — not justified by results).
**Artifacts**: `documentation/markdowns/4_cost_optimization/` (entry ES, 6 charts, `m6_visualization.ipynb`,
logs), `api/scripts/run_m6_benchmark.sh`, `evaluation_notebooks/goldens/golden_se_75_estratificado.json`.
**Outstanding (editorial, owner reviews by hand)**: one TODO in the entry (replace a table with an EDA
chart) and the EN translation. See `docs/handoff/PENDIENTES_BLOG.md`.

### Final results (gpt-5.6-luna, 75 queries, 25 per complexity bucket)

| Model | Correctness | Faithfulness | AnswerRelevancy | Gen. median | Cost/1K (output) |
|-------|:-----------:|:------------:|:---------------:|:-----------:|:-----------------:|
| **deepseek-v4-flash** | **0.465** | 0.983 | **0.956** | 11.9s | $0.047 |
| ling-2.6-flash | 0.412 | **0.997** | 0.788 | 5.5s | $0.011 |
| gemini-3.5-flash-lite | 0.161 | 0.852 | 0.628 | 2.5s | $0.173 |

- DeepSeek confirmed as production generator (global advantage 5.3 pts at edge of judge noise, clear in long bucket).
- Ling on Pareto frontier (cost-quality). Gemini sets latency standard (P95 ~3s).
- Router deferred — insufficient benefit given current model cost.

**Closed**: 2026-11-09. Entry 4 (ES) committed and pushed with the integration line.

**Next**: M7 (Agent) — portfolio closer

## M7 — Multi-Step Diagnosis Agent 🚧 (in progress)

**Branch**: `feat/agentic-rag-implementation` (integration line; contains M4 code + M6 tooling + M7 graph)
**Issues**: 3 issues (see `plans/M7_Agent/`)
**Depends on**: M4 ✅

**Bug fixed (2026-11-10)**: `advanced_search_tool` expected a `{"results": [...]}` envelope but
`/api/raw_unified_search` returns a plain list, so every search raised
`'list' object has no attribute 'get'` and the node reported 0 results. The agent had never
retrieved real context. Fixed in `e119cfd`; verified end to end against live services
(3 iterations, 5 documents accumulated, answer citing `SE-*` IDs).

### Implementation complete

- `agent_app` migrated from Groq to OpenRouter (`ChatOpenAI` + `AGENT_MODEL` env var).
- 5-node LangGraph: analyze → search → evaluate → [refine → search]* → generate.
- Per-query search strategy routing (vector_only default, hybrid for lexical-heavy signals).
- Feature flag `USE_LEGACY_AGENT` preserves old ReAct agent.
- Trace event logging, context accumulation with ticketId deduplication.

### Pending

- ⬜ E2E evaluation vs M4 baseline (50 golden QA pairs, gpt-5.6-luna judge).
- ⬜ Entry 5 EN translation.
- ⬜ Documentation of evaluation results.

**Next**: Evaluation → Portfolio complete → M8-M9 deferred

---

## M8 — Vector Backend Migration (Pinecone → MongoDB + Voyage AI) ⏳

**Issues**: #14-#19
**Depends on**: M4 ✅ + M6 ✅
**Why deferred**: Infrastructure consolidation — replaces Pinecone with MongoDB native `$vectorSearch` + `autoEmbed`. Eliminates OpenRouter embedding dependency. Native `$rankFusion` replaces custom hybrid ranking.

---

## M9 — Architectural Improvements ⏳

**Depends on**: M8
**Focus**: RRF calibration, k-tuning, context window management, MCP server. Refinements — not on critical path.
