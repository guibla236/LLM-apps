# D5 — Ventana de contexto del agente (`82a938d8`)

- **Fecha**: 2026-03-01
- **Turnos**: 6
- **Transcripción**: [`../transcripciones/82a938d8-2e15-49e7-9d04-9f4202486364.md`](../transcripciones/82a938d8-2e15-49e7-9d04-9f4202486364.md)

---

## Qué se buscaba

El `agent_app` ya era un RAG agéntico en LangGraph, pero sin manejo de ventana de contexto.
El usuario pide un plan que detecte cuándo el historial es demasiado largo y lo resuma, sin romper el
checkpointer de MongoDB.

## Qué se resolvió

- Estrategia de **resumen incremental** del historial, con el resumen persistido como parte del turno
  en el checkpointer (no recalculado en cada interacción).
- Pregunta clave del usuario: “si la conversación sigue, ¿no tendríamos que generar el resumen en cada
  interacción?” → se aclara qué se guarda y cuándo.
- Riesgo identificado: en un turno agéntico el agente puede hacer **varias** consultas al RAG y
  colapsar la ventana en un único turno → el límite debe contar también los resultados acumulados,
  no solo los mensajes.
- Al final el usuario pide ver los cambios **sin aplicarlos** (los aplicó él).

## Por qué importa para el handoff

Es la base conceptual del estado `accumulated_context` del M7 y de la restricción de
`max_iterations`. Si se rediseña el agente, esta decisión (resumen en el checkpointer + límite por
turno, no por mensaje) debe respetarse.
