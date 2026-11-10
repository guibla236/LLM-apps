# D7 — Antecedentes: cómo se construyó el sistema antes de la migración (feb–may 2026)

Resumen agrupado de las conversaciones que explican el estado del código al llegar julio.
No hace falta leerlas para continuar, salvo que se toque auth, deploy o los evaluadores viejos.

---

## `ebe75f64` — Planificación de la ampliación del servicio
**Fechas**: 2026-02-20 → 02-22 · **54 turnos** ·
[transcripción](../transcripciones/ebe75f64-c0d0-4c2b-befa-bcbcd734062f.md)

- Planifica la ampliación del RAG a un servicio multi-endpoint: ingesta, UI de administración,
  control de acceso, cuotas y API keys.
- Decisiones que quedaron en el código: separar **validación de API key** (endpoints de datos e
  ingesta) de **validación de cuota** (endpoints que consumen LLM); ingesta de tickets solo en local;
  KBs como archivos `.md`; una única variable de entorno para el índice de KBs (“si falla, que no
  haya plan B”); se descarta Redis por complejidad.
- Es el origen de `security.py`, de la UI admin y de los endpoints que hoy tienen rate limit.
- **Relevante ahora**: explica por qué los `@limiter.limit` existen y por qué desactivarlos es
  peligroso (H-04).

## `6438c89e` — Notebook evaluador con Ragas
**Fechas**: 2026-03-02 → 03-05 · **39 turnos** ·
[transcripción](../transcripciones/6438c89e-1e1d-4b1d-8bb8-971d484102ff.md)

- Primer evaluador serio (Ragas en Colab). Problemas de warnings, métricas sin barra, timeouts y
  generación de ground truths por pipeline (que reintroduce el sesgo del generador).
- Deja la discusión “ground truth generado vs ground truth real” que después justifica Stack Exchange.

## `1653f8a5` — Comparación finetuning vs RAG
**Fechas**: 2026-03-17 → 04-12 · **65 turnos** ·
[transcripción](../transcripciones/1653f8a5-190d-457c-90d9-6508b5b15fc3.md)

- Diseña el experimento de un LLM con finetuning sobre tickets versus el RAG, con el mismo golden.
- Aparece el problema del idioma (datos en español, prompt estandarizado en inglés) y la elección de
  hiperparámetros.
- **Relevante**: es la línea de trabajo que quedó fuera de la serie actual; si se retoma, hay que
  decidir si entra como entrada extra o se descarta.

## `d58971f1` — Notebook de finetuning
**Fecha**: 2026-03-03 · **4 turnos** · [transcripción](../transcripciones/d58971f1-2d3a-4ce3-ab3b-d4b6435c7704.md)
Preparación del JSON de tickets y del notebook de finetuning (complemento del anterior).

## `c98d77b8` + `9ea32553` — Anatomía y grafo del agente
**Fechas**: 2026-04-14 · **11 + 2 turnos** ·
[c98d77b8](../transcripciones/c98d77b8-7d95-45eb-8cf0-a18f65803f8d.md) ·
[9ea32553](../transcripciones/9ea32553-771e-468e-8858-a0e9075efbe8.md)

- Explicación de librerías del `agent_app` (LangChain + LangGraph, checkpointer MongoDB).
- Generación automática del diagrama del grafo al iniciar el servicio (`agent_graph.png`).
- Surge la pregunta “¿qué tan difícil sería migrar a un grafo custom?” → semilla del M7.
- Corrección: el venv es `backend_venv`.

## `a1415846` + `b213dd16` — Resiliencia del evaluador y análisis de 429
**Fechas**: 2026-03-29 → 03-30 · **16 + 3 turnos** ·
[a1415846](../transcripciones/a1415846-f0af-42a0-b2ee-ff92d9005075.md) ·
[b213dd16](../transcripciones/b213dd16-b96a-4b6b-8f37-7ebc13e3d2d5.md)

- Qué pasa si DeepEval recibe un 429 → reintentos, guardado incremental del CSV, reanudación.
- Análisis de `eval_results_290326.csv`: qué preguntas fallaron por métrica y cuáles por cuota.
- **Es el diseño que después se implementó en `run_eval.py`** (reintentos + `--append-to`).

## `6f8ab41f` — Deploy en Vercel
**Fecha**: 2026-03-15 · **15 turnos** · [transcripción](../transcripciones/6f8ab41f-bf87-4d2d-b0dd-e9c36aaa7009.md)

- `uv lock` sin solución, límite de 500 MB de Lambda, limpieza de `requirements.txt` (se crea
  `requirements.dev.txt`).
- **Relevante**: si se vuelve a deployar, el tamaño de dependencias sigue siendo el límite.

## `f90b2315` — Validador de token
**Fecha**: 2026-02-28 · **4 turnos** · [transcripción](../transcripciones/f90b2315-2dba-45b9-aa32-4cd993a380ef.md)
Origen de la validación de JWT/API key en `security.py`.

## `dd25704a` — Crítica a la evaluación y elección de proveedor (2026-07-10, 4 turnos)
[transcripción](../transcripciones/dd25704a-371c-4e15-9f86-ef32975e8d71.md)

- Punto de partida: “la evaluación del RAG no está bien lograda”, el endpoint de evaluación es caótico
  y devuelve un CSV que después hay que analizar a mano. Es la queja que origina el evaluador
  standalone de M2.
- Discusión de proveedores: OpenCode Go vs Groq. Diagnóstico del usuario: “Groq tiene modelos viejos
  y cada vez menos”. De ahí sale la migración a **OpenRouter** (D-12), que después se extiende al
  agente y al juez.
- Relevante para entender por qué el evaluador y el proveedor cambiaron antes del M2.

## `9bd068ad`, `b46b55d3`, `c5e2b8a1`, `a6d603df`, `d7ad1680`, `480a4e19`, `da883487`
Sesiones cortas de soporte a notebooks de evaluación (Kaggle, gráficos, exports de CSV, latencia en
el output). Aportan contexto menor; están indexadas en [`../transcripciones/README.md`](../transcripciones/README.md).
