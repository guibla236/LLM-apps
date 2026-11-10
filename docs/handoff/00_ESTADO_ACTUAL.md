# 00 — Estado actual (corte 2026-08-19)

Resumen factual. Los números están tomados de `ROADMAP.md`, `plans/MILESTONES.md` y los logs de
`evaluation_notebooks/raw_results/`.

---

## 1. Foto del repositorio

| Ítem | Valor |
|---|---|
| Repo | `guibla236/LLM-apps` (GitHub) |
| Ruta local | `/home/guillermo/Documentos/Courses/GenAI_E2_bootcamp/Tarea_2` |
| Rama actual | `feat/cost-optimization-benchmark` |
| Upstream | **ninguno** (no existe en `origin`) |
| Divergencia vs `main` | 57 commits adelante, 0 atrás |
| Working tree | 5 archivos modificados + ~20 rutas sin trackear |
| Stashes | 3 (`2026-08-02`, `2026-08-17`, `2026-08-17`) |
| Repo anidado | `plans/` (ignorado por el principal; 3 archivos modificados sin commitear) |

Ramas relevantes ya mergeadas a la línea de trabajo: `feat/rag-real-data-migration`,
`feat/real-corpus-ingestion`, `feat/exploratory-data-analysis`, `feat/migration-to-real-dataset`,
`feat/search-optimization`, `feat/eval_pipeline`, `refactor/real-corpus-migration`.
Existe `backup/real-corpus-migration-pre-fix` como red de seguridad de una corrección de retrieval.

## 2. Estado por milestone

| M | Tema | Estado | Evidencia |
|---|---|---|---|
| M0 | EDA del corpus Stack Exchange y decisión de filtrado | ✅ 2026-07-19 | `documentation/notebooks/eda_stackexchange_corpus.ipynb`, `plans/M0_EDA/` |
| M1 | Ingesta del corpus real + realineación de paradigma | ✅ 2026-07-30 | `api/scripts/ingest_stackexchange_dataset.py`, `run_ingest_pipeline.sh` |
| M2 | Golden QA (200) + re-evaluación limpia | ✅ 2026-08-03 | `evaluation_notebooks/goldens/golden_se_200.json`, `api/scripts/run_eval.py` |
| M3 | Publicación (entradas 0–2 ES+EN) | ✅ 2026-08-17 (falta #13 portfolio) | `documentation/markdowns/0..2/` |
| M4 | Optimización de retrieval: embeddings, chunking, léxico | ✅ 2026-08-16 | `documentation/markdowns/3_semantic_retrieval_improvements/` |
| M5 | Pipeline de evaluación en CI/CD | ⏸️ diferido | no hay workflow de GitHub Actions |
| M6 | Benchmark de costo/latencia por complejidad | ✅ 2026-08-16 (benchmark); blog ES listo, EN pendiente | `documentation/markdowns/4_cost_optimization/` |
| M7 | Agente de diagnóstico multi-paso (LangGraph) | 🚧 implementación lista, **evaluación E2E pendiente** | `agent_app/`, `plans/M7_Agent/`, `documentation/markdowns/5_agentic_diagnosis/` |
| M8 | Migración Pinecone → MongoDB `$vectorSearch` + Voyage | ⏸️ diferido | `plans/M8_VectorMigration/` |
| M9 | Mejoras arquitectónicas (RRF, k-tuning, MCP) | ⏸️ diferido | `plans/M9_Architectural/` |

**Decisión del usuario (2026-11-09)**: parte de lo que estaba en curso se cancela y se retoma con
otro workflow, todavía sin definir. Lo único que hay que preservar sí o sí de ese tramo es el
**conocimiento y los resultados ya producidos** (M6 cerrado, M7 implementado sin evaluar).

## 3. Resultados vigentes (los números que el blog cita)

### M2 — post-migración, 50 pares, juez `deepseek-v4-flash`

| Métrica | Vector Only | Hybrid |
|---|:---:|:---:|
| Correctness | 24.00% | **36.00%** |
| Faithfulness | 90.10% | **98.47%** |
| AnswerRelevancy | 94.57% | **94.76%** |

Interpretación: el corpus real bajó Correctness respecto del sintético (las respuestas doradas ya no
están sesgadas por el generador), pero el híbrido recuperó +12 pts. Este es el baseline “sucio” que
justifica M4.

### M4 — optimización de retrieval, 50 pares, juez `gpt-5.6-luna`, `vector_only`

| Métrica | Baseline `all-minilm` | Ganador P1 `voyage-4-lite` chunk 1000/100 | Δ |
|---|:---:|:---:|:---:|
| Correctness | 50.40% | **51.00%** | +0.60 |
| Faithfulness | 98.91% | 98.38% | −0.53 |
| AnswerRelevancy | 96.14% | 95.86% | −0.28 |
| ContextualPrecision | 60.33% | **69.40%** | **+9.07** |
| ContextualRecall | 23.66% | **25.91%** | +2.25 |

Hallazgo que ordena todo lo que vino después: **el híbrido dejó de aportar**. Con `voyage-4-lite`
la búsqueda semántica es tan buena que el léxico desplaza contexto útil (CR −2.72 en la corrida
final `vector_only` vs `hybrid`). De ahí nace la idea del agente que decide *cuándo* usar léxico.

### M6 — benchmark de generadores, 75 queries estratificadas (25 por bucket), k=10

| Modelo | Correctness | Faithfulness | AnswerRelevancy | Mediana gen. | Costo/1K salida |
|---|:---:|:---:|:---:|:---:|:---:|
| **deepseek-v4-flash** | **0.465** | 0.983 | **0.956** | 11.9 s | $0.047 |
| ling-2.6-flash | 0.412 | **0.997** | 0.788 | 5.5 s | $0.011 |
| gemini-3.5-flash-lite | 0.161 | 0.852 | 0.628 | 2.5 s | $0.173 |

Conclusión: DeepSeek queda como generador de producción; Ling está en la frontera de Pareto
(costo/calidad); Gemini marca el estándar de latencia (P95 ~3 s). **El router híbrido se descartó**:
el beneficio no justifica la complejidad con los precios actuales.

## 4. Infraestructura de datos (estado al corte)

| Recurso | Contenido |
|---|---|
| Pinecone `kb-se-all` | 81.599 vectores del corpus Stack Exchange (chunk 1000/100) |
| Pinecone `kb-synthetic-legacy` | corpus sintético original (~750 pares ES), baseline histórico |
| MongoDB `qa_pairs` | 60.161 documentos, índices `ticketId` (unique) y `community` |
| MongoDB Atlas Search | índice léxico `default` sobre `qa_pairs` (reemplaza BM25 local) |
| Goldens | `golden_se_200.json` (200 estratificados), `golden_se_75_estratificado.json` (M6) |

## 5. Working tree sin commitear (⚠️)

**Modificados**

| Archivo | Qué tiene | Acción sugerida |
|---|---|---|
| `api/app.py` | rate limits `@limiter.limit(...)` comentados | **revertir** salvo que siga el benchmark |
| `api/modules/security.py` | cuotas por IP y por usuario comentadas + mensajes de error traducidos | separar: traducción se queda, cuotas se restauran |
| `api/modules/rag_unified_retriever.py` | experimento `EXPAND_CONTEXT` (ventana de contexto, off por default) | decidir si se descarta con M4 cerrado |
| `documentation/notebooks/eda_stackexchange_corpus.ipynb` | ajustes del EDA por imprecisión detectada | commitear o descartar explícitamente |
| `.gitignore` | ajustes | revisar |

**Sin trackear, relevante**

- `ROADMAP.md` — **fuente de verdad del avance**; no está commiteado.
- `documentation/markdowns/4_cost_optimization/` — entrada de blog M6 (ES) + logs + notebook de gráficos.
- `documentation/markdowns/5_agentic_diagnosis/` — borrador de la entrada M7 (solo motivación).
- `documentation/markdowns/3_.../logs/` — corridas `p0_luna` y `p1_expanded_luna` (CSV/JSON/logs).
- `api/scripts/run_m2_eval.sh`, `run_m6_benchmark.sh`, `backfill_exp_a_metadata.py`.
- `api/logs/` — logs de la ingesta del 2026-07-21 (2,2 MB).
- `PR_description.md`, `RAG_DATASET_MIGRATION_PLAN.md`.

## 6. Lo que NO existe

- Workflow de CI/CD para evaluación (M5).
- Router de modelos en producción (descartado en M6).
- Evaluación E2E del agente M7 (código sí, números no).
- Versión en inglés de las entradas 4 y 5.
- **La entrada 3 (M4) no está en esta rama**: vive en `feat/search-optimization` (ver H-11).
- Actualización del README/portfolio con la serie completa (#13).
- Stub/branch remota para la rama actual.
