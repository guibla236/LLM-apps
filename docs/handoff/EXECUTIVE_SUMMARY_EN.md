# Executive summary (EN)

Handoff package for continuing this project in another harness. Spanish docs are authoritative;
this is the one-page English version.

---

## What this project is

A level-1 IT support RAG that is being developed as a **portfolio series**: each stage ships as a
blog entry (Spanish + English) that explains the problem, the method and the measured results. The
narrative arc goes from a simple RAG over synthetic data to an **agentic RAG** over a real corpus.

## Where it stands (as of 2026-08-19)

| Milestone | Theme | Status |
|---|---|---|
| M0 | EDA of the real Stack Exchange corpus + filtering decision | ✅ done |
| M1 | Real corpus ingestion (60,161 MongoDB docs / 81,599 Pinecone vectors) + Q&A paradigm realignment | ✅ done |
| M2 | 200-pair stratified golden set + clean DeepEval re-evaluation | ✅ done |
| M3 | Publication (entries 0–2, ES+EN) | ✅ done, portfolio README missing |
| M4 | Retrieval optimization (embeddings, chunking, lexical search) | ✅ done |
| M5 | CI/CD evaluation pipeline | ⏸️ deferred |
| M6 | Cost/latency benchmark by query complexity | ✅ benchmark done; EN blog missing |
| M7 | Multi-step diagnosis agent (LangGraph) | 🚧 implemented, **E2E evaluation missing** |
| M8/M9 | Vector backend migration / architectural refinements | ⏸️ deferred |

## Key results

- **M2** (50 pairs, DeepSeek judge): Correctness 24% vector-only → 36% hybrid. The drop versus the
  synthetic baseline is interpreted as removal of generator bias, not a regression.
- **M4** (50 pairs, independent `gpt-5.6-luna` judge): winner is `voyage-4-lite` + chunk 1000/100,
  ContextualPrecision 60.33% → **69.40%**. Crucially, **hybrid search stopped helping**
  (ContextualRecall −2.72), so `vector_only` became the production default.
- **M6** (75 stratified queries): DeepSeek V4 Flash wins on quality (0.465 correctness), Ling 2.6
  Flash sits on the cost/quality Pareto frontier, Gemini 3.5 Flash Lite wins on latency (2.5 s median)
  but loses badly on quality (0.161). **The model router was deliberately not implemented** — the data
  did not justify it.

## The thesis that ties the series together

M4's negative finding (lexical search hurts on average, but helps on queries with error codes,
commands and IDs) is what motivates an agent: deciding *when* to change search strategy and *when to
stop searching* is a conditional decision, i.e. exactly what an agent is for.

## Critical risks to address first

1. **Unpushed work**: `feat/cost-optimization-benchmark` has 57 commits and no upstream.
2. **The M4 blog entry only exists on `feat/search-optimization`**, 4 commits ahead of the current branch.
3. **Uncommitted security workaround**: rate limits and quotas are commented out in `api/app.py` and
   `api/modules/security.py`.
4. **`plans/` is a nested, git-ignored repository** — invisible in a clean clone (a snapshot is
   included here).
5. **Credentials were exposed in chat logs** (Groq, OpenRouter, JWT_SECRET, APP_API_KEY, MongoDB
   host); transcripts in this package are redacted, but keys should be rotated.

## Most valuable next steps

1. Push branches and merge `feat/search-optimization` into the working branch.
2. Revert the security workaround; commit or discard the rest of the working tree.
3. Resolve the 9 open FIXMEs in the M6 cost blog with current prices.
4. Run the M7 end-to-end evaluation (protocol already written in `plans/M7_Agent/02_Agent_Evaluation.md`)
   — **confirm scope first**, since the user announced some in-flight work will be cancelled and
   redefined.
5. Update README/portfolio (issue #13) and translate entries 4 and 5.

Full detail: [`00_ESTADO_ACTUAL.md`](./00_ESTADO_ACTUAL.md) · [`03_HILOS_ABIERTOS.md`](./03_HILOS_ABIERTOS.md).
