# ¿Datos sintéticos o reales? Qué cambió (y qué no) al migrar un RAG de un corpus sintético a uno real

En las dos entradas anteriores se planteó el problema: un RAG con métricas modestas construido sobre datos sintéticos. A partir de eso, se realizó un análisis de un corpus real de aproximadamente 60.000 pares de preguntas y respuestas de Stack Exchange como posible solución. En esta tercera entrada se cierra la trilogía: se ejecuta la migración y se evalúa el sistema en su configuración definitiva con el corpus generado por personas reales.

En la primera entrada de esta trilogía planteé como hipótesis que el problema del RAG no estaba en la arquitectura, sino en la materia prima. Los datos sintéticos generados por LLMs pueden sufrir de una perfección que el mundo real no contiene y esa perfección artificial transforma métricas simples en quimeras imposibles. El análisis exploratorio de la segunda entrada validó la viabilidad del corpus real. Esta entrada cierra el círculo: la hipótesis se confirmó, y con números contundentes.

### Construcción del _golden dataset_

Para evaluar el sistema se construyó un _golden dataset_ de 200 pares pregunta-respuesta muestreados aleatoriamente del corpus real, con `seed=42` para garantizar reproducibilidad. El muestreo fue **estratificado por comunidad**, con cuotas proporcionales a una noción de relevancia de cada comunidad para soporte IT de nivel 1 que además evite la subrrepresentación de comunidades pequeñas como el caso de `devops` que discutimos durante el EDA. La estratificación se muestra en la siguiente tabla:

<div align="center">

| Comunidad | Pares | Categoría | Porcentaje |
|-----------|------:|-----------|-----------|
| superuser | 50 | Hardware / Office | 25% |
| askubuntu | 50 | OS / General | 25% |
| apple | 25 | MDM / Mobility | 12.5% |
| android | 25 | MDM / Mobility | 12.5% |
| serverfault | 15 | DevOps / Infra | 7.5% |
| dba | 10 | Data & SQL | 5% |
| networkengineering | 10 | Networking | 5% |
| security | 10 | Cybersecurity | 5% |
| devops | 5 | DevOps | 2.5% |



![Composición por comunidad de los 50 pares evaluados](images/sample_community_composition.png)

</div>

La estratificación garantiza que todas las áreas temáticas del soporte estén representadas, sin que las comunidades grandes (superuser, askubuntu) dominen completamente la muestra. Primero se obtuvieron solo 50 pares del _golden dataset_ barajados de forma tal que fueran representativos de las 9 comunidades. Luego, se evaluaron dos escenarios: búsqueda puramente vectorial y búsqueda híbrida (Semántica + BM25). En el primer escenario deberíamos ver cuán buena es la búsqueda semántica, mientras que en la segunda deberíamos observar si la búsqueda tradicional por palabras clave suma valor al sistema.

Todos los golden pairs están excluidos del índice vectorial y del índice BM25. Esto garantiza que el sistema nunca pueda recuperar el documento exacto de la pregunta evaluada: las métricas de retrieval miden la capacidad de encontrar el documento más relevante por similitud, no de obtener una coincidencia literal. Es una forma acotada de generalización que, si bien el LLM generador, entrenado en datos públicos, podría reconocer problemas conocidos de StackExchange, el retrieval no puede apoyarse en la coincidencia exacta.

## Métricas de evaluación

Para evaluar el RAG se utilizó la librería [DeepEval](https://github.com/hwchase17/deepeval), con cinco métricas que diagnostican etapas diferentes del pipeline:

<center>

| Métrica | Qué mide | Etapa que diagnostica |
|---------|----------|----------------------|
| **Correctness** | ¿La respuesta generada es factualmente correcta según la respuesta esperada? | End-to-end |
| **Faithfulness** | ¿La respuesta generada se basa en el contexto recuperado o alucina? | Generation |
| **AnswerRelevancy** | ¿La respuesta generada es pertinente a la pregunta? | Generation |
| **ContextualPrecision** | ¿El contexto recuperado es relevante para la pregunta? | Retrieval |
| **ContextualRecall** | ¿El contexto recuperado cubre la información que la respuesta esperada menciona? | Retrieval |

</center>

Una distinción importante: las dos últimas métricas evalúan al _retriever_ (qué tan bien encuentra documentos), mientras que Faithfulness y AnswerRelevancy evalúan al generador (qué tan bien usa ese contexto) y Correctness evalúa el sistema completo.

> **Una nota al margen sobre el camino.** La primera pasada de esta evaluación arrojó un 0.00% de ContextualPrecision en el escenario de búsqueda puramente vectorial. Un cero absoluto sobre 50 preguntas no es algo que un sistema de mala calidad produzca, sino una gran advertencia de que hay algo roto. Sabiendo esto, procedí a auditar la cadena de retrieval para luego confirmar que la búsqueda semántica no se estaba ejecutando contra el corpus real: estaba consultando un _namespace_ de Pinecone vacío. Se corrigieron los bugs de conexión y la evaluación se repitió. Los números de esta entrada son los de esa corrida corregida y los ceros de las métricaas quedaron como un nuevo recordatorio de que, en estadística, las métricas demasiado exactas indican problemas profundos en vez de resultados reales.

## Resultados

El diseño de esta comparación es deliberadamente conservador: entre el baseline sintético de abril y esta corrida, el único cambio fue el corpus. Mismo pipeline, mismo retriever, misma metodología de evaluación, mismo juez. Todo lo demás constante, las cinco métricas subieron. Eso es lo que hace que la migración sea concluyente: la materia prima era el problema.

<center>

| Métrica | Vector Only | Hybrid (BM25 + Vector) |
|---------|:-----------:|:----------------------:|
| Correctness | 24.00% | **36.00%** |
| Faithfulness | 90.10% | **98.47%** |
| AnswerRelevancy | 94.57% | **94.76%** |
| ContextualPrecision | 29.37% | **31.88%** |
| ContextualRecall | 13.86% | **17.15%** |

</center>

<div align="center">

![Comparación de métricas: Vector Only vs Hybrid](images/metrics_vector_vs_hybrid.png)

</div>

### Comparación con el baseline sintético

<center>

| Especificación | Sintético (abril) | Real (corregido) |
|:---------------|:---:|:---:|
| Documentos en el índice | 750 | **60.161** |
| _Golden pairs_ excluidos | ✅ Sí | ✅ Sí |
| Modelo generador | Llama 3.1 8B | DeepSeek V4 Flash |
| | | |
| Correctness (Hybrid) | 19.33% | **36.00%** |
| Faithfulness (Hybrid) | 84.24% | **98.47%** |
| AnswerRelevancy (Hybrid) | 56.31% | **94.76%** |
| ContextualPrecision (Hybrid) | 11.19% | **31.88%** |
| ContextualRecall (Hybrid) | 11.67% | **17.15%** |

</center>

<div align="center">

![Comparación de métricas: corpus sintético vs real](images/metrics_synthetic_vs_real.png)

</div>

### Lo que estas métricas significan

**Correctness 36.00%**: supera el baseline sintético (19.33%) y lo hace en condiciones más exigentes, dado que ahora estamos midiendo generalización sobre respuestas reales de StackExchange escritas por humanos. Más de una de cada tres respuestas generadas es considerada factualmente correcta por el juez.

**Faithfulness 98.47%**: en los 50 casos evaluados, la respuesta generada se basó en el contexto recuperado. Esta métrica merece dos matices:

1. **El juez y el generador son el mismo modelo** (`deepseek/deepseek-v4-flash`). Esto introduce un sesgo de autoevaluación: un modelo tiende a ser indulgente con las respuestas de su propia familia. El número real de Faithfulness podría ser algo menor con un juez independiente. Tener un juez distinto al generador es una limitación metodológica a corregir en una próxima iteración, dado que la actual se pretendía como una primera medición de los cambios y se buscó que fuera eficiente en costos.

2. **La definición de Faithfulness mide generación pero sujeta a que el pipeline RAG esté funcionando como tal**: que el LLM use la evidencia recuperada en lugar de responder de memoria o inventar también es capturado por esta métrica. Si el modelo ignoró el contexto y dio una respuesta halucinada, Faithfulness daría un valor bajo incluso siendo un modelo potente. Por esto, el valor alto indica que el flujo *recuperar y generar sobre lo recuperado* se respeta, algo central para un RAG.

**AnswerRelevancy 94.76%**: casi 19 de cada 20 respuestas son pertinentes a la pregunta del usuario. Mejora sustancial respecto al baseline sintético (56.31%) y confirma que la generación está alineada con el formato Q&A.

**ContextualPrecision 31.88% y ContextualRecall 17.15%**: frente al baseline sintético de abril (11.19% y 11.67%), la precisión contextual casi se triplica y el recall crece más de cinco puntos. La búsqueda semántica funciona por sí sola (el vector-only alcanza 29.37% de precisión contextual) y el BM25 aporta un complemento léxico adicional de casi 2.5 puntos. La precisión no es perfecta porque el sistema recupera documentos *similares* a la pregunta pero nunca el documento exacto (esto ocurre porque los _golden pairs_ están excluidos del índice).

Con la recuperación ya operativa, el siguiente paso lógico es empujar estas métricas hacia arriba. `all-minilm:22m` (384 dimensiones) fue una elección pragmática para el prototipo sintético, pero la capacidad semántica para distinguir matices en un corpus técnico se espera que sea mayor con modelos más avanzados y _embeddings_ de mayor dimensión. La siguiente fase evaluará modelos modernos como `voyage-4-lite` (1024 dimensiones) junto con distintas estrategias de chunking, que van desde eliminar el chunking por completo hasta probar ventanas más amplias. Encontrar la combinación que maximice la precisión del recuperador sin tocar el resto del pipeline será el objetivo.

### Un hallazgo de infraestructura: el índice BM25 no cabe en producción

La migración trajo consigo un problema inesperado: **el índice BM25 dejó de ser viable para la versión desplegada** dada la infraestructura con la que se venía trabajando. Con el corpus sintético (750 documentos) el índice pesaba unos cientos de kilobytes, mientras que ahora, con los 60.000 pares reales, el archivo índice para hacer la búsqueda léxica con BM25 creció a **125 MB**.

El resultado práctico es que **la búsqueda híbrida (BM25 + Vector) solo funciona en el entorno local de desarrollo**. Si bien el retrieval funciona relativamente bien con la búsqueda semántica (29.37% de ContextualPrecision), el híbrido agrega un complemento léxico valioso (31.88%) que se perdería en producción. Ante esta situación, surge una posibilidad: **Mover la búsqueda léxica a MongoDB Atlas** dado que ya tenemos los datos allí y también se utiliza BM25 para dicha búsqueda, por lo que habilitar la búsqueda híbrida en producción implica algunos pocos cambios de código.

Eventualmente, MongoDB Atlas también podría encargarse de la búsqueda semántica, pero eso se evaluará una vez que la búsqueda semántica esté optimizada y no dependa de BM25 para cumplir con los requerimientos de recuperación.

### Conclusiones

**1. La hipótesis de la trilogía se confirmó: la materia prima era el problema.** El sistema completo, con corpus real y en su configuración actual, supera al sistema sintético en Correctness (36.00% vs 19.33%) y lo mejora drásticamente en Faithfulness (98.47% vs 84.24%) y AnswerRelevancy (94.76% vs 56.31%). Con 80 veces más documentos y preguntas reales escritas por humanos, el sistema responde mejor, no peor. Tal como se pensó desde un principio, los datos sintéticos eran un problema y los datos reales la solución.

**2. El sistema genera respuestas casi sin alucinaciones.** Faithfulness 98.47% en el escenario híbrido, 90.10% incluso en Vector Only. El pipeline *recuperar y generar sobre lo recuperado* se respeta. El matiz: el juez y el generador son el mismo modelo, lo que puede inflar levemente el número — validar con un juez independiente es una tarea pendiente.

**3. El retrieval es el nuevo punto fuerte del pipeline.** La recuperación del corpus real casi triplica la del baseline sintético (ContextualPrecision 31.88% vs 11.19%) y la búsqueda semántica funciona por sí sola (29.37% en vector-only). La siguiente fase (Search Optimization) evaluará si modelos modernos como `voyage-4-lite` (1024 dimensiones) y estrategias de chunking pueden empujar estas métricas aún más.

### Referencias

- [Artículo 1: Introducción a la migración de datos](../0_dataset_migration_intro/dataset_migration_intro_es.md)
- [Artículo 2: EDA del corpus de Stack Exchange](../1_dataset_migration_EDA/dataset_migration_EDA_es.md)
- [Resultados completos en CSV](logs/comparison_20260803_definitive.csv)
