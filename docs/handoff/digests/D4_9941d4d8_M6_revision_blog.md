# D4 — Revisión externa del blog M6 (`9941d4d8`)

- **Fecha**: 2026-08-08
- **Turnos**: 1 (una sola instrucción larga, sin respuesta completa)
- **Transcripción**: [`../transcripciones/9941d4d8-a8fe-41b2-aa1e-88b61c2d86d0.md`](../transcripciones/9941d4d8-a8fe-41b2-aa1e-88b61c2d86d0.md)

---

## Qué pasó

El usuario había puesto a **otro agente** (con capacidad de ver imágenes) a auditar el blog de costos
y sus seis gráficos. Pegó el veredicto completo en esta sesión y pidió:

1. Mejorar la entrada de blog incorporando esas observaciones.
2. Incorporar el argumento de que **Gemini tiene un valor real por latencia** (el usuario siente que
   se lo estaba descartando injustamente).
3. “Trata de no olvidarte de nada.”

## Contenido del veredicto (lo que importa)

El auditor concluyó que **las conclusiones principales eran verosímiles y estaban bien respaldadas**,
con matices:

- Los gráficos de correctness por bucket sostienen la ventaja de DeepSeek, pero la diferencia con
  Ling está en el orden del ruido del juez → no sobreafirmar.
- Latencia: Gemini es un caso de uso legítimo cuando el SLA manda, aunque pierda en calidad.
- Varias afirmaciones necesitaban explicitar la métrica de costo (tokens medidos vs estimados).

## Por qué está en el paquete

Este hilo **no se ejecutó** (quedó como instrucción). Explica el origen de parte de los FIXMEs del
blog M6 y, sobre todo, deja escrito el criterio editorial: el blog debe defender a Gemini en latencia
sin cambiar la recomendación de DeepSeek como generador.

Ver [H-02](../03_HILOS_ABIERTOS.md) para el estado de esos cambios.
