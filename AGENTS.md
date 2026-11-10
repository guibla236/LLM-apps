# AGENTS.md

Entry point for any AI agent (any harness) working on this repository.

## Read this first

`docs/handoff/` contains a complete handoff package written for exactly this purpose:

1. [`docs/handoff/00_ESTADO_ACTUAL.md`](docs/handoff/00_ESTADO_ACTUAL.md) — factual state, risks
2. [`docs/handoff/01_HISTORIA_POR_ETAPA.md`](docs/handoff/01_HISTORIA_POR_ETAPA.md) — what each stage was
   meant to achieve and what it produced
3. [`docs/handoff/03_HILOS_ABIERTOS.md`](docs/handoff/03_HILOS_ABIERTOS.md) — open threads and next actions
4. [`docs/handoff/02_DECISIONES.md`](docs/handoff/02_DECISIONES.md) — decisions already made (do not re-litigate)
5. [`docs/handoff/04_COMO_CONTINUAR.md`](docs/handoff/04_COMO_CONTINUAR.md) — environment and commands

Environments are recreated with `./scripts/bootstrap_envs.sh` (see `--help`). Do not `pip install`
ad hoc: `api/requirements.txt` is runtime only, `requirements.eval.txt` is for the eval/ingestion
scripts and `requirements.dev.txt` for notebooks and tooling.

Before running any evaluation, read [`docs/handoff/08_NOTAS_ULTIMA_SESION.md`](docs/handoff/08_NOTAS_ULTIMA_SESION.md):
it records a fixed contract bug, an unresolved sufficiency-judge behaviour and an operational trap
(daily quota makes search return empty results instead of an error).

Do **not** ingest `docs/handoff/transcripciones/` wholesale (~2,6 MB of raw chat with terminal noise).
Use the index there, then the digest in `docs/handoff/digests/`, then targeted `grep`.

## Non-negotiable rules

- Every number that goes into a blog entry must be traceable to a CSV/JSON/log in
  `evaluation_notebooks/raw_results/` or in that entry's `logs/` folder. Never estimate.
- The blog series is bilingual (Spanish + English) and narrative, not a technical report. Negative
  results are part of the value.
- Commits: one topic each, `type(scope): description` in English. The owner usually commits manually;
  propose the message instead of committing.
- Do not commit anything that disables auth, rate limits or quotas (`api/app.py`,
  `api/modules/security.py` currently contain a benchmark workaround — see H-04).
- Secrets live in `.env` files and are never committed.

## State snapshot

Last documented state: **2026-08-19**. Branch `feat/cost-optimization-benchmark`, no upstream,
57 commits ahead of `main`. The M4 blog entry lives only on `feat/search-optimization`.
Milestones M0–M4 and M6 are closed; M7 is implemented but not evaluated; M5/M8/M9 are deferred.
