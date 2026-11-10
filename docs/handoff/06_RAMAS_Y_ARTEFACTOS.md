# 06 — Ramas y artefactos: dónde vive cada cosa

Análisis al 2026-11-09, con `git` (merge-bases y contención verificados, no inferidos).

---

## Topología real

```
main  33313d1 (2026-07-19, merge PR #44)
│
├── backup/real-corpus-migration-pre-fix        +340 commits  (2026-08-02)
│      Línea muerta: intento de M1/M2 antes del "fix" de namespace/metadata. No la usa nadie.
│
└── refactor/real-corpus-migration              +23          (2026-08-03)
       M1 corregido (ingesta + paradigma Q&A).
       │
       └── 2a195b4  "docs: correct M2 results with retrieval fixes"  (2026-08-03)
            │  Punto de bifurcación. A partir de acá las tres líneas se separan.
            │
            ├── feat/eval_pipeline              +44          (2026-08-17)
            │      M2/M3: entradas 0-2, juez Luna, sección de evaluador independiente.
            │      NO tiene M4 ni M6 ni M7.
            │
            └── 6492c97  (2026-08-05, fin del trabajo de M4 en código)
                 │
                 ├── feat/search-optimization   +58 (4 propias)   (2026-08-17)
                 │      **Único lugar donde existen las entradas M4 (ES+EN)** y los logs finales.
                 │      NO tiene M6 ni M7.
                 │
                 └── feat/cost-optimization-benchmark  +57 (3 propias)  (2026-08-05)
                      Herramientas del benchmark M6 (--generator-model, golden estratificado).
                      NO tiene el blog de M4.
                      │
                      └── feat/agentic-rag-implementation  +66 (9 propias)  (2026-08-16)
                           **Implementación completa del grafo M7** (5 nodos, prompts, fallback).
                           NO tiene el blog de M4 ni la evaluación del agente.
```

No es una pila perfecta: `feat/eval_pipeline` quedó **hermana** de la línea M4/M6/M7, y el blog de M4
se commiteó en `feat/search-optimization`, que tampoco contiene M6/M7. La “matrioshka” real es:

```
cost-optimization-benchmark ⊂ agentic-rag-implementation
```

y las dos piezas que faltan en esa pila son **el blog M4** (en `search-optimization`) y **los docs
M2/M3 de eval_pipeline**.

## Quién tiene cada artefacto

| Artefacto | main | refactor | eval_pipeline | search-opt | cost-opt | agentic (M7) | Working tree |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Entrada 0 (intro ES+EN) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| Entrada 1 (EDA ES+EN) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| Entrada 2 (post-migración ES+EN) | — | — | ✅ | ✅ | ✅ | ✅ | — |
| **Entrada 3 (M4 ES+EN)** | — | — | — | ✅ | — | — | — |
| **Entrada 4 (M6, ES)** | — | — | — | — | — | — | ✅ sin commitear |
| **Entrada 5 (M7, borrador ES)** | — | — | — | — | — | — | ✅ sin commitear |
| Código M4 (Atlas Search, voyage) | — | — | — | ✅ | ✅ | ✅ | + fixes |
| Herramientas M6 | — | — | — | — | ✅ | ✅ | — |
| **Código M7 (grafo)** | — | — | — | — | — | ✅ | — |
| `ROADMAP.md` | — | — | — | — | — | — | ✅ sin commitear |
| Logs M4 finales (`p0_luna`, `m2luna`, `p1_expanded`) | — | — | — | ✅ | — | — | parcial |
| Fix de seguridad (rate limits/cuotas) | correcto | correcto | correcto | correcto | correcto | correcto | ⚠️ roto |

## Qué está pusheado

| Rama | ¿En `origin`? | ¿Local = remoto? |
|---|---|---|
| `refactor/real-corpus-migration` | sí | sí |
| `feat/eval_pipeline` | sí | sí |
| `feat/search-optimization` | sí | sí |
| `feat/cost-optimization-benchmark` | **no** | — |
| `feat/agentic-rag-implementation` (M7) | **no** | — |
| `backup/real-corpus-migration-pre-fix` | **no** | — |

→ El código de **M6 y M7 existe solo en este disco**.

## Consolidación mínima recomendada

Objetivo: una sola rama con todo lo que se va a conservar.

```bash
git switch feat/agentic-rag-implementation        # ya contiene M6
git merge feat/search-optimization                 # trae blog M4 + logs finales (4 commits)
# opcional, para no perder los docs de M2/M3:
git merge feat/eval_pipeline                       # 44 commits; revisar conflictos en entrada 2
git push -u origin feat/agentic-rag-implementation
```

Después, commitear desde el working tree: entradas 4 y 5, `ROADMAP.md`, scripts, logs sueltos.
Antes de eso, **revertir el workaround de seguridad**.

Riesgo de conflicto: bajo en el merge de `search-optimization` (docs y logs nuevos; el único roce es
el chore de remoción de BM25), medio en el de `eval_pipeline` (dos versiones de la entrada 2 y
renombres de logs `m2_*`).

## Qué es descartable sin pérdida

| Elemento | Motivo |
|---|---|
| `backup/real-corpus-migration-pre-fix` | superada por `refactor/real-corpus-migration`; 340 commits de una línea que ya no se usa |
| `feat/rag-real-data-migration`, `feat/migration-to-real-dataset`, `feat/exploratory-data-analysis` | detrás de `main` por 320+ commits, ya mergeadas por PR |
| `feat/cost-optimization-benchmark` | su contenido ya está dentro de `feat/agentic-rag-implementation` |
| `feat/eval_pipeline` | su contenido está en la línea M7 salvo la sección del evaluador independiente; decidir si se mergea o se descarta |
| Stashes `2026-08-02` y `2026-08-17` (2) | trabajo de `feat/eval_pipeline`/`search-optimization` ya superado; revisar antes de dropear |
| ~25 branches de tareas viejas del curso | sin relación con la serie |

---

## Estado tras la consolidación (2026-11-09)

Línea de integración: **`feat/agentic-rag-implementation`**, pusheada a `origin`.

Qué se hizo:

1. Se revirtió el workaround de seguridad (`api/app.py`, `api/modules/security.py`) antes de commitear.
2. Se commitearon los entregables del working tree: entrada 4 (M6) con gráficos y logs, borrador de la
   entrada 5, `ROADMAP.md`, plan de migración, runners de evaluación, logs de ingesta y el paquete
   `docs/handoff/`.
3. `git merge feat/search-optimization` → entrada 3 (M4) y logs finales, sin conflictos.
4. La entrada 2 final (con la sección del juez independiente) se trajo **quirúrgicamente** desde
   `feat/eval_pipeline` (`git checkout feat/eval_pipeline -- documentation/markdowns/2_post_migration_eval`),
   en vez de mergear esa rama: su código es anterior a M4 y habría generado conflictos inútiles en
   `rag_unified_retriever.py` y `agent_app/`.
5. M6 quedó marcado como cerrado en `ROADMAP.md` y en `plans/MILESTONES.md`.

Estado de cada rama:

| Rama | Estado |
|---|---|
| `feat/agentic-rag-implementation` | **activa**, contiene M4 (código+blog), M6 y M7 |
| `feat/search-optimization` | mergeada; se conserva como referencia |
| `feat/eval_pipeline` | su documentación ya está en la línea activa; archivada |
| `feat/cost-optimization-benchmark` | contenida en la línea activa; archivada |
| `backup/real-corpus-migration-pre-fix` | archivada |
| `refactor/real-corpus-migration` | mergeada y pusheada; se conserva |

Archivo: se crearon tags anotados `archive/<rama>` para las ramas archivadas (no se borró ninguna).
Los tres stashes se conservan; el `stash@{0}` era equivalente al workaround ya revertido.

## Próximo paso

**M7 se termina** (decisión 2026-11-09): correr la evaluación E2E, escribir los resultados en la
entrada 5 y traducirla. Protocolo en `plans/M7_Agent/02_Agent_Evaluation.md`.
