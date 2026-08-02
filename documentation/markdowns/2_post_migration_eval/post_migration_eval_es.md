# ¿Datos sintéticos o reales? Qué cambió (y qué no) al migrar un RAG de un corpus sintético a uno real

En las dos entradas anteriores se planteó el problema: un RAG con métricas modestas construido sobre datos sintéticos. A partir de eso, se realizó un análisis de un corpus real de aproximadamente 60.000 pares de preguntas y respuestas de Stack Exchange como posible solución. En esta tercera entrada se cierra la trilogía: se ejecuta la migración y se evalúa el sistema en su configuración definitiva con el corpus generado por personas reales.

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

La estratificación garantiza que todas las áreas temáticas del soporte estén representadas, sin que las comunidades masivas (superuser, askubuntu) dominen completamente la muestra. Primero se obtuvieron solo 50 pares del _golden dataset_ barajados de forma tal que fueran representativos de las 9 comunidades. Luego, se evaluaron dos escenarios: búsqueda puramente vectorial y búsqueda híbrida (Semántica + BM25). En el primer escenario deberíamos ver cuán buena es la búsqueda semántica, mientras que en la segunda deberíamos observar si la búsqueda tradicional por palabras clave suma valor al sistema.

Todos los _golden pairs_ están excluidos del índice vectorial y del índice BM25, razón por la que el sistema mide generalización, no capacidad de memorizar.

## Métricas de evaluación

Para evaluar el RAG se utilizó la librería [DeepEval](https://github.com/hwchase17/deepeval), con cinco métricas que diagnostican etapas diferentes del pipeline:

<center>

| Métrica | Qué mide | Etapa que diagnostica |
|---------|----------|----------------------|
| **ContextualPrecision** | ¿El contexto recuperado es relevante para la pregunta? | Retrieval |
| **ContextualRecall** | ¿El contexto recuperado cubre la información que la respuesta esperada menciona? | Retrieval |
| **Faithfulness** | ¿La respuesta generada se basa en el contexto recuperado o alucina? | Generation |
| **AnswerRelevancy** | ¿La respuesta generada es pertinente a la pregunta? | Generation |
| **Correctness** | ¿La respuesta generada es factualmente correcta según la respuesta esperada? | End-to-end |

</center>

Una distinción importante: las dos primeras métricas evalúan al _retriever_ (qué tan bien encuentra documentos), mientras que las dos siguientes evalúan al generador (qué tan bien usa ese contexto) y la última evalúa el sistema completo.

## Resultados

<center>

| Métrica | Vector Only | Hybrid (BM25 + Vector) |
|---------|:-----------:|:----------------------:|
| Correctness | 25.20% | **25.80%** |
| Faithfulness | **97.30%** | 97.03% |
| AnswerRelevancy | **88.32%** | 85.52% |
| ContextualPrecision | 0.00% | **7.99%** |
| ContextualRecall | 0.00% | **5.71%** |

</center>

<div align="center">

![Comparación de métricas: Vector Only vs Hybrid](images/metrics_vector_vs_hybrid.png)

</div>

### Comparación con el baseline sintético

<center>

| Especificación | Sintético (abril) | Real (julio) |
|:---------------|:---:|:---:|
| Documentos en el índice | 807 | **60.161** |
| _Golden pairs_ excluidos | ✅ Sí | ✅ Sí |
| Modelo generador | Llama 3.1 8B | DeepSeek V4 Flash |
| | | |
| ContextualPrecision (Hybrid) | 11.19% | 7.99% |
| ContextualRecall (Hybrid) | 11.67% | 5.71% |
| Faithfulness (Hybrid) | 84.24% | **97.03%** |
| AnswerRelevancy (Hybrid) | 56.31% | **85.52%** |
| Correctness (Hybrid) | 19.33% | **25.80%** |

</center>

<div align="center">

![Comparación de métricas: corpus sintético vs real](images/metrics_synthetic_vs_real.png)

</div>

### Lo que estas métricas significan

**Correctness 25.80%**: supera el baseline sintético (19.33%) y lo hace en condiciones más exigentes, dado que ahora estamos midiendo generalización sobre respuestas reales de StackExchange escritas por humanos. Una de cada cuatro respuestas generadas es considerada factualmente correcta por el juez. Si bien resulta mejorable, es un buen síntoma que el cambio de materia prima haya mejorado el desempeño.

**Faithfulness 97.03%**: en los 50 casos evaluados, la respuesta generada se basó en el contexto recuperado. Esta métrica merece dos matices:

1. **El juez y el generador son el mismo modelo** (`deepseek/deepseek-v4-flash`). Esto introduce un sesgo de autoevaluación: un modelo tiende a ser indulgente con las respuestas de su propia familia. El número real de Faithfulness podría ser algo menor con un juez independiente. Tener un juez distinto al generador es una limitación metodológica a corregir en una próxima iteración, dado que la actual se pretendía como una primera medición de los cambios y se buscó que fuera eficiente en costos.

2. **La definición de Faithfulness mide generación pero sujeta a que el pipeline RAG esté funcionando como tal**: que el LLM use la evidencia recuperada en lugar de responder de memoria o inventar también es capturado por esta métrica. Si el modelo ignoró el contexto y dio una respuesta halucinada, Faithfulness daría un valor bajo incluso siendo un modelo potente. Por esto, el valor alto indica que el flujo *recuperar y generar sobre lo recuperado* se respeta, algo central para un RAG.

**AnswerRelevancy 85.52%**: más de cuatro de cada cinco respuestas son pertinentes a la pregunta del usuario. Mejora sustancial respecto al baseline sintético (56.31%) y es la métrica de generación más alta del sistema junto a Faithfulness.

**ContextualPrecision 7.99% y ContextualRecall 5.71%**: las métricas de _retrieval_ siguen siendo las más bajas del sistema. BM25 aporta recuperación por palabras clave que el _embedding_ semántico por sí solo no logra (Vector Only da 0% en ambas). La precisión contextual es baja porque el sistema recupera documentos *similares* a la pregunta pero nunca el documento exacto (esto ocurre porque los _golden pairs_ están excluidos del índice).

El siguiente paso lógico es atacar la causa raíz del problema: la calidad del modelo de embeddings. `all-minilm:22m` (384 dimensiones) fue necesario para un prototipo con datos sintéticos, pero no tiene la capacidad semántica para distinguir matices y aún menos para hacerlo en un corpus técnico de 60.000 documentos reales. La siguiente fase evaluará modelos modernos como `voyage-4-lite` (1024 dimensiones) junto con distintas estrategias de chunking — desde eliminar el chunking por completo hasta probar ventanas más amplias — para encontrar la combinación que maximice la precisión del recuperador sin tocar el resto del pipeline.

### Un hallazgo de infraestructura: el índice BM25 no cabe en producción

La migración trajo consigo un problema inesperado: **el índice BM25 dejó de ser viable para la versión desplegada** dada la infraestructura con la que se venía trabajando. Con el corpus sintético (807 documentos) el índice pesaba unos cientos de kilobytes, mientras que ahora, con los 60.000 pares reales, el archivo índice para hacer la búsqueda léxica con BM25 creció a **125 MB**. Esa magnitud choca con el despliegue por dos razones: la carga del índice demoraría más tiempo que el permitido por Vercel para un *cold start* y además ocurre que el servidor debe cargar el JSON completo como un diccionario para construir el retriever BM25 y al hacerlo, excede la RAM disponible en el plan que brinda la plataforma.

El resultado práctico es que **la búsqueda híbrida (BM25 + Vector), la única que aportó valor en la etapa de retrieval, solo funciona en el entorno local de desarrollo**. Esto no bloquea el experimento: la evaluación corre en local y los resultados de esta entrada se obtuvieron con la configuración completa. En estas circunstancias, se opta por retrasar la liberación de la nueva versión del producto que hace uso del nuevo conjunto de datos hasta que se posea un *retrieval* semántico que las métricas validen como funcional. Esto implica priorizar la mejora de la búsqueda semántica antes que destinar esfuerzo a un problema de infraestructura que no resulta central para el experimento.

El plan a futuro pasa por dos caminos:
1. **Mejorar la búsqueda semántica**: Implementar modelos de embeddings más avanzados y estrategias de chunking para mejorar la precisión del recuperador semántico.
2. **Mover la búsqueda tradicional a MongoDB Atlas**: Utilizar la plataforma de MongoDB para gestionar la búsqueda léxica, lo que habilitará la búsqueda híbrida en producción.

Eventualmente, MongoDB Atlas también podría encargarse de la búsqueda semántica, pero eso se evaluará una vez que la búsqueda semántica esté optimizada y no dependa de BM25 para cumplir con los requerimientos de recuperación.

### Conclusiones

**1. La migración de datos se realizó correctamente.** El sistema completo, con corpus real y en su configuración actual, supera al sistema sintético en Correctness (25.80% vs 19.33%) y lo mejora drásticamente en Faithfulness (97.03% vs 84.24%) y AnswerRelevancy (85.52% vs 56.31%). Con 75 veces más documentos y preguntas reales, el sistema responde mejor, no peor.

**2. El sistema genera respuestas casi sin alucinaciones.** Faithfulness 97.03% en el escenario híbrido, 97.30% incluso en Vector Only. El pipeline *recuperar y generar sobre lo recuperado* se respeta. El matiz: el juez y el generador son el mismo modelo, lo que puede inflar levemente el número — validar con un juez independiente es una tarea pendiente.

**3. El retrieval sigue siendo el cuello de botella.** Las métricas de recuperación (ContextualPrecision 7.99%, ContextualRecall 5.71%) son las más bajas del sistema. BM25 es indispensable para que el recuperador tenga capacidad de búsqueda efectiva (Vector Only sin BM25 da 0% en ambas). La causa raíz es el modelo de embeddings — `all-minilm:22m` (384 dimensiones) no captura la semántica de un dominio técnico con 60.000 documentos. La siguiente fase (Search Optimization) evaluará modelos modernos como `voyage-4-lite` (1024 dimensiones) y estrategias de chunking para corregir esto.

### Referencias

- [Artículo 1: Introducción a la migración de datos](../0_dataset_migration_intro/dataset_migration_intro_es.md)
- [Artículo 2: EDA del corpus de Stack Exchange](../1_dataset_migration_EDA/dataset_migration_EDA_es.md)
- [Resultados completos en CSV](logs/comparison_20260731_definitive.csv)
