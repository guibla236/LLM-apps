# ¿Datos sintéticos o reales? Qué cambió (y qué no) al migrar un RAG de un corpus sintético a uno real

En las dos entradas anteriores se planteó que el RAG poseía métricas modestas porque fue construido sobre datos sintéticos. A partir de eso, se realizó un análisis de un corpus real de aproximadamente 60.000 pares de preguntas y respuestas de Stack Exchange como posible solución. En esta tercera entrada se cierra la trilogía de migración ejecutándose la misma y evaluándose el sistema en su configuración definitiva con el corpus generado por personas reales.

En la primera entrada de este diario de migración se planteó como hipótesis que el problema del RAG no estaba en la arquitectura, sino en la materia prima. Los datos sintéticos generados por LLMs pueden sufrir de una perfección que el mundo real no contiene y esa perfección artificial transforma métricas simples en quimeras imposibles. El análisis exploratorio de la segunda entrada validó la viabilidad del corpus real. Esta entrada cierra el círculo: la hipótesis se confirmó y lo hizo con resultados contundentes.

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

La estratificación garantiza que todas las áreas temáticas relevantes estén representadas, sin que las comunidades grandes (superuser, askubuntu) dominen completamente la muestra. Se construyó un _golden dataset_ de **200 pares** con esta estratificación y, de él, se tomaron **50 pares** para las evaluaciones de esta entrada mediante un sub-muestreo que preserva las mismas proporciones por comunidad. Luego, se evaluaron dos escenarios: búsqueda puramente vectorial y búsqueda híbrida (Semántica + BM25). En el primer escenario deberíamos ver cuán buena es la búsqueda semántica, mientras que en el segundo deberíamos observar si la búsqueda tradicional por palabras clave suma valor al sistema.

Todos los golden pairs están excluidos del índice vectorial y del índice BM25. Esto garantiza que el sistema nunca pueda recuperar el documento exacto de la pregunta evaluada. Así, las métricas de retrieval miden la capacidad de encontrar el documento más relevante por similitud, no de obtener una coincidencia literal. Es una forma acotada de generalización que, si bien el LLM generador (entrenado en datos públicos) podría reconocer problemas conocidos de StackExchange, el retrieval no puede apoyarse en la coincidencia exacta.

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

> **Una nota al margen sobre el camino.** La primera pasada de esta evaluación arrojó un 0.00% de ContextualPrecision en el escenario de búsqueda puramente vectorial. Un cero absoluto sobre 50 preguntas no es algo que un sistema de mala calidad produzca, sino una gran advertencia de que hay algo roto. Sabiendo esto, procedí a auditar la cadena de retrieval para luego confirmar que la búsqueda semántica no se estaba ejecutando contra el corpus real: estaba consultando un _namespace_ de Pinecone vacío. Se corrigieron los bugs de conexión y la evaluación se repitió. Los números de esta entrada son los de esa corrida corregida y los ceros de las métricaas quedaron como un nuevo recordatorio de que, en estadística, las métricas demasiado exactas indican problemas técnicos en vez de resultados propiamente dichos.

## Resultados

El diseño de esta comparación es deliberadamente conservador: entre el baseline sintético de abril y esta corrida, el único cambio fue el corpus. Mismo pipeline, mismo retriever, misma metodología de evaluación, mismo juez (DeepSeek V4 Flash, el generador de la época). Estando todo lo demás constante, las cinco métricas subieron. Eso es lo que hace que la migración sea concluyente: la materia prima no era la mejor. Estos resultados son el registro de esa lectura. 

De todas formas, si bien se intentó tener comparabilidad con la evaluación previa, la utilización del mismo modelo para generar y evaluar el sistema resulta un problema metodológico. La sección "Baseline de referencia con juez independiente" mide nuevamente el mismo sistema con otro juez y muestra que la conclusión de la migración no depende del evaluador.

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

1. **El juez y el generador son el mismo modelo** (`deepseek/deepseek-v4-flash`). Esto introduce un sesgo de autoevaluación: un modelo tiende a ser indulgente con las respuestas de su propia familia. Por eso, más abajo, esta misma entrada valida la lectura con un juez independiente: GPT 5.6 Luna.

2. **La definición de Faithfulness mide generación pero sujeta a que el pipeline RAG esté funcionando como tal**: que el LLM use la evidencia recuperada en lugar de responder de memoria o inventar también es capturado por esta métrica. Si el modelo ignoró el contexto y dio una respuesta halucinada, Faithfulness daría un valor bajo incluso siendo un modelo potente. Por esto, el valor alto indica que el flujo *recuperar y generar sobre lo recuperado* se respeta, algo central para un RAG.

**AnswerRelevancy 94.76%**: casi 19 de cada 20 respuestas son pertinentes a la pregunta del usuario. Mejora sustancial respecto al baseline sintético (56.31%) y confirma que la generación está alineada con el formato Q&A.

**ContextualPrecision 31.88% y ContextualRecall 17.15%**: frente al baseline sintético de abril (11.19% y 11.67%), la precisión contextual casi se triplica y el recall crece algo más de cinco puntos. La búsqueda semántica funciona por sí sola (el vector-only alcanza 29.37% de precisión contextual) y el BM25 aporta un complemento l éxico adicional de aproximadamente 2.5 puntos porcentuales.

Conviene explicitar el techo de diseño de estas métricas antes de juzgarlas: todos los _golden pairs_ fueron excluidos deliberadamente del índice vectorial y del léxico. La consecuencia es que el retriever nunca puede recuperar el documento exacto de la pregunta evaluada dado que el mismo no se encuentra indexado. Por esto, solo puede encontrar documentos *similares* al documento faltante, razón por la que una precisión perfecta es inalcanzable: el "documento correcto" no existe dentro del índice. Esa es la forma acotada de generalización que se diseñó y cualquier lectura de las métricas de retrieval de esta serie debe tener ese límite superior en mente.

Con la recuperación ya operativa, el siguiente paso lógico es empujar estas métricas hacia arriba. `all-minilm:22m` y su dimensionalidad de 384 valores fue una elección pragmática para el prototipo sintético pero la capacidad semántica para distinguir matices en un corpus técnico se espera que sea mayor con modelos más avanzados y _embeddings_ de mayor dimensión. En el futuro se evaluarán modelos modernos como `voyage-4-lite` (1024 dimensiones) junto con distintas estrategias de chunking, que van desde eliminar el chunking por completo hasta probar ventanas más amplias. El objetivo será encontrar la combinación que maximice la precisión del recuperador sin tocar el resto del pipeline.

### El índice BM25 no cabe en producción

La migración trajo consigo un problema inesperado: **el índice BM25 dejó de ser viable para la versión desplegada** dada la infraestructura con la que se venía trabajando (Vercel gratuito). Con el corpus sintético (750 documentos) el índice pesaba unos cientos de kilobytes, mientras que ahora con los 60.000 pares reales, el archivo índice para hacer la búsqueda léxica con BM25 creció a **125 MB**.

El resultado es que **la búsqueda híbrida (BM25 + Vector) solo funciona en el entorno local de desarrollo**. Con el juez de la época, el retrieval semántico mostraba 29.37% de Contextual Precision y el híbrido agregaba un complemento léxico de 2.5 puntos (31.88%) que se perdería en producción. Ante esta situación, surge una posibilidad: **Mover la búsqueda léxica a MongoDB Atlas** dado que ya tenemos los datos allí y esa plataforma también utiliza BM25 para dicha búsqueda, por lo que habilitar la búsqueda híbrida en producción implica algunos pocos cambios de código que se llevarán adelante en la siguiente etapa.

Eventualmente, MongoDB Atlas también podría encargarse de la búsqueda semántica, pero eso se evaluará una vez que la búsqueda semántica esté optimizada y no dependa de BM25 para cumplir con los requerimientos de recuperación.

### Baseline de referencia con juez independiente

La comparación de esta entrada usó el mismo juez que el generador (DeepSeek V4 Flash) por coherencia metodológica con la evaluación de abril, un diseño válido para aislar la variable corpus usado pero que arrastra el sesgo de autoevaluación señalado antes. 

Para que las mejoras que siguen en la serie partan de valores sin ese sesgo, se establece aquí un _baseline_ de referencia evaluado con un juez independiente: GPT 5.6 Luna, de la familia OpenAI, distinto al generador. Se utilizó para evaluar el sistema sobre las mismas 50 consultas golden y la misma configuración del sistema. Resulta interesante ver las diferencias con el juez original.

<center>

| Métrica | Vector Only | Hybrid (BM25 + Vector) |
|---------|:-----------:|:----------------------:|
| Correctness | **50.40%** | 46.80% |
| Faithfulness | **98.91%** | 98.78% |
| AnswerRelevancy | 96.14% | **96.77%** |
| ContextualPrecision | 60.33% | **64.54%** |
| ContextualRecall | **23.66%** | 22.20% |

</center>

La comparación entre jueces sobre el mismo sistema dimensiona el efecto del juez en los valores absolutos. Antes de interpretarla, una advertencia metodológica: no hay una verdad de referencia contra la cual medir a los jueces, así que no podemos afirmar si DeepSeek subestima o Luna sobreestima. Lo que sí es verificable:

- **La brecha se concentra en las métricas de retrieval.** Contextual Precision difiere en 32 puntos porcentuales (31.88% -> 64.54% en el híbrido) y Contextual Recall en aproximadamente 5, mientras que las métricas de generación pura difieren poco (AnswerRelevancy +2, Correctness +11 en hybrid, Faithfulness +0.3). El efecto del juez no se distribuye parejo sino que impacta donde el juez debe razonar sobre rankings de documentos.
- **La dirección de la brecha es la opuesta a la esperada.** El sesgo de autoevaluación documentado suele ser indulgencia con la propia familia. Acá DeepSeek puntúa *más bajo* que un juez independiente. Ambos comportamientos son compatibles con los datos: DeepSeek puede ser severo con su propio output, o Luna puede ser más permisivo en general. No lo sabemos.
- **Lo que importa para esta serie no es el absoluto, sino la consistencia.** No se precisa saber cuál juez se acerca más a una "verdad" que desconocemos mientras utilizamos la ténica _LLM as a judge_: necesitamos que todas las comparaciones de aquí en adelante usen el mismo juez, para que las diferencias que medimos sean atribuibles al sistema y no al evaluador. De la misma forma, evaluar la respuesta con el mismo que esta se genera es algo no aceptable por la cuestión de los sesgos.

<center>

| Métrica | Juez deepseek (corrida de esta entrada) | Juez gpt-5.6-luna (baseline de referencia) |
|---------|:---:|:---:|
| Correctness (Hybrid) | 36.00% | **46.80%** |
| Faithfulness (Hybrid) | 98.47% | **98.78%** |
| AnswerRelevancy (Hybrid) | 94.76% | **96.77%** |
| ContextualPrecision (Hybrid) | 31.88% | **64.54%** |
| ContextualRecall (Hybrid) | 17.15% | **22.20%** |

</center>

Estos valores quedan definidos como el **baseline de referencia oficial** del proyecto hasta ahora: a partir de aquí, toda medición de las mejoras siguientes se comparará contra esta columna con juez constante. La columna histórica de la migración (DeepSeek) se conserva como referencia de continuidad con la evaluación de abril pero ya no es la base de comparación.

#### El juez no solo cambia los absolutos: puede invertir un veredicto comparativo

La tabla de esta sección permite un ejercicio adicional: comparar la dirección del efecto del hybrid bajo cada juez. Con el juez anterior, el híbrido parecía aportar en todas las métricas; con el juez de referencia, el panorama es distinto:

<center>

| Métrica | ¿Hybrid aporta? Juez DeepSeek | ¿Hybrid aporta? Juez luna |
|---------|:---:|:---:|
| Correctness | Sí (+12.0) | **No** (−3.6) |
| Faithfulness | Sí (+8.4) | No (−0.1) |
| AnswerRelevancy | Sí (+0.2) | Sí (+0.6) |
| ContextualPrecision | Sí (+2.5) | Sí (+4.2) |
| ContextualRecall | Sí (+3.3) | **No** (−1.5) |

</center>

En las métricas de generación, la elección del juez no cambia el veredicto. Pero en **Correctness y Contextual Recall**, el hybrid parece aportar con DeepSeek y deja de aportar (o resta levemente, dentro de la varianza de los resultados) con Luna. El reencuadre es entonces doble:
- La migración sigue siendo exitosa dado que con cualquier juez, el corpus real supera al sintético en todas las métricas. 
- Sin embargo, en el *retrieval*, que en la lectura de DeepSeek parecía el punto débil del sistema con 29.37% de Contextual Precision y una Contextual Recall bastante pobre, Luna presenta métricas más altas: 60.33% de Contextual Precision en vector-only y 23.66% de Contextual Recall (ambos vector-only pero lo mismo ocurre con hybrid). Si de aquí en más vamos a utilizar ese juez por las razones ya citadas, la mejora del retrieval deja de ser un problema urgente por resolver y pasa a ser un área con margen de mejora.

### Conclusiones

**1. La hipótesis de la migración se confirmó: la materia prima era el problema.** El sistema completo, con corpus real y en su configuración actual, supera al sistema sintético en Correctness (36.00% vs 19.33%) y lo mejora drásticamente en Faithfulness (98.47% vs 84.24%) y Answer Relevancy (94.76% vs 56.31%). Con 80 veces más documentos y preguntas reales escritas por humanos, el sistema responde mejor. Tal como se pensó desde un principio, los datos sintéticos eran un problema.

**2. El sistema genera respuestas casi sin alucinaciones.** Faithfulness 98.47% en el escenario híbrido, 90.10% incluso en Vector Only (con el mismo juez que se usó en el sistema original; con el juez de referencia, 98.78% y 98.91% respectivamente) por lo que estas métricas confirman que el flujo de recuperación y generación sobre lo recuperado se respeta sin alucinaciones notorias.


**3. El retrieval es el nuevo punto fuerte del pipeline.** Con el juez anterior (el mismo usado para la generación de la respuesta), la recuperación había mostrado el menor avance frente al baseline sintético (ContextualPrecision 31.88% vs 11.19%, casi el triple) y quedó como sospechosa de las limitaciones del sistema. Con el juez nuevo, ese mismo sistema mide **60.33% de ContextualPrecision en vector-only y 64.54% en hybrid**, un nivel sólido para un embedding local de 384 dimensiones. De todas formas, no podemos afirmar cuál de los dos jueces tiene mayor razón, solo preferiremos GPT 5.6 Luna de aquí en más para evaluar el sistema con una familia distinta a la del generador. Por esta decisión de diseño, el retrieval deja de ser el punto débil urgente y pasa a ser un área con margen de mejora.

### Referencias

- [Artículo 1: Introducción a la migración de datos](../0_dataset_migration_intro/dataset_migration_intro_es.md)
- [Artículo 2: EDA del corpus de Stack Exchange](../1_dataset_migration_EDA/dataset_migration_EDA_es.md)
- [Resultados completos en CSV](logs/comparison_20260803_definitive.csv)
