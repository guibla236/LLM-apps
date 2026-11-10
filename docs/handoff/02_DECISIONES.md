# 02 — Decisiones y alternativas descartadas

Registro tipo ADR. Está acá para **no re-litigar** lo ya decidido: si vas a proponer algo distinto,
hacelo explícitamente y con evidencia nueva.

Formato: contexto → decisión → consecuencias → alternativas rechazadas.

---

### D-01 — Congelar el baseline antes de migrar
**Contexto**: había mejoras de retrieval a medio hacer cuando se decidió cambiar el dataset; mezclarlas
haría imposible atribuir mejoras.
**Decisión**: stash de esos cambios (`stash@{2026-08-02}` y los del 17/08) + branch temporal
`backup/real-corpus-migration-pre-fix` + milestone futuro para retomarlas.
**Consecuencia**: M2–M4 se miden contra un baseline limpio. Las mejoras quedaron huérfanas: si se
retoman, hay que reevaluarlas contra el corpus nuevo (pueden haber quedado obsoletas).
**Alternativas**: mergear todo junto y medir después (rechazada: sin atribución).

### D-02 — Corpus real Stack Exchange en lugar de sintético
**Contexto**: el corpus sintético (~750 pares ES) tenía goldens generados por el mismo LLM, lo que
hacía que las métricas midieran el sesgo del generador y no la calidad del RAG.
**Decisión**: migrar a ~60K pares reales EN de 12 comunidades IT.
**Consecuencia**: corpus en inglés (todo el sistema se realinea), mucho más ruidoso y heterogéneo.
**Alternativas**: seguir con sintético y mejorar el golden (rechazada: no resuelve el sesgo);
ChromaDB local (rechazada: el deploy en Vercel/Render es volátil, se mantiene Pinecone).

### D-03 — Un único filtro duro y un único namespace
**Contexto**: el EDA mostró que `score_tech ≥ 2` ya lo cumple el 91,9% del corpus y que el 98% del
contenido DevOps está fuera de la comunidad `devops`.
**Decisión**: filtrar solo por `upvoted_answer >= 50 chars` (604 pares descartados) e ingerir todo
en un namespace `kb-se-all`, guardando `community` como metadata de procedencia.
**Consecuencia**: no hay filtrado por categoría ni partición por comunidad; el recall depende del
ranking, no de la selección de índice.
**Alternativas**: filtrar por `score_tech` (rechazada: no aporta), particionar por comunidad
(rechazada: mata DevOps), mapear comunidades a categorías IT (descartado cuando se eliminaron los KBs).

### D-04 — Chunking 1000/100
**Contexto**: el 75% de las preguntas entra en un chunk de 1000 caracteres.
**Decisión**: `RecursiveCharacterTextSplitter(chunk_size=1000, overlap=100)` sobre título+cuerpo,
con la respuesta en metadata (`expected_output`, recortada a 500 chars).
**Consecuencia**: 81.599 vectores para 60.161 documentos. El `expected_output` no se vectoriza.
**Alternativas**: chunks más chicos (más precisión, menos contexto), respuesta completa en el chunk
(rechazada: infla tokens y diluye la pregunta).

### D-05 — Rehacer la ingesta para excluir el Golden QA
**Contexto**: se detectó (tarde) que los pares usados como golden estaban dentro del índice → fuga
de datos en la evaluación.
**Decisión**: reingestar con `--exclude-golden-ids` y IDs determinísticos (`md5(title_body)[:12]`).
**Consecuencia**: una ingesta completa extra (horas) y la necesidad de verificar duplicados después.
**Alternativas**: dejar los goldens dentro y descontarlos al evaluar (rechazada: no escala).

### D-06 — Migrar BM25 local a MongoDB Atlas Search
**Contexto**: el índice `bm25_index.json` se desincronizaba y pesaba en el repo; además ya había
MongoDB en la arquitectura.
**Decisión**: búsqueda léxica nativa de Atlas sobre `qa_pairs`; se elimina `rank-bm25` y el JSON.
**Consecuencia**: la búsqueda híbrida depende de un índice de Atlas (`default`) que hay que crear
en cada entorno. La API necesita reinicio para tomar cambios de índice.
**Alternativas**: mantener BM25 con rebuild automático (rechazada: fragilidad), Elasticsearch
(rechazada: infra extra).

### D-07 — M6 fue benchmark, no router
**Contexto**: la hipótesis era enrutar consultas cortas a modelos baratos y largas a modelos caros
(aprovechando la log-normal del EDA).
**Decisión**: medir primero. El benchmark mostró que el delta de calidad DeepSeek vs Ling está en el
borde del ruido del juez (5,3 pts) y que el costo actual no justifica un router.
**Consecuencia**: no se implementa router; DeepSeek queda como generador único. El “trabajo futuro”
del blog menciona el router como línea abierta.
**Alternativas**: implementar el router igual (rechazada por el usuario con estos datos).

### D-08 — `vector_only` como default; léxico condicional
**Contexto**: con `voyage-4-lite`, el híbrido empeora Contextual Recall (−2,72) porque el léxico
desplaza contexto denso relevante.
**Decisión**: default `vector_only` en producción; el léxico se usa solo cuando la consulta tiene
carga léxica (códigos de error, comandos, IDs, versiones). Esa condición la decide el nodo
`analyze_query` del agente (M7).
**Consecuencia**: el híbrido deja de ser una estrategia global y pasa a ser una capacidad del agente.
**Alternativas**: calibrar el peso de fusión (RRF/convexo) en vez de desactivar el léxico — quedó
como mejora futura (M9), no se intentó.

### D-09 — Juez independiente del generador
**Contexto**: en M2 el juez era el mismo modelo que generaba (DeepSeek), lo que infla la
auto-consistencia. En M6/M4 final se pasó a `gpt-5.6-luna`.
**Decisión**: usar `gpt-5.6-luna` como juez en las corridas finales; documentar la comparación
DeepSeek vs Luna y tratar las cifras viejas como “subestimadas por el juez”.
**Consecuencia**: hay tablas de M2 con juez DeepSeek y de M4/M6 con Luna; **no son directamente
comparables**. El blog lo explicita en una nota metodológica.
**Alternativas**: re-ejecutar todo con un solo juez (caro y no aportaba al relato).

### D-10 — Un solo k para comparar
**Decisión**: k=10 en M4 final y M6, igual al default de producción, para que las 50 queries de M4
estén dentro del golden de 75 de M6 y las cifras sean comparables.
**Consecuencia**: no se exploró el efecto de k (queda para M9).

### D-11 — Blog con cifras trazables
**Decisión**: toda cifra publicada debe salir de un CSV/JSON/log en la carpeta `logs/` de la entrada.
Los notebooks de visualización solo grafican, no calculan métricas nuevas.
**Consecuencia**: cuando cambia el juez o se corrige una corrida, hay que regenerar tablas **y**
mover logs a la carpeta de la entrada correcta (pasó: logs `m2_*` mal ubicados en `3_.../logs`).

### D-12 — Groq → OpenRouter
**Contexto**: los límites de Groq quedaron chicos para evaluaciones largas.
**Decisión**: OpenRouter como proveedor único (generador y juez), con modelos nuevos registrados en
`api/available_models.json`.
**Consecuencia**: costo variable y dependencia de un agregador; el agente también se migró
(`ChatOpenAI` con `base_url` de OpenRouter).

### D-13 — Agente: LangGraph custom con feature flag
**Contexto**: el agente era un ReAct delgado que hacía una sola pasada de retrieval.
**Decisión**: grafo explícito de 5 nodos, estado tipado, `max_iterations=3`, y `USE_LEGACY_AGENT`
para poder volver al ReAct sin romper la app.
**Alternativa rechazada**: sub-agentes por nodo (el usuario conocía LangGraph y prefirió nodos con
responsabilidad única; se comparó ReAct vs grafo en el borrador del blog M7).

### D-14 — No usar git worktrees (por ahora)
**Decisión**: trabajo secuencial en una branch; los worktrees se evaluaron y se postergaron hasta
cerrar M2/M3.
**Consecuencia**: hay 3 stashes y varias branches vivas; el riesgo de pisarse es real.

### D-15 — Planes en repo separado `plans/`
**Contexto**: se quería versionar la planificación por separado y usarla como “product backlog”
(migración conceptual desde Azure DevOps/Jira a Issues de GitHub).
**Consecuencia**: `plans/` es un repo git anidado e **ignorado** por el principal → en un clone
limpio no existe. Acá se incluyó un snapshot, pero el historial sigue solo en el disco local.
**Recomendación**: para el nuevo harness, versionar los planes en el repo principal (o como submodule
explícito) y desactivar la regla `.gitignore:44`.
