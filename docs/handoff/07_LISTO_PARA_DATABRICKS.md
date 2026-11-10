# 07 — ¿Está todo listo para migrar las evaluaciones a Databricks?

Chequeo de preparación hecho el 2026-11-09. Respuesta corta: **el protocolo y los artefactos están
listos; el driver de evaluación no**. Lo que falta es acotado y está listado abajo.

---

## Listo para usar desde un clúster

| Activo | Estado | Dónde |
|---|---|---|
| Golden sets deterministas | ✅ | `evaluation_notebooks/goldens/` — `golden_se_200.json` (200), `golden_se_75_estratificado.json` (75), `golden_se_50_m4.json` |
| Protocolo de evaluación escrito | ✅ | `plans/M7_Agent/02_Agent_Evaluation.md` (agente), `plans/M2_Evaluation/`, `plans/M4_SearchOptimization/` |
| Definición de métricas y juez | ✅ | Correctness / Faithfulness / AnswerRelevancy (+ Contextual Precision/Recall para retrieval), juez `openai/gpt-5.6-luna` |
| Contrato de artefactos | ✅ | CSV por pregunta + `*_aggregate.json` (estructura abajo) |
| Runner de referencia | ✅ | `api/scripts/run_eval.py` (flags, reintentos, `--append-to`, chequeo de saldo) |
| Dependencias fijadas | ✅ | `api/requirements.txt` (21 líneas) y `api/requirements.dev.txt` (229) con versiones exactas (`deepeval==3.8.9`) |
| Costos estimados | ✅ | ~$0.60/50 pares (optimista), ~$1–3 realista |
| Decisiones metodológicas registradas | ✅ | `docs/handoff/02_DECISIONES.md` (D-09 juez independiente, D-10 k=10, D-07 sin router) |

### Contrato de artefactos (lo que un job debe producir igual)

```
CSV por pregunta:
timestamp,question,ticketId,kb,contextual_precision,contextual_recall,
faithfulness,answer_relevancy,correctness,retrieval_secs,generation_secs,
judge_secs,total_secs,output_chars,output_tokens

*_aggregate.json:
total_questions, timestamp, <métrica>: {mean, median, std, min, max, count}
```

## Lo que falta

| # | Falta | Impacto | Esfuerzo |
|---|---|---|:--:|
| 1 | **Eval core desacoplado.** `run_eval.py` tiene el HTTP hardcodeado a `/api/augment_search_results` y `/api/raw_unified_search`. No hay una interfaz `answer(question) -> dict`. | Sin esto, el job de Databricks es un fork del script, no un driver. | Medio día |
| 2 | **Driver del agente M7.** No existe nada que llame a `/chat/`, y ese endpoint exige **JWT Bearer** validado contra `/api/me` (no acepta `X-API-KEY`). | La entrada 5 no se puede cerrar. | 1 día |
| 3 | **Sesión por pregunta.** El checkpointer persiste por `thread_id`; reutilizar sesión contamina la pregunta siguiente. Además, crear sesión dispara `generate_session_title` (LLM extra que no entra en la latencia medida por el servicio). | Números inválidos si se ignora. | Incluido en #2 |
| 4 | **`k` del agente.** Hoy default 3; para comparar con M4/M6 hay que setear `AGENT_SEARCH_K=10`. | Mezcla “agente” con “menos contexto”. | ✅ Ya parametrizado |
| 5 | **Métricas del agente.** Iteraciones y documentos acumulados salen del `trace`, que son strings de UI. | Parseo frágil. | 2 h |
| 6 | **MLflow.** No está en ninguna dependencia ni hay tracking configurado. | Sin esto, Databricks aporta orquestación pero no trazabilidad. | 2 h |
| 7 | **Empaquetado.** `api/` no tiene `pyproject.toml` ni `setup.py`. En el clúster habría que `%pip install -r` y agregar el repo al `sys.path`, o construir un wheel. | Fricciona el primer job. | 2 h |
| 8 | **Requirements de evaluación.** `requirements.dev.txt` tiene 229 líneas con Jupyter/matplotlib; no es apto para clúster tal cual. Falta un `requirements.eval.txt` mínimo (deepeval, langchain, httpx, requests). | Arranque lento y conflictos con el runtime. | 1 h |
| 9 | **Versión de Python fijada.** `.devcontainer` usa 3.11, los venv locales son 3.12, y Databricks Runtime trae su propia versión. | Conflictos difíciles de diagnosticar. | Decisión, 10 min |
| 10 | **Secret management.** No hay `.env.example`. Las variables están documentadas en `04_COMO_CONTINUAR.md` pero no hay plantilla. Los secret scopes de Databricks serían el reemplazo. | Onboarding manual y riesgo de claves filtradas. | 1 h |
| 11 | **Mongo no resuelve.** La URI de `agent_app/backend/.env` apunta a `cluster0.3kfr8t9.mongodb.net`, que **no resuelve DNS**. | Ni local ni remoto arranca el agente. | Bloqueante, 15 min |
| 12 | **Allowlist de red.** Pinecone y Atlas tienen que aceptar la IP de salida del clúster (serverless no siempre es estática). | El job falla en la primera llamada. | Configuración |

## Bloqueante previo a cualquier corrida

```
1. URI de MongoDB válida (hoy no resuelve).
2. API principal desplegada y alcanzable desde el clúster (el agente valida JWT contra /api/me).
3. Índice Atlas Search `default` creado en el cluster de Mongo.
4. Saldo/limit de OpenRouter para ~50 queries × (4 llamadas del agente + 3 del juez).
```

## Recomendación de secuencia

1. Arreglar credenciales y verificar que API + agente levantan en local (bloqueante #11).
2. Extraer el eval core con interfaz `answer(question) -> dict | AnswerResult` (#1).
3. Driver del agente con sesión aislada y JWT (#2, #3, #5).
4. `requirements.eval.txt` + decisión de versión de Python (#8, #9).
5. MLflow con tracking local por defecto y remoto por env var (#6).
6. Recién entonces el Job de Databricks, con secret scopes (#10, #12).

Los puntos 1–3 son también lo que necesita cualquier corrida local: **hacer el core desacoplado no es
trabajo específico de Databricks, es trabajo pendiente del proyecto**.
