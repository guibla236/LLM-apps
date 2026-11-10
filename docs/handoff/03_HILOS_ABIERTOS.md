# 03 — Hilos abiertos y cómo retomarlos

Cada hilo tiene: **estado real**, **evidencia**, **próximo paso concreto** y **riesgo si se ignora**.
Ordenados por prioridad de retomada.

---

## H-01 — Evaluación E2E del agente M7 (lo más importante que falta) — **DECIDIDO: terminar**

**Estado**: implementación completa, **sin números**. El borrador del blog
(`documentation/markdowns/5_agentic_diagnosis/agentic_diagnosis_es.md`) tiene secciones de motivación
y referencias, y un cartel “Implementación y resultados pendientes de ejecución (M7)”.

**Evidencia**: `plans/M7_Agent/02_Agent_Evaluation.md` define el protocolo; `agent_app/backend/`
tiene el grafo; `ROADMAP.md` → M7 “Pending”.

**Próximo paso**
1. Levantar API (`uvicorn`) y el backend del agente.
2. Correr los mismos 50 pares de M4 (`golden_se_200.json`, seed 42) contra `POST /chat/`.
3. Evaluar con `gpt-5.6-luna` las 3 métricas de generación (Correctness, Faithfulness,
   AnswerRelevancy) — no las contextuales, porque el retrieval no cambió.
4. Calcular las métricas propias del agente: iteraciones promedio, % con >1 iteración, latencia,
   documentos acumulados.
5. Completar la entrada 5 con tabla comparativa M4 baseline vs agente.

**Riesgo**: sin esto la serie queda sin final y el “portfolio” no demuestra la tesis del M7.

**Nota**: el usuario adelantó (2026-11-09) que parte de lo en curso se cancela y se retoma con otro
workflow. **Confirmar antes de ejecutar**: puede que esta evaluación se redefina (otro golden, otro
juez, u otro alcance). El protocolo de arriba es el que estaba acordado al 2026-08-19.

---

## H-02 — Entrada de blog M6: pendientes editoriales — **delegado al autor**

**Estado**: el blog ES está escrito y es el más completo de la serie, pero el último turno de la
conversación se interrumpió cuando el usuario respondía los FIXMEs. Quedaron planteados:

1. La prueba de hipótesis “casi” al 5% **no es defendible**: hacerla también al 10% y redactar en
   términos de confianza 90/95%, explicando qué es un test de hipótesis.
2. Verificar si la entrada del EDA menciona el supuesto de precios de modelos; **recalcular con
   precios actuales** en vez de heredar los del EDA.
3. Dejar TODOs explícitos donde se usan precios/modelos de abril.
4. FIXME mal ubicado (línea 41 vs 35): reformular la aproximación del router 25/25/25.
5. Redacción del párrafo del 68% (líneas 33–37): “no se entiende nada, mezcla cosas, adelanta
   resultados”.
6. Explicar mejor que se reutilizaron 50 queries y se re-agruparon para cubrir cuartiles.
7. Re-verificar cambios de precios (no solo OpenCode y DeepSeek).
8. Argumentar mejor por qué **no** se puede invalidar a Gemini por respuesta corta a pesar de su
   latencia (el usuario no quedó convencido).
9. Mejorar redacción general.

**Evidencia**: turnos 474–477 de la sesión principal
(`digests/D3_7b0f645a_M1_a_M7.md`, sección “Estado final”), y el propio archivo del blog.

**Próximo paso**: resolver 1–9 con datos actuales de OpenRouter y regenerar la tabla de costos.
Después: traducción EN (no existe).

**Riesgo**: es la entrada con cifras más sensibles (precios, latencia); publicarla con datos de abril
de 2026 sería un error fácil de detectar por un reclutador.

---

## H-03 — Cierre de portfolio (issue #13)

**Estado**: nunca se hizo. `README.md` de la raíz es de marzo y no menciona la serie.
**Próximo paso**: README con índice de la serie (entradas 0→5), stack, resultados clave, links a
logs y a notebooks; agregar el proyecto al portfolio personal.
**Riesgo**: todo el trabajo de blog no se descubre desde el repo.

---

## H-04 — Cambios sin commitear que rompen seguridad — **RESUELTO 2026-11-09**

**Estado**: en el working tree, `api/app.py` tiene **todos los `@limiter.limit` comentados** y
`api/modules/security.py` tiene **comentadas las cuotas por IP y por usuario**. Fue un workaround para
correr benchmarks sin 429.

**Próximo paso**: revertir esos dos archivos a `HEAD` (conservando solo la traducción de mensajes de
error si se quiere) y re-correr un smoke test. Nunca commitear como está.
**Riesgo**: deploy accidental = API sin rate limit ni cuotas.

---

## H-05 — 57 commits sin remoto — **RESUELTO 2026-11-09**

**Estado**: `feat/cost-optimization-benchmark` no tiene upstream y no existe en `origin`.
**Próximo paso**: `git push -u origin feat/cost-optimization-benchmark` (o merge a una branch
publicada), antes de cualquier migración de harness.
**Riesgo**: pérdida total de M4–M7 si falla el disco.

---

## H-11 — El blog de M4 no está en la rama actual — **RESUELTO 2026-11-09**

**Estado**: `documentation/markdowns/3_semantic_retrieval_improvements/semantic_search_optimization_es.md`
y `_en.md` **no existen** en `feat/cost-optimization-benchmark`. Fueron commiteados el 2026-08-17 en
`feat/search-optimization` (`3ac9864`), que está **4 commits por delante** de la rama actual:

```
5c9ecbe  logs de M4 + reemplazo de juez deepseek por gpt-5.6-luna
3ac9864  artículos de search optimization ES+EN
9ff74c6  chore: bm25 index removal from repo
42735d0  logs de evaluación olvidados
```

La rama actual tiene, a su vez, 3 commits que no están en `feat/search-optimization`
(`0b6c6dd`, `78de0d6`, `ce9a72b` — tooling del benchmark M6).

**Hallazgo posterior (2026-11-09)**: el código de **M7** tampoco está en la rama actual; vive en
`feat/agentic-rag-implementation` (9 commits, 2026-08-16), que contiene M6 pero no el blog M4.
La consolidación completa está en [`06_RAMAS_Y_ARTEFACTOS.md`](./06_RAMAS_Y_ARTEFACTOS.md).

**Próximo paso**: mergear `feat/search-optimization` en la rama actual (o al revés) **antes** de
cualquier otra cosa; verificar que la entrada 3 y sus logs queden en el árbol final.

**Riesgo**: creer que la entrada 3 “está escrita y traducida” (lo dice el ROADMAP) y descubrir
después de la migración que el archivo no viajó. Es el artefacto más costoso de rehacer de toda la serie.

---

## H-06 — `plans/` fuera del repo principal

**Estado**: repo git anidado, ignorado por `.gitignore:44`. Tiene 3 archivos modificados sin commit.
**Próximo paso**: decidir entre (a) versionar `plans/` en el repo principal, (b) submodule, o
(c) dejar el snapshot de `docs/handoff/planes/` como copia de lectura.
**Riesgo**: el próximo agente en otro harness **no verá los planes**.

---

## H-07 — Experimento `EXPAND_CONTEXT` sin conclusión

**Estado**: `api/modules/rag_unified_retriever.py` tiene la expansión de contexto implementada y
apagada por default; se corrieron `p0_luna` y `p1_expanded_luna` (logs sin commitear).
**Próximo paso**: decidir si se documenta como hallazgo (los logs están), se descarta o pasa a M9.
**Riesgo**: código muerto que confunde; y logs que se pierden por no estar commiteados.

---

## H-08 — Logs y métricas desordenados

**Estado**: hay CSVs `m2_*` en la carpeta de la entrada 3, logs nuevos en `3_.../logs/` sin commitear,
y `REVISAR_METRICAS_Y_BUDGET.md` suelto.
**Próximo paso**: mover cada corrida a la carpeta de la entrada que la cita (regla D-11) y commitear.
**Riesgo**: tablas del blog sin trazabilidad → exactamente lo que el usuario prohíbe.

---

## H-09 — Entrada 5 en inglés y coherencia de la serie

**Estado**: entradas 0–3 en ES+EN; 4 solo ES; 5 solo borrador ES.
**Próximo paso**: traducir 4 (y 5 cuando tenga resultados) y hacer una pasada de coherencia entre
entradas (numeración, referencias cruzadas, promesas que cada una hace a la siguiente).

---

## H-10 — Deuda diferida que conviene decidir explícitamente

| Ítem | Estado | Recomendación |
|---|---|---|
| M5 CI/CD eval | diferido | borrar del roadmap o hacerlo en 1 día con GitHub Actions |
| M8 Pinecone → MongoDB | diferido, con plan escrito | si no se retoma, archivar el plan |
| M9 mejoras arquitectónicas | diferido | ídem |
| Router M6 | descartado con datos | dejarlo como “trabajo futuro” en el blog |
| Stashes (3) | sin dueño | revisar y descartar o convertir en branches con nombre |

---

## Lo que el usuario pidió explícitamente NO hacer

- No inventar ni estimar métricas: cada número sale de un log.
- No explicitar en el blog omisiones básicas del proceso (ej.: “olvidé actualizar el prompt”).
- No cambiar el EDA por imprecisiones menores sin evaluar el costo/beneficio.
- No usar comandos que el usuario no pueda ver en qué terminal corren.
- No commitear sin que él revise (en general propone él los commits).
