# Issue: Pinecone Namespace Rotation for Experimentation

## Meta

- **Milestone**: M4 — Search Optimization
- **Labels**: `initiative:search-optimization`, `phase:ingestion`, `type:task`, `priority:high`, `area:pinecone`
- **Depends on**: None (infrastructure)

## Description

M4 requires ingesting the same 60K documents multiple times with different embedding models and chunking strategies into Pinecone. The free tier has a 100K vector limit per index. With ~80K vectors per variant, we can only have one experiment live at a time.

Since MongoDB `qa_pairs` is the source of truth and Pinecone IDs are deterministic (`SE-{COMMUNITY}-{md5[:12]}_chunk-{idx}`), vectors are **regenerable** from text. But regeneration costs money (~$0.84/ingestion via OpenRouter embeddings). The namespace rotation strategy must balance experimentation flexibility with cost control.

## Strategy: dedicated experiment indexes (updated 2026-08-02)

### Decision (2026-08-02): no baseline backup + dedicated experiment indexes

**The "preserve `kb-se-all-v1-baseline`" step was dropped**, and the experiment
rotation was moved from *reuse one namespace* to *dedicated indexes per variant*.
Verified findings:

1. **Pinecone has no native namespace copy/rename** — not even in the latest SDK (9.1.0, checked the repo source): the copy-namespace endpoints are absent and the API docs 404. Only `create/describe/delete/list_namespace` + `query_namespaces` exist.
2. **The SDK cannot be upgraded anyway**: `langchain-pinecone` 0.2.13 (latest published, Nov 2025) pins `pinecone<8.0.0`, so the project is locked to 7.x unless `PineconeVectorStore` is refactored away (out of scope for M4).
3. **MongoDB free tier has no published bandwidth limit**, and a re-ingest of ~60K docs is ~60-120 MB of reads — trivial.
4. Vectors are **100% regenerable** from MongoDB `qa_pairs` (deterministic IDs) at $0 cost with local Ollama (~4h) or ~$0.84 with the OpenRouter API.
5. **The 100K limit is PER INDEX, not per project** (Starter plan, up to 6 indexes). With ~60-80K vectors per variant, two variants can be live simultaneously in separate indexes.
6. **Vector dimension is fixed per index** — `voyage-4-lite` produces 1024d while `all-minilm:22m` produces 384d (discovered in the P0 validation test: HTTP 400 "Vector dimension 1024 does not match the dimension of the index 384"). The experiment index must be created with 1024d.
7. **Starter plan quota check (dashboard 2026-08-02)**: 2GB storage, 1M read units/mo, 2M write units/mo — all fit our plan:
   - *Storage*: metadata is small (community + `expected_output` truncated to 500 chars + priority ≈ 0.6KB/vector). 384d vectors ≈ 2.1KB each (~170MB for 80K); 1024d ≈ 4.7KB each (~280MB for 60K, ~380MB for 80K). Three live indexes ≈ ~830MB; even a 4th ≈ ~1.2GB < 2GB. ✅
   - *Write units*: ~1 write unit per KB written → P0 ~280K, P1 ~380K, rotations + winner deploy + baseline restore ≈ 1.5-1.8M units total < 2M/mo. ⚠️ Tight but fits — so **avoid re-ingesting the production baseline until the winner is decided** (saves ~170K units) and delete experiment indexes when done.
   - *Read units*: each query (k=10, 1024d) ≈ 44 units → a 200-question evaluation ≈ ~18K units. Irrelevant vs 1M. ✅

**Rollback path**: re-point `PINECONE_INDEX_NAME` to the production index (384d) and re-run `ingest_stackexchange_dataset.py --resume` against MongoDB to restore the baseline. Simpler than a namespace copy that doesn't exist. Note: the baseline restore is deferred until the M4 winner is chosen (write-unit budget).

### Primary approach: dedicated experiment indexes

```
Production (384d):  tickets-genai-portfolio  → baseline all-minilm:22m (regenerable, $0)
Experiment A (1024d): tickets-m4-exp-a      → P0: voyage-4-lite no-chunk      (~60K vectors)
Experiment B (1024d): tickets-m4-exp-b      → P1: voyage-4-lite chunk 1000/100 (~80K vectors)
                                                → P2/P3 rotate inside B (delete_all + re-ingest)
```

Workflow per experiment:

```
1. Create index tickets-m4-exp-{x} (dimension = embedding dims, cosine)
2. PINECONE_INDEX_NAME=tickets-m4-exp-{x} python scripts/ingest_stackexchange_dataset.py --embedding-model {model} {chunking} --exclude-golden-ids ../evaluation_notebooks/goldens/golden_se_200.json
3. Restart API with PINECONE_INDEX_NAME=tickets-m4-exp-{x} EMBEDDINGS_MODEL={model}
4. Run evaluation (run_eval.py) → save CSV
5. Keep the index alive for re-evaluation, or delete when done
```

**Cost**: $0.84 × N experiments (embeddings are the cost, not namespace ops). Two variants can stay live simultaneously at no extra cost; only the winner needs a final ingestion into production.

**Rollback**: switch `PINECONE_INDEX_NAME` back to `tickets-genai-portfolio`; re-ingest the original all-minilm:22m + chunk_1000 config from MongoDB (~4h local, $0) if the production namespace was cleared.

### Alternative: keep all variants live (if within limits)

Superseded by the dedicated-indexes approach (2026-08-02): the 100K limit is **per index** (up to 6 indexes on Starter), so two ~60-80K variants DO fit simultaneously in separate indexes — no need for namespace tricks.

(The old reasoning assumed a project-wide limit: 60K + 80K = 140K > 100K would have been a blocker within a single index/namespace — which is why the winner still gets deployed to the production index at the end.)

## Pinecone operations reference (dedicated indexes)

```bash
# Create an experiment index (dimension must match the embedding model)
pc.create_index(
    name="tickets-m4-exp-a",
    dimension=1024,  # voyage-4-lite; use 384 for all-minilm:22m
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
)

# Ingest into it (env var selects the index — script reads PINECONE_INDEX_NAME)
PINECONE_INDEX_NAME=tickets-m4-exp-a python scripts/ingest_stackexchange_dataset.py \
    --embedding-model voyage-4-lite --no-chunk \
    --exclude-golden-ids ../evaluation_notebooks/goldens/golden_se_200.json

# Evaluate against it (restart API with the env var set)
PINECONE_INDEX_NAME=tickets-m4-exp-a EMBEDDINGS_MODEL=voyage-4-lite uvicorn app:app --port 8000

# Cleanup when done
pc.delete_index("tickets-m4-exp-a")
```

**No namespace copy/rename exists in Pinecone** — verified across SDK versions (7.x and 9.x). Rotation is done at the index level, not namespace level.

## Vector backup strategy (config only)

Since vectors are regenerable from MongoDB text, the only thing worth backing up is the **configuration** that produced each experiment:

```json
{
  "experiment_id": "voyage4lite_nochunk",
  "embedding_model": "voyage-4-lite",
  "embedding_dims": 1024,
  "chunk_strategy": "no_chunking",
  "chunk_size": null,
  "chunk_overlap": null,
  "pinecone_index": "tickets-m4-exp-a",
  "vector_count": 60161,
  "ingestion_date": "2026-08-01",
  "cost": 0.84
}
```

This config alone is sufficient to regenerate the exact same index.

If local backup is desired for faster restoration, save vectors to `.npz` during ingestion (a future enhancement to `ingest_stackexchange_dataset.py` with `--backup-vectors` flag).

## Acceptance criteria

- [x] Baseline preservation strategy resolved (2026-08-02): no namespace copy — rollback via re-ingest from MongoDB (decision above)
- [x] Experiment rotation strategy resolved (2026-08-02): dedicated indexes per variant (up to 6 indexes, 100K vectors per index); dimension fixed per index (384 vs 1024)
- [ ] Ingestion script uses env var for chunking config (`CHUNK_SIZE`, `CHUNK_OVERLAP`, `NO_CHUNK`)
- [ ] Experiment results documented with config + metrics per variant
- [ ] Winner deployed to production index (`tickets-genai-portfolio`), experiment indexes cleaned up
- [ ] Pinecone SDK upgrade (9.x) documented as blocked by `langchain-pinecone<8.0.0` — revisit when `PineconeVectorStore` is refactored away (M8) or langchain-pinecone relaxes the pin
