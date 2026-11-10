# Conversación `3bed607c-b78b-4ebd-a3cf-a18d3ec5741c`

- Inicio: 2026-02-28 00:21
- Fin: 2026-02-28 00:23
- Turnos: 3

---

## [1] Usuario — 2026-02-28 00:21

Con qué comando podría saber cuál es la branch principal de un repositorio, independientemente de cuál sea el repositorio o la branch donde me encuentre actualmente

### Copilot

El comando más directo (sin importar en qué branch local estés) es:

git remote show origin | sed -n '/HEAD branch/s/.*: //p'

Te devuelve main, master, etc. (la branch por defecto del remoto origin).

Si quieres que funcione incluso cuando el remoto principal no se llame origin:

git remote show "$(git remote | head -n1)" | sed -n '/HEAD branch/s/.*: //p'

Tip: si no devuelve nada, primero actualiza referencias remotas con git fetch --all --prune.

---

## [2] Usuario — 2026-02-28 00:21

inténtalo con el repositorio actual

## [3] Usuario — 2026-02-28 00:23

No, solo dime un comando lo suficientemente robusto como para funcionar con cualquier repositorio en cualquier situación. No confiemos en información local

### Copilot

`r=$(git remote | head -n1); git ls-remote --symref "$r" HEAD | sed -n 's#^ref: refs/heads/\([^[:space:]]*\)[[:space:]]\+HEAD$#\1#p'`

Ese comando consulta directamente el remoto (no `origin/HEAD` local) y devuelve la branch por defecto real (`main`, `master`, etc.).

---
