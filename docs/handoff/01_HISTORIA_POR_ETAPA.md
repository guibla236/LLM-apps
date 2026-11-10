# 01 — Historia por etapa

Cronología de lo que se pretendió, cómo se hizo y qué se obtuvo. Sirve para reconstruir la
narrativa del blog (que es lo que el portfolio vende) sin reabrir las transcripciones.

Cada etapa tiene: **objetivo → qué se hizo → resultado → artefactos → lección**.

---

## Prehistoria (antes de julio 2026): el RAG sintético

- RAG sobre corpus **sintético**: ~750 pares de tickets de soporte IT en español, generados por LLM,
  más KBs también sintéticas nunca revisadas.
- Se lo evaluó y se publicó el diagnóstico (`blog_part1_rag_diagnostics.md`): **~10% Contextual
  Precision y ~22% Correctness**. Sospecha central: las Golden Answers sintéticas eran
  hiper-rígidas, así que el sistema “fallaba” por compararse contra un estándar artificial.
- Consecuencia: no se podía distinguir si el RAG era malo o si el dataset lo hacía parecer malo.
  De ahí nace toda la iniciativa de migración.
- Antes de migrar, el usuario **stasheó** las mejoras que estaban en curso para tener un baseline
  limpio (ver `02_DECISIONES.md`, D-01) y abrió una branch temporal + un milestone futuro.

## M0 — EDA del corpus real y decisión de filtrado ✅ (2026-07-19)

**Objetivo**: elegir un corpus real que represente el caso de uso y decidir, con datos, cómo
ingerirlo.

**Qué se hizo**
- Candidatos evaluados; se elige **Stack Exchange Q&A** (12 comunidades IT), ~60K pares EN.
- EDA en notebook: distribuciones de longitud, `score_tech`, cobertura de términos técnicos,
  profundidad temática por comunidad, outliers, prueba KS de log-normalidad.
- Discusión larga sobre el mecanismo de selección del par pregunta/respuesta (gap de 100 votos).

**Resultado / decisión**
- Ingestar **todo** el corpus con un único filtro duro: `upvoted_answer >= 50 caracteres`
  (se descartan 604 pares). `score_tech` **no** se usa como filtro: el 91,9% ya tiene ≥ 2.
- **Un solo namespace** `kb-se-all`, sin particionar por comunidad: el 98% del contenido DevOps
  vive fuera de la comunidad `devops`, así que particionar mata el recall.
- Chunking `RecursiveCharacterTextSplitter(1000, overlap=100)`: el 75% de las preguntas entra en
  un solo chunk.
- Hallazgo lateral explotado después: las longitudes siguen una **log-normal** → preguntas cortas
  vs largas tienen costo y dificultad distintos → base del M6.

**Artefactos**: `documentation/notebooks/eda_stackexchange_corpus.ipynb` (v2 es el principal, v1
quedó como backup), `plans/M0_EDA/`, entrada de blog `1_dataset_migration_EDA` (ES+EN).

**Lección**: el EDA se escribió como artículo narrativo, no como reporte; cada afirmación se
verificó contra la salida del notebook (hubo varias correcciones por conclusiones no data-driven).

## M1 — Ingesta del corpus real + realineación de paradigma ✅ (2026-07-21 / 2026-07-30)

**Objetivo**: llevar el corpus a Pinecone + MongoDB sin romper la API en producción, y adaptar el
sistema al cambio de paradigma (tickets → Q&A directo).

**Qué se hizo**
- Ingesta por comunidad con `--resume`, `--exclude-golden-ids`, verificación por lote y barra de
  progreso; IDs determinísticos `SE-{COMMUNITY}-{md5[:12]}`.
- Se descubrió a mitad de camino que había que **rehacer la ingesta** para excluir los IDs del
  Golden QA (evitar fuga de datos).
- Prompt de sistema y de HyDE reescritos: de “generar ticket JSON” a “responder Q&A”.
- Formato de respuesta: `{summary, contacts, suggested_actions}` → `{answer}`.
- Categorías de KB traducidas a inglés (bilingüe con fallback).

**Resultado**
- MongoDB `qa_pairs`: **60.161** documentos, 0 duplicados. Pinecone `kb-se-all`: **81.599** vectores.
  12/12 comunidades OK.
- 8/8 tests preexistentes pasan (compatibilidad hacia atrás del `TicketModel`).

**Artefactos**: `api/scripts/ingest_stackexchange_dataset.py`, `build_bm25_index.py`,
`run_ingest_pipeline.sh`, `api/logs/ingest_pipeline_20260721_*.log`.

**Lección**: el progreso de una ingesta larga debe ser visible y reanudable; se perdió trabajo por
un batch que falló en silencio y por volver a lanzar procesos que ya habían corrido.

## M2 — Golden QA y re-evaluación limpia ✅ (2026-08-03)

**Objetivo**: reconstruir el set de evaluación con el corpus real y volver a medir sin el sesgo del
dataset sintético.

**Qué se hizo**
- **200 pares estratificados** (`golden_se_200.json`) muestreados por comunidad/longitud; de esos,
  **50** se usan para las corridas.
- Evaluador standalone (`api/scripts/run_eval.py`) con DeepEval: reintentos, reanudación
  (`--append-to`), límite, selección de métricas y **juez independiente** del generador.
- Se arreglaron tres bugs de retrieval que arruinaban las métricas: namespace mal cableado,
  contrato de metadata `ticketId`/`text`, y re-sort del híbrido que hoisteaba BM25.

**Resultado** (50 pares, juez `deepseek-v4-flash`)

| Métrica | Vector Only | Hybrid |
|---|:---:|:---:|
| Correctness | 24.00% | **36.00%** |
| Faithfulness | 90.10% | **98.47%** |
| AnswerRelevancy | 94.57% | **94.76%** |

**Artefactos**: `run_eval.py`, `run_m2_eval.sh`, logs y CSV en
`documentation/markdowns/2_post_migration_eval/logs/`, entrada `2_post_migration_eval` (ES+EN).

**Lección**: la caída de Correctness no es una regresión del sistema, es la desaparición del sesgo
del golden sintético. El mensaje del blog es “ahora medimos de verdad”.

## M3 — Publicación de la serie ✅ (2026-08-17, falta el cierre de portfolio)

**Objetivo**: convertir las etapas en una serie de blog publicable.

**Qué se hizo**: entradas **0** (intro/motivación), **1** (EDA) y **2** (re-evaluación) escritas y
traducidas a inglés; reescritura de la Parte 1 para que la serie tenga arranque coherente; gráficos
exportados desde notebooks; chequeo de coherencia entre entradas.

**Pendiente**: issue #13 — actualizar `README.md` y la entrada de portfolio con la serie completa.
Es lo que convierte el repo en pieza de portfolio, y quedó sin hacer.

## M4 — Optimización de retrieval ✅ (2026-08-16)

**Objetivo**: subir Contextual Precision/Recall sin tocar el generador.

**Qué se hizo**
- Benchmark de embeddings (Voyage tiers, `qwen3-embedding`, `all-minilm`) y de chunking
  (con/sin, tamaños) con corridas P0/P1 sobre el mismo golden de 50.
- Migración de la búsqueda léxica de **BM25 local a MongoDB Atlas Search** (elimina el índice
  `bm25_index.json` del repo y el problema de mantenerlo sincronizado).
- Experimento de **expansión de contexto** (P1 expanded) controlado por flag.
- Cambio de juez a `gpt-5.6-luna` (independiente del generador) y análisis de la diferencia con
  DeepSeek como juez (DeepSeek subestima).

**Resultado**: gana **P1 = `voyage-4-lite`, chunk 1000/100**, con CP 69,40% (+9,07) y CR 25,91%
(+2,25) sobre `all-minilm`. El híbrido **empeora** CR (−2,72) → se adopta `vector_only` como default
de producción y el léxico queda solo para consultas con carga léxica.

**Artefactos**: notebook de visualización, logs en `3_semantic_retrieval_improvements/logs/`,
entrada `3_semantic_retrieval_improvements` (ES+EN).

**Lección (la más importante de la serie)**: un hallazgo negativo bien argumentado vale más que una
mejora marginal; ese resultado habilita el M7.

## M5 — CI/CD de evaluación ⏸️ diferido

Existía la infraestructura (`run_eval.py` + scripts `.sh`) pero nunca se escribió el workflow de
GitHub Actions. Se difirió por no estar en el camino crítico del portfolio.

## M6 — Benchmark de costo/latencia ✅ (2026-08-16)

**Objetivo**: responder “¿cuánto cuesta responder bien?” usando la log-normal del EDA como guía.

**Qué se hizo**
- Benchmark, **no router** (el router se descartó: ver D-07): 75 queries estratificadas en 3 buckets
  de complejidad (25 c/u), k=10, juez `gpt-5.6-luna`, midiendo latencia y tokens de salida reales.
- Se agregaron `--generator-model` y registro de modelos al evaluador; Gemini Flash Lite incluido a
  pedido del usuario para comparar latencia.

**Resultado**: DeepSeek gana en calidad (0,465 correctness), Ling en costo/calidad (0,412 a 1/4 del
costo), Gemini en latencia (2,5 s mediana, P95 ~3 s) pero pierde calidad (0,161). DeepSeek queda
como generador de producción.

**Artefactos**: `run_m6_benchmark.sh`, `4_cost_optimization/` (blog ES + `m6_visualization.ipynb` +
logs), entrada publicada solo en español.

**Estado fino**: al cierre quedaron **9 FIXMEs** planteados por el usuario sobre la entrada
(prueba de hipótesis al 90/95% en vez de “casi”, precios actualizados, ubicación de un FIXME,
argumentación sobre Gemini, redacción del párrafo del 68%). El turno se interrumpió antes de
aplicarlos → ver [H-03](./03_HILOS_ABIERTOS.md).

## M7 — Agente de diagnóstico multi-paso 🚧 (implementado, sin evaluar)

**Objetivo**: cerrar la serie con un agente que itere sobre el retrieval en vez de ser un wrapper
del RAG; motivado por el hallazgo de M4 (el léxico sirve solo a veces).

**Qué se hizo**
- `agent_app` migrado de Groq a **OpenRouter** (`ChatOpenAI` + `AGENT_MODEL`).
- Grafo LangGraph de 5 nodos: `analyze_query → search_rag → evaluate_sufficiency →
  [refine_query → search_rag]* → generate_answer`, con `max_iterations = 3`.
- **Routing por consulta**: `vector_only` por defecto; `hybrid` si detecta códigos de error,
  comandos, IDs o versiones (regex).
- Acumulación de contexto con deduplicación por `ticketId`, logging de trazas, y feature flag
  `USE_LEGACY_AGENT` para conservar el agente ReAct anterior.
- Borrador de la entrada 5 (`5_agentic_diagnosis/agentic_diagnosis_es.md`): motivación completa,
  resultados pendientes.

**Pendiente**: evaluación E2E contra el baseline de M4 (50 pares, juez `gpt-5.6-luna`), métricas de
agente (iteraciones promedio, % de consultas multi-paso, latencia, documentos acumulados),
traducción EN y cierre narrativo. Ver [H-01](./03_HILOS_ABIERTOS.md).

## M8 / M9 — diferidos

- **M8**: reemplazar Pinecone por MongoDB `$vectorSearch` + Voyage `autoEmbed` y `$rankFusion`
  nativo. Motivo: consolidar infraestructura y eliminar la dependencia de embeddings vía OpenRouter.
- **M9**: calibración de RRF, tuning de k, manejo de ventana de contexto, servidor MCP.

Ninguno se empezó. Si el próximo workflow no los retoma, conviene **borrarlos del roadmap** en vez de
dejarlos como deuda fantasma.

---

## Hilo conductor para la narrativa del blog

```
RAG sintético (métricas falsas)
   → M0: elegir corpus real y decidir con datos
   → M1: ingerir y reescribir el paradigma
   → M2: medir de verdad (baja Correctness, sube honestidad)
   → M4: optimizar retrieval (embeddings + léxico) → el híbrido deja de servir
   → M6: costos y latencia por complejidad (benchmark, no router)
   → M7: agente que decide cuándo buscar distinto y cuándo parar
```
