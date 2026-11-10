# 04 — Cómo continuar (guía práctica)

Orientada a “primer día en el nuevo harness”. Asume que el repo se clona o se abre tal cual está.

---

## 1. Chequeo de realidad antes de tocar nada (15 min)

```bash
cd <repo>
git status                      # esperado: rama feat/cost-optimization-benchmark, sin upstream
git log --oneline -5
git stash list                  # 3 stashes de agosto
git -C plans log --oneline -3   # repo anidado, si existe en el disco
```

1. **Pushear la rama actual** antes de cualquier cosa (H-05).
2. Revisar que `plans/` exista; si no, usar el snapshot `docs/handoff/planes/` (H-06).
3. Decidir qué hacer con el working tree (H-04, H-07, H-08). No arrastrar el workaround de rate
   limits a ningún commit.

## 2. Entorno

Un solo comando, desde la raíz del repo:

```bash
./scripts/bootstrap_envs.sh                      # crea los venvs que falten
./scripts/bootstrap_envs.sh --recreate           # borra y rehace los tres
./scripts/bootstrap_envs.sh --only api --with-dev --lock   # API + eval + notebooks
./scripts/bootstrap_envs.sh --check              # verifica sin instalar nada
```

Crea tres entornos aislados con Python 3.12 o 3.13 (auto-detecta):

| Target | Venv | Requirements |
|---|---|---|
| `api` | `api/tarea2` | `api/requirements.txt` (+ `eval` / `dev` opcionales) |
| `backend` | `agent_app/backend/backend_venv` | `agent_app/backend/requirements.txt` |
| `frontend` | `agent_app/frontend/frontend_venv` | `agent_app/frontend/requirements.txt` |

### Cómo está partido `api/`

| Archivo | Para qué | Quién lo usa |
|---|---|---|
| `api/requirements.txt` | **runtime**: lo que se despliega en Vercel | producción, `uvicorn` |
| `api/requirements.eval.txt` | evaluación e ingesta | `run_eval.py`, `ingest_stackexchange_dataset.py`, `benchmark_embeddings.py` |
| `api/requirements.dev.txt` | tooling y notebooks | desarrollo local: pytest, ruff, jupyter, matplotlib |
| `api/requirements.lock.txt` | freeze exacto (incluye transitivos) | reproducir bit a bit en Python 3.12 |

Los `requirements.lock.txt` se generan con `--lock` y llevan la versión de Python en la cabecera:
**son un snapshot de 3.12**. En 3.13 el bootstrap instala desde los `requirements.txt` curados (todos
los pins tienen wheels cp313, verificado) y conviene regenerar el lock ahí.

### Variables de entorno

| Archivo | Variables clave |
|---|---|
| `api/.env` | `OPENROUTER_API_KEY`, `PINECONE_API_KEY`, `MONGODB_URI`, `MONGODB_DB_NAME`, `APP_API_KEY`, `JWT_SECRET`, `ATLAS_SEARCH_INDEX`, `TICKETS_TO_CONSIDER`, `KBS_TO_CONSIDER` |
| `agent_app/backend/.env` | `APP_API_KEY`, `API_BASE_URL`, `MONGODB_URI`, `AGENT_MODEL`, `AGENT_SEARCH_K` (opcional), `LANGSMITH_*` |
| `agent_app/frontend/.env` | URL del backend / API |

> Rotar credenciales: estuvieron expuestas en logs de chat (ver README, advertencia 4).

## 3. Verificación mínima de que el sistema está sano

```bash
curl -s localhost:8000/ | head
# smoke de retrieval (requiere APP_API_KEY)
curl -s -X POST localhost:8000/api/raw_unified_search \
  -H "Content-Type: application/json" -H "X-API-KEY: $APP_API_KEY" \
  -d '{"query":"ssh permission denied publickey","k":5,"search_method":"vector_only"}' | head
```

Si devuelve documentos con `community` y `expected_output`, el índice `kb-se-all` está bien cableado.
Si devuelve tickets en español o KBs, está apuntando al namespace legacy.

## 4. Correr una evaluación (el loop central del proyecto)

```bash
cd api
./scripts/run_m2_eval.sh        # M2: vector_only + hybrid, juez deepseek (comparabilidad histórica)
./scripts/run_m6_benchmark.sh   # M6: 3 generadores, juez luna, k=10, golden 75
```

Reglas que estos scripts ya implementan y hay que preservar:

- **La API se reinicia entre corridas** que cambian índice, embeddings o modelo (hay caché en memoria).
- **Chequeo de saldo** de OpenRouter antes de lanzar (si se corta el crédito, el eval se reanuda con
  `--append-to`).
- **Salida siempre a `evaluation_notebooks/raw_results/`** con CSV + `_aggregate.json` + `.log`.
- `--limit 5` para humo, `--append-to` para reanudar, `--metrics` para recortar costo.

Ejemplo directo del evaluador:

```bash
python scripts/run_eval.py \
  --golden-json ../evaluation_notebooks/goldens/golden_se_200.json \
  --scenario-name m4_p1_final --search-method vector_only --search-type tickets_only \
  --k 10 --limit 50 --judge-model openai/gpt-5.6-luna \
  --metrics correctness faithfulness answer_relevancy contextual_precision contextual_recall
```

## 5. Convenciones de trabajo que el usuario exige

| Tema | Regla |
|---|---|
| Métricas | Todo número del blog se traza a un CSV/JSON/log. Nada estimado. |
| Commits | Un tema por commit, mensaje `tipo(scope): ...` en inglés; el usuario suele commitear él. |
| Blogs | ES + EN, narrativa de serie, se admiten resultados negativos. |
| Terminales | No lanzar comandos en terminales que el usuario no pueda identificar. |
| Procesos largos | Avisar, dejar logs en vivo, no bloquear la sesión. |
| Costos | Consultar saldo antes de corridas grandes y registrar el costo de cada eval. |
| EDA | No tocarlo por imprecisiones menores sin evaluar el impacto en la narrativa. |

## 6. Plan sugerido para el nuevo harness

**Semana 1 — estabilizar**
1. Pushear rama y crear upstream.
2. Separar el workaround de seguridad; commitear o descartar el resto del working tree.
3. Versionar `plans/` en el repo principal y commitear `ROADMAP.md`.
4. Ordenar logs por entrada de blog y commitear las entradas 4 y 5 en borrador.

**Semana 2 — cerrar la serie**
5. Resolver los 9 FIXMEs del blog M6 con precios vigentes (H-02).
6. Evaluación E2E del agente M7 (H-01) — **previa confirmación del alcance con el usuario**.
7. Traducciones EN de 4 y 5 y pasada de coherencia.

**Semana 3 — portfolio**
8. README/portfolio (#13).
9. Decidir destino de M5/M8/M9 y de los 3 stashes (H-10).

## 7. Dónde NO perder tiempo

- No re-ejecutar M1 (la ingesta está hecha y verificada: 60.161 docs / 81.599 vectores).
- No re-discutir D-03 (filtro/namespace) ni D-08 (`vector_only` default): ya están sostenidos con datos.
- No buscar el “router híbrido” de M6: se descartó a propósito.
- No leer las 59 transcripciones: usá digests + grep.
