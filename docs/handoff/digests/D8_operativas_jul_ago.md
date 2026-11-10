# D8 — Operativas de julio/agosto

Dos sesiones cortas, sin contenido de diseño, pero que explican incidentes del período.

---

## `66ab5367` — Puertos ocupados (2026-07-29, 2 turnos)
[transcripción](../transcripciones/66ab5367-e094-4372-b337-545ab5ea0a32.md)

- Necesitaba liberar procesos en 8000/8001/8002 (API + agente + frontend) antes de relanzar la ingesta.
- No aporta decisiones; sirve como señal de que el entorno local se satura con los tres servicios y
  los venv del proyecto.

## `e69f84fa` — Recuperar branch tras force-push (2026-08-02, 2 turnos)
[transcripción](../transcripciones/e69f84fa-b1c5-4ffb-ae14-e56e057f00cd.md)

- Tras un `push --force`, GitHub mostraba la branch desactualizada.
- Contexto: venía de **recuperar el workspace después de un crash** (ver también `bbba0afa`).
- Confirma el patrón de riesgo del repo: ramas locales sin upstream + force-push + repo `plans/`
  anidado = pérdida de trabajo fácil. Es el antecedente directo de [H-05](../03_HILOS_ABIERTOS.md)
  y [H-06](../03_HILOS_ABIERTOS.md).
