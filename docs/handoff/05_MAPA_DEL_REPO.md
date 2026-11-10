# 05 — Mapa del repositorio

Dónde vive cada cosa. Útil para no re-explorar el repo desde cero.

---

## Árbol de primer nivel

```
Tarea_2/
├── api/                     # RAG service (FastAPI + Pinecone + MongoDB + OpenRouter)
├── agent_app/               # Agente (frontend Streamlit + backend LangGraph)
├── evaluation_notebooks/    # Goldens, resultados crudos, notebooks de EDA/evaluación
├── documentation/
│   ├── markdowns/           # <- LA SERIE DE BLOG (entradas 0..5, ES+EN)
│   └── notebooks/           # notebooks publicables (EDA, visualización de resultados)
├── plans/                   # repo git ANIDADO con los planes M0–M9 (ignorado por el principal)
├── docs/handoff/            # este paquete
├── scripts/
│   └── bootstrap_envs.sh    # recrea los 3 venvs, verifica y genera locks
├── ROADMAP.md               # estado por milestone (sin commitear al corte)
├── RAG_DATASET_MIGRATION_PLAN.md  # plan base de la migración
├── README.md                # desactualizado (marzo): no menciona la serie
└── run_all.sh               # levanta API + agente + frontend
```

## `api/` — el RAG

| Ruta | Qué hay |
|---|---|
| `app.py` | FastAPI con todos los endpoints (`/api/raw_unified_search`, `/api/augment_search_results`, ingesta, auth, UI admin) |
| `main.py` | entrypoint alternativo |
| `modules/rag_unified_retriever.py` | núcleo del retrieval: vector (Pinecone) + léxico (Mongo Atlas Search), HyDE, contexto |
| `modules/database.py` | conexión MongoDB, colecciones (`qa_pairs`, `users`, `ip_usage`, …) e índices |
| `modules/security.py` | API key, JWT, cuotas por IP/usuario, admin |
| `modules/rag_kb_ingestor.py`, `rag_tickets_ingestor.py` | ingesta de KBs y tickets legacy |
| `modules/async_rag_evaluator.py` | evaluación embebida en la API |
| `models/` | Pydantic (`TicketModel` con campos SE opcionales) |
| `prompts/rag_system_prompt.md`, `hyde_ticket.md` | prompts de producción (EN, paradigma Q&A) |
| `scripts/` | **todo el tooling de datos/eval** (ver abajo) |
| `requirements.eval.txt` | eval + ingesta (datasets, pandas, tiktoken) |
| `requirements.lock.txt` | freeze exacto de Python 3.12 |
| `tests/` | 8 tests de compatibilidad del modelo |
| `tarea2/` | venv del proyecto (no versionado) |
| `logs/` | logs de ingesta (sin commitear) |

### `api/scripts/` (lo que más se usa)

| Script | Para qué |
|---|---|
| `ingest_stackexchange_dataset.py` | ingesta del corpus real (`--dry-run`, `--communities`, `--resume`, `--exclude-golden-ids`, `--list-communities`) |
| `build_golden_qa.py` / `build_stratified_golden.py` | construcción de goldens |
| `run_eval.py` | evaluador DeepEval standalone (`--search-method`, `--k`, `--judge-model`, `--generator-model`, `--metrics`, `--limit`, `--append-to`) |
| `run_m2_eval.sh` | corrida M2 (vector_only + hybrid, juez deepseek) |
| `run_m6_benchmark.sh` | corrida M6 (3 generadores, juez luna, k=10) |
| `benchmark_embeddings.py` | benchmark de embeddings/latencia |
| `build_bm25_index.py` | legado (BM25 local, deprecado) |
| `run_scenario_matrix.py` + `scenarios.json` | matriz de escenarios |

## `agent_app/` — el agente

| Ruta | Qué hay |
|---|---|
| `backend/main.py` | API del agente (FastAPI), endpoint `/chat/` |
| `backend/core/` | grafo LangGraph (5 nodos), estado, routing de estrategia de búsqueda |
| `backend/routers/` | endpoints |
| `backend/prompts/` | prompts de los nodos |
| `backend/agent_graph.png` | diagrama del grafo (generado, sin trackear) |
| `frontend/app.py` | UI Streamlit |
| `backend/backend_venv/` | venv |

⚠️ `agent_app/.env`, `agent_app/backend/.env` y `agent_app/frontend/.env` existen en disco y **no se
versionan**. El backend apunta a OpenRouter (no a Groq, pese a lo que diga algún `.env` viejo).

## `evaluation_notebooks/`

```
goldens/                     # golden_expert.json, golden_operational.json (legacy sintéticos)
                             # golden_se_200.json (M2/M4), golden_se_75_estratificado.json (M6)
raw_results/                 # CSV + *_aggregate.json + .log de cada corrida
eda/                         # notebooks y planes del EDA
actual/, plans/              # notebooks por etapa
```

**Regla**: `raw_results/` es la fuente primaria de cifras; los blogs citan copias en su propia
carpeta `logs/`.

## `documentation/markdowns/` — la serie

| Entrada | Carpeta | Estado |
|---|---|---|
| 0 | `0_dataset_migration_intro/` | ES + EN ✅ |
| 1 | `1_dataset_migration_EDA/` | ES + EN ✅ |
| 2 | `2_post_migration_eval/` | ES + EN ✅ |
| 3 | `3_semantic_retrieval_improvements/` | `semantic_search_optimization_{es,en}.md` — **solo existen en la branch `feat/search-optimization`, no en la rama actual** |
| 4 | `4_cost_optimization/` | ES ✅ (sin commitear), EN ❌, `m6_visualization.ipynb` + `img/` + `logs/` |
| 5 | `5_agentic_diagnosis/` | borrador ES (solo motivación), EN ❌ |

Además: `plans/M3_Publication/12_Reescribir_blog_Part1.md` documenta la reescritura de la Parte 1
(la entrada de diagnóstico vieja), que quedó fuera de la carpeta de markdowns.

## `plans/` — planificación

Repo git anidado (ignorado). Contiene `MILESTONES.md`, `LABELS.md`, `README.md` y las carpetas
`M0_EDA`, `M1_Ingestion`, `M2_Evaluation`, `M3_Publication`, `M4_SearchOptimization`,
`M6_HybridInference`, `M7_Agent`, `M8_VectorMigration`, `M9_Architectural`.
En este paquete hay un snapshot de lectura en [`planes/`](./planes/) con
`HISTORIAL_PLANS.txt` (log del repo original).

## Infraestructura externa

| Recurso | Detalle |
|---|---|
| Pinecone | `kb-se-all` (81.599 vectores, corpus real), `kb-synthetic-legacy` (baseline histórico) |
| MongoDB Atlas | `qa_pairs` (60.161 docs), Atlas Search index `default`, colecciones de usuarios/cuotas/logs |
| OpenRouter | generador (`deepseek-v4-flash`) y juez (`gpt-5.6-luna`) |
| LangSmith | trazas del agente (opcional, `LANGSMITH_*`) |
| Vercel | deploy de `api/` (`vercel.json`) |

## Ramas (situación al corte)

- `main`: sin la migración.
- `feat/cost-optimization-benchmark` (**actual**): M1→M7, 57 commits sobre main, sin upstream.
- `feat/search-optimization`: **4 commits por delante de la actual**, incluidos el blog M4 (ES+EN)
  y los logs finales. Divergencia → ver [H-11](./03_HILOS_ABIERTOS.md).
- `feat/agentic-rag-implementation`, `feat/rag-real-data-migration`, `feat/real-corpus-ingestion`,
  `feat/eval_pipeline`, `feat/search-optimization`, `refactor/real-corpus-migration`: trabajo ya
  integrado o paralelo (revisar antes de borrar).
- `backup/real-corpus-migration-pre-fix`: red de seguridad.
- ~30 branches más de etapas anteriores (tareas del curso, features viejas).
