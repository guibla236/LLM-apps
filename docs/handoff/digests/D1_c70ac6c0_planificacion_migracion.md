# D1 — Planificación de la migración (`c70ac6c0`)

- **Fechas**: 2026-07-11 → 2026-08-04
- **Turnos**: 113
- **Transcripción**: [`../transcripciones/c70ac6c0-9cb3-44d7-b4e4-2136d92b764b.md`](../transcripciones/c70ac6c0-9cb3-44d7-b4e4-2136d92b764b.md)
- **Rol**: la conversación donde se **decide** la migración y se escribe el backlog. No ejecuta casi nada.

---

## Punto de partida

El usuario sospecha que el RAG no es malo: es el dataset. Corpus sintético, en español, con Golden
Answers generadas por el mismo LLM. Quiere un corpus real que “matchee el problema” y que construir
el sistema sea **una prueba de cómo hace un RAG por sí mismo**.

## Qué se resolvió

1. **Elección del corpus**: Stack Exchange Q&A (12 comunidades IT, ~60K pares, EN). Se descartó
   ChromaDB local (el deploy es volátil) y se mantuvo Pinecone.
2. **Volumen**: la cuenta gratuita de Pinecone no alcanzaba para todo → se evalúa muestrear; finalmente
   se ingiere todo porque el corpus final entra en el plan pago.
3. **EDA como primer paso obligatorio** (M0) y como **entrada de blog**, no como reporte interno.
4. **Backlog estilo GitHub Issues**: se migran conceptos de Azure DevOps/Jira → labels, milestones e
   issues, con una carpeta `plans/` como “product backlog” versionado aparte.
5. **Congelar el trabajo en curso** (stash + branch de backup) para tener baseline limpio antes de
   migrar, y crear un milestone futuro para retomarlo.
6. **Milestones M0–M9** definidos, con un M6 (costos) y M7 (agente) que después se reordenaron.
7. **Decisión editorial**: no decir en los issues que es “para un portfolio”; sí en los blogs.
8. **Filtrado**: discusión larga sobre el mecanismo de selección de pares (gap de votos) que termina
   en el criterio único de 50 caracteres.

## Estado final

El plan quedó completo y ejecutado hasta M7. Este hilo también define las **restricciones de
narrativa**: el blog debe explicar el *por qué* de cada decisión, y el EDA debe ser legible para
alguien que no leyó nada antes.

## Citas que fijan restricciones

- “Me gustaría que la construcción del sistema sea una prueba de cuán bien puedo hacer un RAG por mí mismo.”
- “Hagamos algo: te pongo en modo planificación y armamos el plan de sustitución del conjunto de datos.”
- “Considero que estaría bueno darle más contexto respecto al pasado del proyecto… de dónde venimos y hacia dónde vamos.”
- “Quiero que transformes este issue en algo ligeramente distinto: una orden de escribir documentación en formato markdown para presentar en un blog.”
- “Esto que estamos planificando hacer, ¿no lo ha hecho cuánta gente ya? ¿No será muy trillado?” → de esa duda salen la comparación académica y el benchmark de retrievers.
