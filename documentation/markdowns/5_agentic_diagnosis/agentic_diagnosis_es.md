# Del RAG al agente: cuándo la búsqueda híbrida tiene sentido, y por qué eso justifica un agente

*Draft — secciones de motivación completas. Implementación y resultados pendientes de ejecución (M7).*

---

La entrada anterior cerró con un hallazgo que contradecía la sabiduría convencional del RAG: **la búsqueda híbrida (semántica + léxica) ya no aportaba — incluso restaba un poco** frente a la búsqueda semántica sola. Esta entrada explica por qué ese resultado, lejos de ser un problema, es la motivación más sólida para el siguiente paso de la serie: un **agente de diagnóstico multi-paso** que decide autónomamente cómo buscar y cuándo dejar de buscar.

## El hallazgo inesperado: el híbrido dejó de servir

Con la búsqueda semántica optimizada (`voyage-4-lite`, 1024 dimensiones) y la búsqueda léxica migrada a MongoDB Atlas Search, se ejecutó la corrida final comparando el ganador de M4 en modo `vector_only` contra el modo `hybrid` (semántica + léxica fusionadas). El resultado fue revelador:

| Métrica | P1 vector_only | P1 hybrid | Δ |
|---|---:|---:|---:|
| Correctness | **51.00%** | 49.80% | −1.20 |
| Faithfulness | **98.38%** | 98.05% | −0.33 |
| AnswerRelevancy | 95.86% | **95.94%** | +0.08 |
| ContextualPrecision | 69.40% | **69.65%** | +0.25 |
| ContextualRecall | **25.91%** | 23.19% | **−2.72** |

La lectura es clara: **el componente léxico se solapa con el denso**. Con `all-minilm:22m` (la era M2), el híbrido era esencial — el vector-only daba 0% y el BM25 agregaba ~2.5 puntos. Con `voyage-4-lite`, la búsqueda semántica es tan buena que añadir resultados léxicos desplaza contexto relevante del vector en lugar de complementarlo.

## ¿Por qué pasa esto? La literatura ya lo anticipaba

El análisis de funciones de fusión en recuperación híbrida de Bruch, Gai & Ingber (2023) demuestra que **la fusión híbrida es sensible a cómo se combinan los puntajes**: la combinación convexa supera al Reciprocal Rank Fusion (RRF) en dominios generales, pero **requiere calibrar un parámetro de peso para el dominio objetivo** — no existe un "50/50 mágico". Nuestro merge asignaba peso fijo al léxico (score 0.8 vs 0.75 del vector) sin calibración alguna. Weaviate usa `alpha=0.75` (75% vector) como default precisamente porque en la práctica el componente semántico suele merecer más peso.

Para un corpus homogéneo como Stack Exchange — preguntas técnicas con respuestas técnicas, en el mismo dominio — la búsqueda densa ya cubre lo que la léxica aportaría. **El híbrido no está mal implementado: está mal aplicado de forma indiscriminada.**

## La idea clave: la búsqueda léxica no está muerta, está condicionada

La conclusión práctica de M4 fue: `vector_only` es la configuración óptima como *default*. Pero hay un subconjunto de consultas donde el léxico sí debería aportar: **consultas con carga léxica pesada** — códigos de error (`0x800705b4`), nombres de comandos (`netsh wlan show networks`), IDs, versiones de software. En esas, la coincidencia exacta de tokens es información que la semántica diluye.

El problema es que no se puede saber de antemano, con una regla estática, cuándo activar la búsqueda léxica. Un sistema que siempre la usa pierde recall (como muestra la tabla). Un sistema que nunca la usa falla en consultas con códigos de error. **La decisión de *cuándo* usar qué estrategia es, por naturaleza, una decisión condicional.**

## De la decisión condicional al agente

Esa decisión condicional es exactamente lo que distingue a un agente de un pipeline fijo:

```
Consulta: "error 0x800705b4 en Windows Update"
  → El agente detecta un código de error → decide activar búsqueda léxica
  → Recupera contexto específico del código → evalúa si alcanza → responde

Consulta: "cómo configuro el firewall para permitir SSH"
  → El agente clasifica la consulta como general → usa solo búsqueda semántica
  → Recupera contexto relevante → evalúa si alcanza → responde
```

El agente no solo decide entre estrategias de búsqueda: también **itera**. Si el contexto recuperado es insuficiente, reformula la consulta con más especificidad y vuelve a buscar — acumulando contexto hasta tener evidencia suficiente para responder, con un máximo de 3 iteraciones para garantizar latencia acotada.

## Por qué esto cierra la serie

La serie ha seguido una progresión deliberada: datos (M0-M3) → búsqueda (M4) → costo (M6) → razonamiento (M7). El agente es el paso lógico porque las decisiones que en M4 se tomaron manualmente (elegir `vector_only` como default, documentar que el léxico solo ayuda en ciertos casos) ahora se vuelven **decisiones en tiempo de ejecución** que el sistema toma por sí solo, informadas por los mismos datos que motivaron el milestone anterior.

<!-- ============================================================
     IMPLEMENTACIÓN — PENDIENTE DE EJECUCIÓN (M7)
     Completar tras implementar el grafo:
     1. Arquitectura LangGraph: 5 nodos (analyze → search → evaluate → refine → generate)
     2. Estado acumulado con deduplicación por ticketId
     3. Límite de 3 iteraciones
     4. Cómo el agente decide entre vector_only y lexical por consulta
     5. Compatibilidad: API RAG sin cambios, frontend Streamlit sin cambios
     ============================================================ -->

<!-- ============================================================
     RESULTADOS — PENDIENTE DE EJECUCIÓN (M7)
     Completar tras la evaluación:
     1. Tabla comparativa: M4 (RAG directo) vs M7 (agente) sobre 50 golden pairs
     2. Métricas: Correctness, Faithfulness, AnswerRelevancy + iteraciones promedio, latencia
     3. Análisis: ¿qué tipos de consulta se benefician del multi-paso?
     4. ¿El enrutamiento léxico/semántico del agente mejora la baseline vector-only?
     5. Reflexión: ¿cuándo el agente falla? (límite de iteraciones, consultas sin contexto)
     ============================================================ -->

## Referencias

- **Bruch, S., Gai, S., & Ingber, A. (2023).** *An Analysis of Fusion Functions for Hybrid Retrieval.* ACM TOIS / arXiv:2210.11934.
- [Artículo 4: Optimización de la búsqueda semántica](../3_semantic_retrieval_improvements/semantic_search_optimization_es.md) — donde nace el hallazgo del híbrido.

---

*Esta entrada es parte de la serie de documentación del proyecto. Las métricas provienen de las evaluaciones ejecutadas con DeepEval sobre 50 pares golden estratificados, con exclusión de los pares del índice (midiendo generalización).*
