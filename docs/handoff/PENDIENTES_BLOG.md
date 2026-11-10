# Pendientes editoriales de la serie de blogs

Nota dejada a pedido del autor: **no se aplicó ningún TODO ni corrección editorial** en las entradas.
Los archivos se commitean tal como estaban; el autor los revisa a mano y pide cambios explícitos.

Estado al 2026-11-09:

| Entrada | Milestone | Archivo | Estado | Qué falta |
|---|---|---|---|---|
| 0 | M0/M3 | `0_dataset_migration_intro/dataset_migration_intro_{es,en}.md` | Cerrada | Nada |
| 1 | M0 | `1_dataset_migration_EDA/dataset_migration_EDA_{es,en}.md` | Cerrada | Nada |
| 2 | M2 | `2_post_migration_eval/post_migration_eval_{es,en}.md` | Cerrada (versión final con juez independiente, traída de `feat/eval_pipeline`) | Nada |
| **3** | **M4** | `3_semantic_retrieval_improvements/semantic_search_optimization_{es,en}.md` | Cerrada y traducida; **recién ahora está en la línea de integración** | Ver abajo |
| **4** | **M6** | `4_cost_optimization/cost_optimization_es.md` | Revisada por el autor, casi cerrada | Ver abajo |
| 5 | M7 | `5_agentic_diagnosis/agentic_diagnosis_es.md` | Borrador (solo motivación y referencias) | Todo: resultados de la evaluación E2E, cierre narrativo y traducción |

---

## Entrada 3 — M4 (`semantic_search_optimization`)

La entrada está completa: resultados, análisis, trabajo futuro, referencias y pie de serie. Lo que
queda es **de auditoría, no de contenido**:

1. **Logs duplicados en dos carpetas.** Al consolidar las ramas, los mismos archivos `m2luna_*`
   quedaron en `2_post_migration_eval/logs/` y en `3_semantic_retrieval_improvements/logs/`
   (venían de dos líneas distintas). Decidir en cuál van y borrar la otra copia.
2. **`REVISAR_METRICAS_Y_BUDGET.md`** quedó en `3_.../logs/`. Es una nota de trabajo, no un log:
   decidir si se conserva, se mueve o se borra.
3. **Referencia al EDA.** La imprecisión detectada al cierre de M4 se corrigió en el notebook
   (`documentation/notebooks/eda_stackexchange_corpus.ipynb`, commit `docs(eda): correct imprecision
   found during M4 close-out`), pero el autor había pedido **no** tocar el EDA por algo menor.
   Revisar si esa corrección se queda o se revierte.

## Entrada 4 — M6 (`cost_optimization_es.md`)

Es la que quedó a medio terminar. Lo que el autor ya había corregido (y está en el archivo):

- Test KS reformulado a 90/95% de confianza (ya no dice “casi”).
- Párrafo del 68% reescrito con precios y tokens actuales.
- Argumento de latencia de Gemini como hallazgo operativo.
- Nota metodológica sobre k y varianza del juez.

Lo que falta:

1. **Un TODO explícito** en la línea 27: “Reemplazar tabla con algún gráfico robado del EDA.”
   (la tabla de percentiles de longitud de respuesta).
2. **Traducción al inglés** (`cost_optimization_en.md`): no existe.
3. Lectura final del autor sobre el resto de los FIXMEs que había planteado (precios, redacción).

## Entrada 5 — M7 (`agentic_diagnosis_es.md`)

Solo tiene motivación, comparación de arquitecturas y referencias. No se puede cerrar hasta correr
la evaluación E2E del agente. Decisión del 2026-11-09: **M7 se termina**, no se descarta.

---

## Estado de M7 (2026-11-09)

Hechos verificados, sin recomendaciones:

1. La evaluación de M7 **no se ejecutó**. No hay números y la entrada 5 sigue siendo un borrador
   sin resultados.
2. El harness de evaluación del agente **no existe**: `api/scripts/run_eval.py` habla con
   `/api/raw_unified_search` + `/api/augment_search_results`, nunca con `/chat/`.
3. Condiciones técnicas que debe cumplir cualquier driver que se escriba:
   - autenticarse con **JWT Bearer** contra `/api/me` (el agente no acepta `X-API-KEY`);
   - abrir **una sesión por pregunta** (el checkpointer persiste por `thread_id`);
   - fijar **`AGENT_SEARCH_K=10`** para igualar el protocolo de M4/M6;
   - medir latencia del lado del cliente (el servicio la calcula pero solo la loguea en Mongo);
   - extraer iteraciones y documentos acumulados del `trace` (hoy son strings de UI).
4. `AGENT_SEARCH_K` es la parametrización del `k` del tool: default **3** (producción), `10` para
   evaluar. Implementada en `agent_app/backend/tools/advanced_search.py` (commit `9ae6ba2`).
5. Trampa conocida: crear sesión dispara `generate_session_title` (llamada LLM extra) que no entra
   en la latencia medida por el servicio pero sí en la del cliente.
