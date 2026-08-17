# Del diagnóstico a la optimización: cómo mejorar la búsqueda semántica de un RAG sin tocar la arquitectura

En la entrada anterior de esta serie se completó la migración de datos y se obtuvo las métricas que resultaban de la evaluación del nuevo sistema que fueron sustancialmente mejores que aquellas obtenidas para el mismo objetivo pero usando datos sintéticos. Una vez que ya teníamos el nuevo conjunto de datos funcionando y validado, el siguiente paso era mejorar la calidad de la búsqueda semántica.

En esta entrada se documentan las distintas partes de dicho proceso de mejora: los experimentos, las decisiones de costo y el resultado final que define la nueva configuración de búsqueda del sistema.

## El punto de partida

Una vez integrados los nuevos datos con el sistema anterior y adaptado todo lo necesario, la búsqueda semántica con el modelo de embeddings `all-minilm:22m`, sus 384 dimensiones alcanzaba y un chunking como el establecido para los tickets y Knowledge Bases, obtenía las siguientes métricas de recuperación usando GPT-5 Luna como juez:

<center>

| Métrica | Vector Only | Hybrid (léxico + vector) |
|---|---:|---:|
| ContextualPrecision | 60.33% | 64.54% |
| ContextualRecall | 23.66% | 22.20% |

</center>

El modelo de embeddings se seleccionó por ser lo suficientemente pequeño como para permitir la creación local de embeddings usando Ollama, algo suficiente para la cantidad de tickets y Knowledge Bases con las que se contaba. Al cambiar a un corpus real de 60.000 pares técnicos de preguntas y respuestas (consultas), no solo que la generación de los mismos implicaba un tiempo de proceso mucho mayor, sino que su capacidad semántica era la sospechosa principal para las limitaciones en las métricas de recuperación.

Además de las cuestiones relativas al modelo, la búsqueda semántica no había sido optimizada para el corpus, desconociéndose si las estrategias de _chunking_ de dividir los tickets de a 200 caracteres y dejar 20 de solapamiento o 1000/100 para los KBs eran las más adecuadas para el mismo.

## El diseño experimental

El análisis exploratorio dejó dos hallazgos relevantes para esta etapa: el 75% de las preguntas cabe en un único _chunk_ de 1000 caracteres y la máxima cantidad que puede tener una consulta es de 4.171. Teniendo en cuenta esto y garantizado el acceso a modelos mucho más nuevos para crear embeddings (como Voyage 4 de principios de 2026), se diseñaron una serie de experimentos con un solo modelo nuevo y dos estrategias de chunking:

<center>

| Experimento | Embedding | Chunking |
|---|---|---|
| **P0** | voyage-4-lite (1024d) | Sin chunking (documento completo) |
| **P1** | voyage-4-lite (1024d) | Chunking sugerido por el EDA (1000/100) |

</center>

`voyage-4-lite` se eligió por su mejor relación calidad-precio ($0.02/M tokens, 1024 dimensiones, MTEB de 65 puntos contra 56 del modelo anterior). Nótese también que el modelo produce vectores de 1024 dimensiones, lo que implica casi tres veces más información semántica que puede almacenarse por documento, algo que se espera que también potencie los resultados.

Una precisión metodológica ha de hacerse: en este cambio que estamos haciendo se mueven varias piezas al mismo tiempo. Asignar las mejoras que podrán observarse a un cambio específico (modelo, dimensionalidad, chunking) resulta imposible.
**Decisiones metodológicas importantes**:

1. **Solo `vector_only` por variante**: el híbrido confunde el efecto del embedding con el causado por BM25 y duplica el costo de evaluación sin aportar valor adicional al análisis del _retrieval_. El _hybrid_ se reserva para el final, con el ganador de la búsqueda semántica.
2. **Solo métricas de retrieval (ContextualPrecision/Recall) en las variantes**: son las que responden si mejoró la búsqueda. Las preguntas de generación dependen del LLM, no del embedding. De todas formas, con la idea de saber las métricas finales del sistema, el ganador se re-evaluará con las 5 métricas.

## Resultados esperados

Se espera que la implementación del nuevo modelo de embeddings, la dimensionalidad mayor de estos y la estrategia de _chunking_ de menor fragmentación mejore ambas métricas de _retrieval_. Entre las dos estrategias de chunking propuestas, se plantean dos escenarios verosímiles:

1. Que se manifieste un trade-off entre precisión y recall causado por la fragmentación excesiva, beneficiando a P0 en precision y a P1 en recall (y viceversa).
    - Esto es algo que puede observarse en el _survey_ de RAG de Gao et al. (2023), el cual documenta que el _chunk size_ genera un trade-off precisión/recall: chunks más chicos mejoran el _matching_ pero generan pérdidas de contexto.
2. Que ambas métricas mejoren simultáneamente en el experimento con _chunking_ 1000/100, lo que indicaría que el _chunking_ logró capturar la mayor cantidad de información relevante, lo que sería verosímil si se considera que el chunking sugerido por el EDA había sugerido esta estrategia. 
    - Esta excepción al trade-off clásico encuentra respaldo en la literatura: Chen et al. (2023) demuestran que cuando la unidad de indexación (el _chunk_ elegido) se alinea con la unidad semántica del contenido (que es lo que buscamos que el _chunk_ capture), la recuperación mejora sin sacrificar precisión, dado que no fragmenta la semántica disponible.

De todas formas, es necesario hacer una precisión sobre el segundo punto: por razones de costo y de tiempo, no se evaluará la variante de _chunking_ 2000/200 o 500/50, por lo que no se podrá determinar si el _chunking_ sugerido por el EDA es el óptimo o si un _chunking_ más grande podría mejorar aún más las métricas. Esto será trabajo futuro pero al menos si sucede se podrá rechazar la hipótesis de que no hacer chunking es la mejor alternativa.

## Resultados de los experimentos iniciales

Para la evaluación, al igual que se hizo en el [artículo anterior](../2_post_migration_eval/post_migration_eval_es.md), se utilizó el juez de referencia `gpt-5.6-luna` para todas las comparaciones. Los resultados obtenidos fueron los siguientes:

<center>

| Variante | ContextualPrecision | ContextualRecall |
|---|---:|---:|
| Baseline previo (all-minilm) | 60.33% | 23.66% |
| **P0** (voyage-4-lite, no-chunk) | 64.01% | 23.92% |
| **P1** (voyage-4-lite, chunk 1000/100) | **69.40%** | **25.91%** |

</center>

Lo primero que salta a la vista de utilizar un modelo más moderno es que el impacto es positivo: **la precisión contextual subió 4 puntos con el documento sin _chunking_ (P0) y 9 puntos con el chunking sugerido por el EDA (P1)**, todo esto respecto al _baseline_ con los datos nuevos, usando ambos exactamente el mismo sistema pero diferenciándose en la estrategia de chunking usada. Esto significa que los cambios realizados sobre la búsqueda semántica incrementaron la calidad de los resultados aumentando la cantidad de documentos relevantes recuperados respecto del total de recuperación.

Cuando pasamos a la evaluación del _contextual recall_ vemos que el cambio de modelo, de la estrategia de chunking y de la dimensionalidad de los embeddings también provocó un salto en la métrica. La comparación entre las dos estrategias de _chunking_, sin embargo, no muestra el trade-off clásico que la literatura y la lógica anticipaban:

- **Chunking 1000/100 (P1)**: mejor precisión (69.40%) y mejor _recall_ (25.91%), implicando esto que el _chunk_ captura mejor la semántica de la consulta concreta, lo que le permite al retriever no solo obtener resultados más relevantes sino también rankearlos mejor, lo que a su vez acerca al top las afirmaciones que el sistema necesita.
- **Sin chunking (P0)**: precisión menor (64.01%) y recall menor (23.92%), indicando esto que el embedding del documento completo diluye la semántica específica y los documentos que llegan al top no son necesariamente los que contienen las afirmaciones de la respuesta esperada.

De esta forma validamos que impactó más el segundo punto de los resultados esperados que el primero, desapareciendo el trade-off tradicional entre las dos alternativas de chunking. Esto se puede atribuir a haber seguido la sugerencia del EDA, dado que el 75% de las preguntas del corpus cabe en un único chunk de 1000 caracteres y eso nos posibilita que el chunking 1000/100 **no fragmente** el contexto. 

De todas formas, esta conclusión es débil por la precisión metodológica que se hizo en la sección anterior: no se evaluó un _chunking_ más grande (2000/200) o más chico (500/50), por lo que no se puede determinar si el _chunking_ sugerido por el EDA es el óptimo o si un _chunking_ distinto podría mejorar aún más las métricas. 

## El chunking ganador

A pesar que es indiscutible la mejora con el modelo de embeddings nuevo, lo que sí queda pendiente discutir es el método de _chunking_. **El ganador es P1: voyage-4-lite con chunking 1000/100**, la variante que mejoró ambas métricas de retrieval frente al baseline y a P0, con el juez de referencia (GPT-5.6-luna).

Para el cierre se ejecutaron las **5 métricas del ganador con un juez independiente** (`openai/gpt-5.6-luna` de la familia OpenAI, distinta al generador que pertenece a la familia de modelos DeepSeek). Los resultados finales en `vector_only`:

<center>

| Métrica | Baseline (all-minilm) | **P1 final (voyage-4-lite)** |
|---|---:|---:|
| Correctness | 50.40% | **51.00%** |
| Faithfulness | **98.91%** | 98.38% |
| AnswerRelevancy | 96.14% | **95.86%** |
| ContextualPrecision | 60.33% | **69.40%** |
| ContextualRecall | 23.66% | **25.91%** |

</center>

La comparación con juez constante entre ambas columnas permite dimensionar la mejora real del cambio de embeddings: ContextualPrecision sube 9 puntos (60.33% → 69.40%) y ContextualRecall sube unos 2.25 (23.66% → 25.91%), mientras que Correctness apenas cambia (+0.6 pts, algo que puede encontrarse dentro del ruido del juez).


## Incorporando la búsqueda sintáctica y la validez del sistema híbrido

Para poner en contexto este resultado conviene recordar de dónde venimos. Sobre el baseline anterior (all-minilm), el hybrid **sí aportaba** respecto del vector-only, medido con el mismo juez de referencia:

<center>

| Métrica | Baseline vector_only (luna) | Baseline hybrid (luna) | Δ |
|---|---:|---:|---:|
| Correctness | **50.40%** | 46.80% | −3.60 |
| Faithfulness | **98.91%** | 98.78% | −0.13 |
| AnswerRelevancy | 96.14% | **96.77%** | +0.63 |
| ContextualPrecision | 60.33% | **64.54%** | +4.21 |
| ContextualRecall | **23.66%** | 22.20% | −1.46 |

</center>

Con la migración de la búsqueda léxica a **MongoDB Atlas Search** (reemplazando el índice BM25 local de 125 MB, imposible de desplegar en Vercel), se ejecutó la corrida final del `hybrid` del ganador con el mismo juez independiente. La tabla anterior con las nuevas condiciones arrojó los siguientes resultados:

<center>

| Métrica | P1 vector_only (luna) | P1 hybrid (luna) | Δ |
|---|---:|---:|---:|
| Correctness | **51.00%** | 49.80% | −1.20 |
| Faithfulness | **98.38%** | 98.05% | −0.33 |
| AnswerRelevancy | 95.86% | **95.94%** | +0.08 |
| ContextualPrecision | 69.40% | **69.65%** | +0.25 |
| ContextualRecall | **25.91%** | 23.19% | **−2.72** |

</center>

**El hybrid ya no aporta.** En la era del modelo, _chunking_ y dimensionalidad anteriores (all-minilm), el hybrid daba un aporte de **4.21 puntos de CP** (60.33% → 64.54%) a costa de −1.46 de CR, como muestra la tabla anterior, indicando que el componente léxico complementaba a la búsqueda semántica. Con `voyage-4-lite`, la búsqueda semántica es tan buena que el componente léxico **se solapa** con el denso: suma +0.25 de CP pero pierde −2.72 de CR (los resultados léxicos desplazan contexto relevante del vector).

**¿Qué puede estar pasando?** El comportamiento observado podría estar asociado a lo que encuentran Bruch, Gai & Ingber (2023) en *An Analysis of Fusion Functions for Hybrid Retrieval*: estos autores demuestran que la fusión híbrida de resultados (semánticos y léxicos) **no tiene una receta única**. Así, la forma de combinar el _score_ semántico y el _score_ léxico para un mismo documento que fue encontrado en los dos métodos de búsqueda, afecta el resultado de la fusión. Además, afirman que el parámetro que logra extraer lo mejor de ambos componentes **debe calibrarse para cada dominio**, lo que nos dice que no existe un valor mágico para el ponderador. 

La unión de resultados que se implementó aquí no calibraba ese equilibrio: asignaba scores fijos (0.75 al vector, 0.8 al léxico) y daba prioridad de orden a los resultados vectoriales, sin ajustar esa relación al corpus. La consecuencia es que cuando el componente semántico es fuerte (como sucede en los experimentos con P1 donde se cubren bien las consultas), ese desbalance a favor del léxico desplaza contexto relevante del vector, lo que podría estar detrás de la caída de 2.72 puntos porcentuales de CR en las pruebas.

**La conclusión práctica**: para el corpus Stack Exchange con voyage-4-lite, `vector_only` es la configuración óptima como default. El hybrid o directamente la búsqueda léxica quedan disponibles para consultas con carga léxica pesada (códigos de error, nombres de comando, IDs), donde la búsqueda exacta sí se espera que aporte. La decisión de cuándo usarlo es un candidato natural para el **enrutamiento dinámico** que el agente de diagnóstico multi-paso implementará, algo que será materia de una mejora futura.

# Síntesis

Con esta entrada queda definida la configuración de búsqueda del sistema, resultado de las decisiones evaluadas con los experimentos realizados aquí:

<center>

| Componente | Configuración final |
|---|---|
| **Modelo de embeddings** | `voyage-4-lite` (1024 dimensiones) — reemplaza a `all-minilm:22m` (384d) |
| **Chunking** | 1000/100 (sugerido por el EDA: el 75% de las preguntas cabe en un único chunk) |
| **Búsqueda semántica** | Vectorial sobre el índice `tickets-m4-exp-b` (namespace `kb-se-all`) |
| **Búsqueda léxica** | MongoDB Atlas Search (reemplaza al BM25 local de 125 MB, imposible de desplegar en producción) |
| **Modo por defecto** | `vector_only` — el hybrid ya no aporta con el embedding nuevo (se solapa con el denso) |
| **Juez de evaluación** | `gpt-5.6-luna` (independiente del generador, juez de referencia de la serie) |

</center>

Las métricas finales del sistema en su configuración definitiva (`vector_only`, juez GPT-5.6 Luna):

<center>

| Métrica | Resultado final |
|---|---:|
| Correctness | **51.00%** |
| Faithfulness | **98.38%** |
| AnswerRelevancy | **95.86%** |
| ContextualPrecision | **69.40%** |
| ContextualRecall | **25.91%** |

</center>

El sistema queda, entonces, con una búsqueda semántica optimizada que mejora la precisión contextual en ~9 puntos sobre el baseline con juez constante (60.33% → 69.40%), un chunking alineado con la distribución del corpus (que evita el trade-off precisión/recall al no fragmentar el documento típico).

## Lo que sigue

Con la búsqueda semántica optimizada y la léxica migrada a MongoDB Atlas Search (lo que permite que funcione en producción sin el archivo local), la etapa de mejora de la búsqueda se considera cerrada, más allá de que podría profundizarse con la investigación de más alternativas que validen o maticen las decisiones de arquitectura tomadas aquí. 

Luego de esto evaluaremos si, como también sugiere el EDA, podemos implementar modelos más pequeños y baratos para consultas más simples a partir de saber la longitud de las respuestas. 

Una vez tengamos resultados de esa investigación, procederemos con una mejora: hacer el RAG algo agéntico a partir de un **agente de diagnóstico multi-paso**, que, — motivado por el hallazgo del hybrid, podría enrutar mejor entre búsqueda semántica y léxica las consultas e iterar hasta tener contexto suficiente.

## Precisiones que podrían motivar futuros análisis

Esta entrada deja definida una configuración de búsqueda sólida y respaldada por datos, pero también varias preguntas abiertas que valdría la pena explorar para afinar o confirmar las decisiones tomadas:

**1. Aislar el efecto de la dimensionalidad del embedding.** El cambio de all-minilm (384 dimensiones) a voyage-4-lite (1024) movió a la vez el modelo y su dimensionalidad, y las mejoras observadas no pueden atribuirse a una sola de esas piezas. Aislar la dimensionalidad no es directo: `all-minilm` no admite 1024 dimensiones (su arquitectura la fija en 384) ni voyage se puede reducir fácilmente a 384 (al menos que se implemente alguna técnica de reducción de dimensionalidad). Podría también probarse con Voyage 4 las distintas dimensionalidades que brinda para saber cuál es la ideal.

**2. Mapear el chunking alrededor del punto óptimo.** La conclusión de que 1000/100 es el punto donde el chunk no fragmenta al documento típico se apoyó en comparar solo dos estrategias (sin chunking vs 1000/100). Quedaron sin explorar el chunking más grande (2000/200) y uno más chico (500/50), además de un punto intermedio (1500/150). Probarlos permitiría ver si 1000/100 es un máximo local o si el dial se puede girar aún más en cualquiera de los dos sentidos, y validaría con más evidencia la hipótesis del EDA de que el tamaño del chunk debe alinearse con la distribución de longitudes del corpus.

**3. Calibrar la fusión híbrida en lugar de descartarla.** El veredicto de que el hybrid "ya no aporta" se obtuvo con un "_merge naive_" (scores fijos, orden vector-primero, sin calibración). La literatura citada sugiere que una fusión calibrada con un ponderador ajustado al dominio, podría recuperar parte del valor del componente léxico sin el costo en _recall_ que mostró la versión actual. Probar una fusión con el peso calibrado (p. ej. un alpha dominado por el vector) sería la contraparte natural de la conclusión de esta entrada.

## Referencias

- **Bruch, S., Gai, S., & Ingber, A. (2023).** *An Analysis of Fusion Functions for Hybrid Retrieval.* ACM TOIS / arXiv:2210.11934. — Análisis de fusión híbrida: la combinación convexa supera al RRF y requiere calibrar el peso del componente léxico; la fusión naive no siempre ayuda.
- **Benham, R., Mackenzie, J., Moffat, A., & Culpepper, J. S. (2019).** *Boosting Search Performance Using Query Variations.* ACM TOIS / arXiv:1811.06147. — Fusión de rankings (base del RRF usado en búsqueda híbrida).
- **Reimers, N., & Gurevych, I. (2019).** *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.* arXiv:1908.10084. — Fundamentos de los embeddings de frases (familia de `all-minilm`).
- **Muennighoff, N., et al. (2022).** *MTEB: Massive Text Embedding Benchmark.* arXiv:2210.07316. — Benchmark de modelos de embeddings (contexto de la elección voyage-4-lite vs all-minilm).
- **Flax Sentence Embeddings Team (2021).** *Stack Exchange question pairs.* HuggingFace — `flax-sentence-embeddings/stackexchange_titlebody_best_and_down_voted_answer_jsonl`. — Dataset utilizado; diseñado originalmente para entrenar embeddings por aprendizaje contrastivo.

- **Gao, Y., et al. (2023).** *Retrieval-Augmented Generation for Large Language Models: A Survey.* arXiv:2312.10997. — Documenta el chunk size como dial de trade-off precisión/recall y las técnicas de augmentation del contexto recuperado.
- **Chen, T., Wang, H., Chen, S., Yu, W., Ma, K., Zhao, X., Zhang, H., & Yu, D. (2023).** *Dense X Retrieval: What Retrieval Granularity Should We Use?* arXiv:2312.06648. — La granularidad de la unidad de indexación impacta el rendimiento del retrieval: las unidades finas y semánticamente autónomas (proposiciones) superan a los pasajes; base para el argumento de que el chunk alineado con la unidad semántica reduce el trade-off.

**Sobre la comparabilidad con otros trabajos**: el dataset de Stack Exchange fue creado para **entrenamiento de embeddings por contraste**, y no encontramos un trabajo publicado que lo use como corpus de un RAG de soporte IT evaluado con métricas contextuales (ContextualPrecision/Recall de DeepEval) — el uso canónico del dataset es el entrenamiento de modelos (p. ej. `Hum-Works/lodestone-base-4096-v1`, entrenado sobre él). Por eso no existe un _baseline_ directo comparable con nuestras métricas específicas: nuestros números son una referencia nueva, y la comparación más sólida es la interna (contra la _baseline_ corregida con el mismo pipeline).

---

*Esta entrada es parte de la serie de documentación del proyecto. Las métricas provienen de las evaluaciones ejecutadas con DeepEval sobre 50 pares golden estratificados, con exclusión de los pares del índice (midiendo generalización).*
