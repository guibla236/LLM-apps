# D6 — Primer intento de mejorar métricas (`718a5f25`)

- **Fechas**: 2026-05-29 → 2026-05-31
- **Turnos**: 37
- **Transcripción**: [`../transcripciones/718a5f25-224b-4fab-9603-a5d5e5a78f91.md`](../transcripciones/718a5f25-224b-4fab-9603-a5d5e5a78f91.md)

---

## Qué se buscaba

Antes de decidir la migración de dataset: “revisá el código del RAG y decime qué podemos hacer para
mejorar las métricas”. Incluye la idea de **múltiples índices de Pinecone** para probar chunkings.

## Qué se hizo

- Análisis del código y propuesta de líneas de mejora (embeddings, chunking, índices alternativos,
  reranking).
- Construcción de un **notebook evaluador** independiente (en `evaluation_notebooks/`), en inglés,
  para no depender de la evaluación embebida en la API.
- Pelea larga con el tooling: 422 del endpoint, `KeyError: 'verdicts'`, OpenAI API key inexistente,
  venv equivocado, “no tests encontrados”, salidas que no se guardaban.

## Por qué importa

1. Es el **origen del evaluador standalone** que después se convirtió en `run_eval.py`.
2. Muestra los dolores concretos (paths, venv, credenciales, persistencia de resultados) que M2
   terminó resolviendo con `--append-to`, reintentos y CSV incremental.
3. Deja claro que la idea de “varios índices para comparar chunkings” se evaluó y se resolvió después
   con **namespaces + reindexado configurable** (M4), no con múltiples índices.

## Citas

- “Tenemos dos golden QAs… ¿cuál tendríamos que usar acá?”
- “La librería no la encuentra porque está instalada en un venv. Usalo.”
- “El error sigue ahí. Encontrá una solución. Además tenés un montón de boilerplate en la celda 5 que es un desastre.”
