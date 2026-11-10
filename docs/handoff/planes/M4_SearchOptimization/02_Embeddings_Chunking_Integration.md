# Issue: Integrate OpenRouter Embeddings & Chunking Variants

## Meta

- **Milestone**: M4 — Search Optimization
- **Labels**: `initiative:search-optimization`, `phase:ingestion`, `type:task`, `priority:high`, `area:backend`, `area:pinecone`
- **Depends on**: M4 namespace strategy (01_Namespace_Management.md)

## Description

Replace the local Ollama embedding model (`all-minilm:22m`, 384-dim) with OpenRouter-hosted embedding models and make chunking strategy configurable. The goal is to test 3 chunking strategies × 1-2 embedding models, measure the retrieval improvement, and deploy the best combination.

### Files to modify

| File | Change |
|------|--------|
| `api/modules/third_party_clients.py` | Add OpenRouter embeddings client, make embedding model configurable via env var |
| `api/scripts/ingest_stackexchange_dataset.py` | Add `--no-chunk`, `--chunk-size`, `--chunk-overlap` flags; support configurable embedding model |
| `api/.env` | Add `EMBEDDINGS_MODEL`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `NO_CHUNK` env vars |

### Embedding model integration

OpenRouter supports embeddings via the `/api/v1/embeddings` endpoint (OpenAI-compatible). Primary model: `voyage-4-lite` (1024-dim, Matryoshka-capable, $0.02/1M tokens, launched Jul 2026).

```python
# api/modules/third_party_clients.py
from langchain_openai import OpenAIEmbeddings

def get_embeddings_model(model_name: str = None) -> OpenAIEmbeddings:
    """Returns an OpenAI-compatible embeddings client via OpenRouter."""
    model = model_name or os.getenv("EMBEDDINGS_MODEL", "voyage-4-lite")
    return OpenAIEmbeddings(
        model=model,
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
        dimensions=1024,  # voyage-4-lite native dims; Matryoshka allows 256/512/2048
    )
```

### Chunking strategies to implement

Based on EDA findings (see `00_Search_Optimization_Overview.md`):

| Flag | Behavior | EDA rationale |
|------|----------|---------------|
| `--no-chunk` | Embed entire `title_body` as one vector per doc | 100% of docs fit in Voyage's 32K token window. Max doc = 4,199 chars. |
| `--chunk-size 1000 --chunk-overlap 100` | Baseline: RecursiveCharacterTextSplitter | Current production. 75% in 1 chunk. Control. |
| `--chunk-size 2000 --chunk-overlap 200` | Larger chunks | Intermediate. Reduces fragmentation to ~5% of docs. |

### Experiment workflow

For each (embedding_model, chunking_config) combo:

```bash
# 1. Configure
export EMBEDDINGS_MODEL=voyage-4-lite

# 2. Ingest (variant A: no chunking)
python ingest_stackexchange_dataset.py --no-chunk --namespace kb-se-all

# 3. Evaluate (50 pairs, vector_only + hybrid scenarios)
python run_eval.py \
  --scenario-name voyage4lite_nochunk \
  --golden-json ../evaluation_notebooks/goldens/golden_se_200.json \
  --limit 50

# 4. Delete namespace
# (manual via Pinecone console or script)

# 5. Repeat for next variant
```

## Acceptance criteria

- [ ] `OpenAIEmbeddings` client wired to OpenRouter in `third_party_clients.py`
- [ ] `EMBEDDINGS_MODEL` env var controls embedding model selection (default: `voyage-4-lite`)
- [ ] `--no-chunk` flag working in ingest script (embeds full `title_body`)
- [ ] `--chunk-size` and `--chunk-overlap` flags working
- [ ] Ingestion script falls back to Ollama locally if `EMBEDDINGS_MODEL` not set to an OpenRouter model (backward compat)
- [ ] Embedding latency measured: per-call time for OpenRouter vs local Ollama, plus batch ingestion throughput
- [ ] 3 experiments executed: voyage-4-lite × (no_chunk, chunk_1000, chunk_2000)
- [ ] Evaluation CSV per experiment saved with descriptive filenames
- [ ] Comparative table: `experiment | Correctness | Faithfulness | AnswerRelevancy | ContextualPrecision | ContextualRecall`
- [ ] Winner deployed to production `kb-se-all` namespace

## Cost estimate

| Item | Cost |
|------|------|
| 3 ingestion runs (voyage-4-lite × 3 chunking) | $2.52 |
| 1 final ingestion (winner) | $0.84 |
| Evaluation API calls (judge model, 150 queries total) | ~$0.50 |
| **Total** | **~$3.86** |

## References

- OpenRouter embeddings docs: https://openrouter.ai/docs/features/embeddings
- LangChain OpenAIEmbeddings: https://python.langchain.com/docs/integrations/text_embedding/openai/
- EDA chunking analysis: `documentation/markdowns/1_dataset_migration_EDA/dataset_migration_EDA_en.md`
