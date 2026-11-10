# Handoff — RAG → RAG agéntico (portfolio)

Paquete de traspaso para continuar este proyecto en otro harness/agente.
**Fecha de corte del estado documentado: 2026-08-19** (último turno de la conversación principal).
Paquete armado: 2026-11-09.

> **Leé esto primero.** Este directorio no es documentación del producto: es el *contexto operativo*
> que el agente anterior tenía en la cabeza. La documentación del producto (las entradas de blog)
> está en [`documentation/markdowns/`](../../documentation/markdowns/).

---

## Qué es el proyecto (en 5 líneas)

Un RAG de soporte IT de nivel 1 que evoluciona en etapas publicadas como entradas de blog
(ES + EN), pensado como portfolio para búsqueda laboral de AI Engineer. La serie arranca con un
RAG simple sobre datos sintéticos, migra a un corpus real de Stack Exchange, mide con DeepEval,
optimiza retrieval/embeddings, mide costos de inferencia y cierra con un agente de diagnóstico
multi-paso sobre LangGraph.

## Orden de lectura recomendado

| # | Documento | Para qué |
|---|---|---|
| 1 | [`00_ESTADO_ACTUAL.md`](./00_ESTADO_ACTUAL.md) | Qué está hecho, qué no, en qué rama y con qué riesgo |
| 2 | [`01_HISTORIA_POR_ETAPA.md`](./01_HISTORIA_POR_ETAPA.md) | Qué se pretendió en cada etapa y qué se obtuvo |
| 3 | [`03_HILOS_ABIERTOS.md`](./03_HILOS_ABIERTOS.md) | Qué quedó a medias, qué se cancela y cuál es el próximo paso |
| 4 | [`02_DECISIONES.md`](./02_DECISIONES.md) | Decisiones tomadas y alternativas descartadas (evita re-litigar) |
| 5 | [`04_COMO_CONTINUAR.md`](./04_COMO_CONTINUAR.md) | Entorno, comandos, convenciones y “primer día” |
| 6 | [`05_MAPA_DEL_REPO.md`](./05_MAPA_DEL_REPO.md) | Dónde vive cada cosa (código, datos, índices, notebooks) |
| 7 | [`06_RAMAS_Y_ARTEFACTOS.md`](./06_RAMAS_Y_ARTEFACTOS.md) | Topología de ramas y en qué rama vive cada artefacto (M4, M6, M7) |
| — | [`EXECUTIVE_SUMMARY_EN.md`](./EXECUTIVE_SUMMARY_EN.md) | Resumen ejecutivo en inglés |

Si necesitás **detalle fino o el razonamiento original**, no leas las transcripciones enteras:
usá [`transcripciones/README.md`](./transcripciones/README.md) como índice, después el digest de la
sesión en [`digests/`](./digests/) y recién entonces grep sobre el `.md` de la sesión puntual.

## Regla de uso de las fuentes

```
docs/handoff/
├── 00..05 + README            <- narrativa curada (empezá acá)
├── digests/                   <- resumen por conversación, con temas y estado final
├── transcripciones/           <- 59 conversaciones completas (fuente primaria, ruidosa)
└── planes/                    <- snapshot de plans/ (planes M0–M9, repo git anidado)
```

1. **No ingerir `transcripciones/` en bloque** (≈2,6 MB de chat con ruido, notificaciones de
   terminal y reintentos). Es una fuente de consulta puntual, no de contexto inicial.
2. La verdad sobre resultados numéricos está en `ROADMAP.md`, `plans/MILESTONES.md` y los CSV/JSON
   de `evaluation_notebooks/raw_results/` — no en la transcripción, que puede tener borradores.
3. Donde la transcripción y el `ROADMAP.md` discrepen, gana el ROADMAP (fue actualizado después).

## Advertencias críticas (leer antes de tocar código)

1. **Rama actual sin upstream.** `feat/cost-optimization-benchmark` tiene 57 commits que **no
   existen en `origin`**. Si se pierde el disco, se pierde la etapa M4–M7. Primer paso: pushear.
2. **Hay cambios sin commitear que rompen seguridad**: `api/app.py` y `api/modules/security.py`
   tienen los rate limits y las cuotas **comentados a mano** (workaround de benchmark). No deben
   llegar a producción. Ver [hilos abiertos H-06](./03_HILOS_ABIERTOS.md).
3. **`plans/` es un repo git anidado e ignorado** por el repo principal (`.gitignore:44`). En un
   clone limpio no existe. Acá quedó el snapshot en [`planes/`](./planes/), pero su historial vive
   solo en tu disco.
4. **Secretos.** Los `.env` están fuera de git, pero aparecieron claves reales en los logs de chat
   (Groq, OpenRouter, `JWT_SECRET`, `APP_API_KEY`, host de MongoDB). Las transcripciones de este
   paquete están **redactadas**; aun así, rotá esas credenciales.
5. **La rama actual no tiene el blog de M4.** `semantic_search_optimization_{es,en}.md` vive solo en
   `feat/search-optimization`, 4 commits por delante. Mergear antes de migrar de harness
   ([H-11](./03_HILOS_ABIERTOS.md)).
6. **El estado tiene ~3 meses de antigüedad** (corte 2026-08-19). Precios de modelos, modelos
   disponibles y versiones de librerías pueden haber cambiado: reverificá antes de citar.

## Convenciones del proyecto que el próximo agente debe respetar

- **Blog primero**: cada etapa termina en una entrada en `documentation/markdowns/<n>_<tema>/`,
  en español y en inglés, con resultados verificados contra logs (no estimados).
- **Nada de números inventados**: el usuario exige que cada cifra del blog sea trazable a un CSV/JSON
  de `evaluation_notebooks/raw_results/` o a un log de la carpeta `logs/` de la entrada.
- **Tono narrativo**: serie de blog, no informe técnico. Se explicita el “por qué” y se admite lo
  que salió mal (el portfolio se vende como criterio, no como éxito).
- **Commits**: `tipo(scope): descripción` en inglés, un tema por commit, y el usuario commitea a mano
  en la mayoría de los casos (el agente propone el mensaje).
- **Idioma**: código y documentación técnica en inglés; conversación y borradores de blog en español.
