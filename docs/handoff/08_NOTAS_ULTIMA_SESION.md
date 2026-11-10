# 08 — Notas de la última sesión (2026-11-10)

Escrito para quien retome el proyecto en la Raspberry Pi. **Sólo hechos verificados esa tarde**, con
la evidencia al lado. Nada de recomendaciones: eso es decisión de quien siga.

---

## 1. Lo que se verificó contra servicios reales

Con la API en `:8000`, el agente en `:8001` y MongoDB/Pinecone/OpenRouter online:

| Prueba | Resultado |
|---|---|
| `GET /api/me` con `X-API-KEY` | 200 |
| `POST /api/raw_unified_search` (`vector_only`) | 3 resultados `SE-SERVERFAULT-*` |
| `POST /api/raw_unified_search` (`hybrid`) | 3 resultados (Atlas Search activo) |
| `POST /api/augment_search_results` | respuesta de 1470 chars, citando IDs `SE-*` |
| `POST /chat/` del agente (JWT) | 200, 10 eventos de traza, 5 documentos acumulados, respuesta de 3796 chars |
| `qa_pairs` en Mongo | **60.161** documentos |

## 2. El bug que se corrigió (y por qué importaba)

`agent_app/backend/tools/advanced_search.py` hacía `data.get("results", [])`, pero
`/api/raw_unified_search` devuelve una **lista** de strings. Cada búsqueda lanzaba
`Error executing search: 'list' object has no attribute 'get'`, el nodo registraba `0 new results` y
el agente respondía **sin contexto recuperado**.

Era silencioso: el agente decía "no encontré información" en vez de reportar el error. Una evaluación
de M7 habría medido un agente ciego. Corregido en `e119cfd`.

## 3. Hallazgo abierto: el juez de suficiencia nunca converge

Traza exacta de la corrida de verificación (`/chat/`, consulta sobre `ssh permission denied`):

```
analyze  | estrategia: hybrid
search   | 3 new results, 3 total accumulated
evaluate | sufficient=False, gaps identified (3)
refine   | ...
search   | 1 new results, 4 total accumulated
evaluate | sufficient=False, gaps identified (3)
refine   | ...
search   | 1 new results, 5 total accumulated
evaluate | sufficient=False, gaps identified (3)
generate | respuesta final
```

Contexto recuperado en la última iteración: incluía `SE-SERVERFAULT-c8f324ec7540`, cuyo contenido trae
la solución exacta (`chown 1001:1002 ...`). Aun así el juez dijo `sufficient=False` en las tres
evaluaciones y el grafo llegó a `max_iterations = 3`.

**Consecuencia medible**: si esto se repite en las 50 consultas del protocolo, la métrica
"% de consultas con más de 1 iteración" daría 100% y cada consulta costaría 3 búsquedas + 3 llamadas
de juez + 3 de refinamiento. El prompt (`prompts/evaluate_prompt.md`) pide que `sufficient` sea `true`
*"ONLY if the context contains the specific solution … exact commands, error-code explanations, or
step-by-step fix"*.

**No se tocó**: es una decisión de calibración. Antes de lanzar la evaluación conviene medir cuántas
consultas llegan a 3 iteraciones (el campo está en la traza) y decidir si el criterio es el buscado.

## 4. Trampa operativa: la cuota diaria bloquea las búsquedas

El usuario `test` tenía `daily_usage = 2789` con `quota_limit = 200`. `/api/raw_unified_search`
responde 429 y **el tool del agente traduce eso a "no results"**, no a error. Para verificar hubo que
resetear `users.daily_usage` en Mongo y restaurarlo después.

Si la evaluación se lanza sin revisar esto, todos los resultados serán vacíos y parecerá un problema
de retrieval.

## 5. Particularidades de M7 que no están en el código obvio

- `/chat/` exige **JWT Bearer** validado contra `{API_BASE_URL}/api/me`. No acepta `X-API-KEY`.
- `API_BASE_URL` en `agent_app/backend/.env` apunta a `:8000`; si la API corre en otro puerto, el
  agente responde `401 "Could not connect to auth service"`.
- El checkpointer persiste por `thread_id` (`username_session_id`): **una sesión por pregunta** en
  cualquier driver de evaluación, o las respuestas se contaminan entre consultas.
- Crear sesión dispara `generate_session_title`, una llamada LLM extra que **no** entra en la latencia
  que mide el servicio.
- `AGENT_SEARCH_K` (default 3) fija el `k` del tool. Para comparar con M4/M6 hay que ponerlo en 10.
- El nodo `analyze` elige `hybrid` cuando detecta nombres de comando, y `ssh` está en la lista del
  prompt: consultas con `ssh` van por híbrido aunque no tengan códigos de error.

## 6. Raspberry Pi

- Todas las dependencias tienen wheels `aarch64` para cp312 y cp313 (verificado contra PyPI).
- Requiere **glibc ≥ 2.28**: `pyarrow`, `numpy` y `tiktoken` sólo publican `manylinux_2_28_aarch64`.
  `bootstrap_envs.sh` avisa si no se cumple.
- Los `requirements.lock.txt` commiteados son un freeze de **Python 3.12 en x86_64**. Regenerarlos
  en la Pi (`--recreate --lock`) antes de confiar en ellos.

## 7. Herramientas agregadas en esa sesión

| Archivo | Para qué |
|---|---|
| `scripts/bootstrap_envs.sh` | crea/verifica los tres venvs; `--check` no instala nada |
| `api/requirements.eval.txt` | eval e ingesta, separado del runtime |
| `requirements.lock.txt` × 3 | freeze exacto (snapshot de 3.12/x86) |
| `run_all.sh` | ahora bootstrapea si faltan venvs y usa el intérprete de cada uno |
