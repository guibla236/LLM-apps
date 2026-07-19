# Introducción

Previamente realicé el ejercicio de implementar un sistema RAG utilizando 750 tickets de soporte generados sintéticamente, que se valiera de registros de resoluciones de los mismos y consumiera algunas _Knowledge Bases_ que giraban alrededor de los mismos para poder responder preguntas de soporte IT de Nivel 1, tales como problemas de redes, infraestructura, movilidad, ciberseguridad, etcétera.

Si bien el experimento resultó exitoso en la medida que pude construir con mis propias manos un sistema RAG funcional y con su variante agéntica, las métricas de evaluación arrojaron bastante pobres. Antes este escenario, distintas soluciones aparecían como posibles causantes de las mismas: mala estrategia de chunking, LLMs demasiado baratos para las etapas de aumentado y generación, baja dimensionalidad de los _embeddings_, una arquitectura que intentaba encontrar respuestas en lugares equivocados, entre otras tantas posibles causas que pudieran estar transformando un ejemplo de esta técnica a todas luces trivial, en algo fallido.

¿Y si el problema está en los datos sintéticos? Esta pregunta me surgió cuando, recomendado por mi background académico, me tocó asesorar equipos con problemas similares. Allí, volví sobre mi experiencia en este proyecto de demostración para empezar a cuestionarme mi estrategia inicial de ir realizando mejoras y progresivamente ir evaluando los resultados. 

En el mundo real me ha tocado trabajar con datos reales. Los datos reales tienen sus problemas pero también tienen mecanismos que permiten evaluarlos de una forma que es también realista. Los datos generados por LLMs pueden sufrir tanto de halucinaciones como de una perfección que el mundo real no contiene y que transforma métricas simples, en quimeras imposibles.

Es por eso que antes de empezar desesperadamente a intentar corregir uno a uno los problemas del RAG, aplicando mejoras y mediciones sobre todas las eventuales variantes e hiperparámetros de esta arquitectura de búsqueda y generación de respuestas, me propuse el sinceramiento de un sistema que pretende dar respuestas útiles a preguntas realistas. Llega el momento, entonces, de indagar en la realidad si existe un conjunto de datos que se adapte al problema y que permita a esta aplicación, responder preguntas reales.

# En busca del conjunto de datos real

Existen varios conjuntos de datos públicos disponibles en la web que permiten construir una versión realista de esta solución. Tras evaluar distintas opciones, la que me resultó de mayor interés fue el conjunto de datos de Huggingface conocido como [`flax-sentence-embeddings/stackexchange_titlebody_best_and_down_voted_answer_jsonl`](https://huggingface.co/datasets/flax-sentence-embeddings/stackexchange_titlebody_best_and_down_voted_answer_jsonl).

Este conjunto de datos contiene 210.000 pares de preguntas y respuestas extraídas automáticamente de la plataforma [Stack Exchange](https://stackexchange.com/), de los cuales alrededor de 60.000 pares corresponden a hilos de discusión sobre temas relacionados a IT (que es el objetivo de este RAG), razón por la que se podrían utilizar solo estos.

<center>

| Community | Pares |
|-----------|-------|
| superuser | 17425 |
| askubuntu | 9975 |
| serverfault | 7969 |
| apple | 6696 |
| unix | 6173 |
| security | 3069 |
| android | 2830 |
| dba | 2502 |
| webapps | 1906 |
| sharepoint | 1691 |
| networkengineering | 476 |
| devops | 53 |

</center>

De las aproximadamente 60.000 preguntas de IT, casi la mitad provienen de los sub-foros `superuser` y `askubuntu`, mientras que el resto se distribuye en los otros 10 sub-foros restantes. Esto es relevante porque luego nos resultará útil filtrar por sub-foro y así poder construir un RAG especializado en un tema particular, o bien uno más generalista que abarque todos los temas de soporte IT.

## Descripción del conjunto de datos

El dataset brinda tan solo tres columnas: 
1. `title_body` presenta el título del hilo y la descripción dada por su creador buscando respuestas.
2. `upvoted_answer`: es la respuesta más votada por la comunidad. Esta columna es clave porque será nuestra respuesta realista al problema del usuario, nuestro _ground truth_ al momento de evaluar el RAG.
3. `downvoted_answer`: La peor respuesta de todo el hilo.

A estas tres columnas se le suma una cuarta que indica a qué sub-foro de StackExchange pertenece el hilo de discusión (`community`).

De más queda decir que las columnas relevantes son las primeras dos, mientras que la tercera podría servirnos para realizar algún experimento de _contrastive learning_ y la cuarta nos permite filtrar por sub-foro.

## ¿Qué tan bueno es este conjunto de datos?

Un punto clave del conjunto de datos es que filtra toda pregunta en que la respuesta mejor votada tenga un saldo de votos de al menos 100 positivos de distancia respecto a la segunda, o donde la peor respuesta tenga _score_ negativo. Esto es un arma de doble filo para nuestro objetivo de crear un RAG con estos datosporque si pensamos en un _edge case_ donde una pregunta solo tenga respuestas negativas, la misma puede llegar a ser incluida sí la respuesta menos peor votada aventaja a la peor votada por 100 votos o más.

<div align="center">

![Fuente: https://github.com/nreimers/flax-sentence-embeddings/blob/de583831d9b8b3454ed62fb74f783380ab2e933b/datasets/stackexchange/transforms.py#L111](images/extractor.png)


Fuente: https://github.com/nreimers/flax-sentence-embeddings/blob/de583831d9b8b3454ed62fb74f783380ab2e933b/datasets/stackexchange/transforms.py#L111

</div>

Dado que el conjunto de datos actual no brinda una columna con el score de la respuesta usada y por lo tanto no podemos aplicar la regla de que el score tiene que ser positivo  y que si queremos computar esos scores habría que descargar 25 GB de datos (algo que es un despropósito por algo que resulta ser un _edge case_), se plantea realizar un análisis exploratorio del conjunto de datos que permita establecer qué mejoras se pueden implementar a partir de filtrar pares pregunta-respuesta que resulten irrelevantes o no realicen un gran aporte a las respuestas que el sistema sea capaz de generar.

Lo anterior es clave por otro punto de este tipo de sistemas: cuando tenemos tantas posibles preguntas, su inserción en un espacio vectorial puede generar que las K más cercanas que extrae el RAG no sean las mejores y en consecuencia se termine extrayendo respuestas basura surgidas del ruido incluido en el _dataset_. Al mismo tiempo, un espacio vectorial más poblado requiere mayor tiempo de cálculos de distancias y por consiguiente, incrementa la latencia del _retrieval_. Por estas razones es que querremos controlar el trade-off entre calidad y latencia a partir de buscar formas de incrementar la calidad de los datos que preservamos en la base de datos vectorial.

Junto a lo anterior y más allá de que siempre hay que realizar un _Exploratory Data Analysis_ cuando se obtiene un nuevo conjunto de datos, la realidad es que también estaría bueno medir cuántas preguntas tienen respuestas técnicas que sean consideradas propicias para un contexto de soporte IT. Si después de analizar esto, encontramos que la cobertura temática es amplia, podremos decir que el conjunto de datos vale la pena para el problema que queremos resolver con el mismo.

# Resumen

La presente entrada plantea un camino para afrontar cambios a un experimento de RAG que fue exitoso en la etapa de implementación pero no obtuvo métricas aceptables.

Antes de comenzar el camino de las mejoras típicas que se recomiendan para incrementar métricas, se plantea como hipótesis mejorar la materia prima: los datos 750 tickets de soporte sintéticos que se usan para responder las preguntas de los usuarios pueden resultar insuficientes o demasiado rígidos para el objetivo planteado. 

Dado que no se cuenta con una base de datos empresarial de tickets, resulta atractivo intentar construir lo mismo pero utilizando respuestas en foros públicos de internet. Existe un conjunto de datos en Huggingface que sirve para nuestro caso pero naturalmente surgen dudas relativas a su calidad y relevancia para la aplicación que se busca construir.

Como parte de este artículo, se buscó presentar el problema y los distintos pasos que se harán para solventarlo. En el siguiente artículo se indagará sobre la calidad del corpus propuesto y se discutirán los distintos mecanismos que permitan incrementarla sin perder generalidad temática, junto a la decisión relativa a la calidad mínima necesaria como para considerar usarlo en sustitución de los datos sintéticos.

# Referencias

- [flax-sentence-embeddings/stackexchange_titlebody_best_and_down_voted_answer_jsonl](https://huggingface.co/datasets/flax-sentence-embeddings/stackexchange_titlebody_best_and_down_voted_answer_jsonl)
- [Stack Exchange](https://stackexchange.com/)
- Publicación original sobre el hackatón colaborativo que se organizó entre Huggingface y Google Cloud en 2021 para entrenar sentence embeddings con estos datos: [Train the Best Sentence Embedding Model Ever with 1B Training Pairs](https://discuss.huggingface.co/t/train-the-best-sentence-embedding-model-ever-with-1b-training-pairs/7354)
- Entrada sobre los resultados del hackatón en el blog de Huggingface: [Train a Sentence Embedding Model with 1 Billion Training Pairs](https://huggingface.co/blog/1b-sentence-embeddings)
