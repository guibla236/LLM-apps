# From Diagnosis to Optimization: How to Improve the Semantic Search of a RAG Without Touching the Architecture

The previous article in this series completed the data migration and reported the evaluation metrics of the new system, which were substantially better than those obtained for the same goal using synthetic data. Once the new dataset was working and validated, the next step was to improve the quality of semantic search.

This article documents the different parts of that improvement process: the experiments, the cost decisions and the final result that defines the new search configuration of the system.

## The Starting Point

Once the new data was integrated with the previous system and everything needed was adapted, the semantic search using the `all-minilm:22m` embedding model, its 384 dimensions and the chunking established for tickets and Knowledge Bases, obtained the following retrieval metrics using GPT-5 Luna as judge:

<center>

| Metric | Vector Only | Hybrid (lexical + vector) |
|---|---:|---:|
| ContextualPrecision | 60.33% | 64.54% |
| ContextualRecall | 23.66% | 22.20% |

</center>

The embedding model was selected for being small enough to allow local embedding creation using Ollama, sufficient for the number of tickets and Knowledge Bases we had. When moving to a real corpus of 60,000 technical question-answer pairs, not only did generating them involve much longer processing times, but its semantic capacity was the main suspect behind the retrieval metric limitations.

Beyond the model itself, the semantic search had not been optimized for the corpus: we did not know whether the chunking strategies of splitting tickets into 200-character chunks with 20 characters of overlap, or 1000/100 for the KBs, were the most suitable for it.

## The Experimental Design

The exploratory analysis left two relevant findings for this stage: 75% of questions fit in a single 1000-character chunk, and the maximum length a query can have is 4,171. Taking this into account, and with access to much newer models for creating embeddings (such as Voyage 4 from early 2026), we designed a series of experiments with a single new model and two chunking strategies:

<center>

| Experiment | Embedding | Chunking |
|---|---|---|
| **P0** | voyage-4-lite (1024d) | No chunking (full document) |
| **P1** | voyage-4-lite (1024d) | Chunking suggested by the EDA (1000/100) |

</center>

`voyage-4-lite` was chosen for its best quality-price ratio ($0.02/M tokens, 1024 dimensions, MTEB of 65 points vs 56 of the previous model). Note also that the model produces 1024-dimensional vectors, which implies almost three times more semantic information that can be stored per document, something expected to also boost results.

A methodological caveat must be made: in this change we are moving several pieces at the same time. Attributing the improvements that will be observed to a specific change (model, dimensionality, chunking) is impossible.
**Important methodological decisions**:

1. **Only `vector_only` per variant**: the hybrid confounds the embedding effect with the one caused by BM25 and doubles the evaluation cost without adding value to the retrieval analysis. The hybrid is reserved for the end, with the semantic search winner.
2. **Only retrieval metrics (ContextualPrecision/Recall) in the variants**: they are the ones that answer whether the search improved. Generation questions depend on the LLM, not the embedding. However, with the idea of knowing the system's final metrics, the winner will be re-evaluated with all 5 metrics.

## Expected Results

The implementation of the new embedding model, its higher dimensionality and the less fragmented chunking strategy is expected to improve both retrieval metrics. Between the two proposed chunking strategies, two plausible scenarios are considered:

1. A trade-off between precision and recall caused by excessive fragmentation, benefiting P0 in precision and P1 in recall (and vice versa).
    - This can be observed in the RAG survey by Gao et al. (2023), which documents that chunk size generates a precision/recall trade-off: smaller chunks improve matching but cause context loss.
2. Both metrics improve simultaneously in the 1000/100 chunking experiment, which would indicate that the chunking managed to capture the largest amount of relevant information — plausible if we consider that the chunking suggested by the EDA pointed to this strategy.
    - This exception to the classic trade-off finds support in the literature: Chen et al. (2023) show that when the indexing unit (the chosen chunk) aligns with the semantic unit of the content (which is what we want the chunk to capture), retrieval improves without sacrificing precision, since it does not fragment the available semantics.

That said, a caveat must be made on the second point: for cost and time reasons, the 2000/200 or 500/50 chunking variants will not be evaluated, so it will not be possible to determine whether the chunking suggested by the EDA is optimal or whether a larger chunking could improve the metrics even further. This will be future work, but at least if it happens, the hypothesis that not chunking is the best alternative can be rejected.

## Results of the Initial Experiments

For the evaluation, as done in the [previous article](../2_post_migration_eval/post_migration_eval_en.md), the reference judge `gpt-5.6-luna` was used for all comparisons. The results obtained were the following:

<center>

| Variant | ContextualPrecision | ContextualRecall |
|---|---:|---:|
| Previous baseline (all-minilm) | 60.33% | 23.66% |
| **P0** (voyage-4-lite, no-chunk) | 64.01% | 23.92% |
| **P1** (voyage-4-lite, chunk 1000/100) | **69.40%** | **25.91%** |

</center>

The first thing that stands out when using a more modern model is that the impact is positive: **contextual precision rose 4 points with the unchunked document (P0) and 9 points with the chunking suggested by the EDA (P1)**, both relative to the baseline with the new data, both using exactly the same system but differing in the chunking strategy used. This means that the changes made to the semantic search increased the quality of the results by raising the number of relevant documents retrieved relative to the total retrieved.

When we look at contextual recall, we see that the change of model, chunking strategy and embedding dimensionality also caused a jump in the metric. The comparison between the two chunking strategies, however, does not show the classic trade-off that the literature and logic anticipated:

- **Chunking 1000/100 (P1)**: better precision (69.40%) and better recall (25.91%), implying that the chunk captures the semantics of the specific query better, which allows the retriever not only to obtain more relevant results but also to rank them better, bringing to the top the statements the system needs.
- **No chunking (P0)**: lower precision (64.01%) and lower recall (23.92%), indicating that embedding the full document dilutes the specific semantics and the documents reaching the top are not necessarily the ones containing the statements of the expected answer.

In this way we validated that the second point of the expected results had more impact than the first, with the traditional trade-off between the two chunking alternatives disappearing. This can be attributed to having followed the EDA suggestion, since 75% of the corpus questions fit in a single 1000-character chunk, which allows the 1000/100 chunking **not to fragment** the context.

That said, this conclusion is weak due to the methodological caveat made in the previous section: a larger (2000/200) or smaller (500/50) chunking was not evaluated, so it cannot be determined whether the chunking suggested by the EDA is optimal or whether a different chunking could improve the metrics further.

## The Winning Chunking

Although the improvement with the new embedding model is undisputed, what remains to be discussed is the chunking method. **The winner is P1: voyage-4-lite with 1000/100 chunking**, the variant that improved both retrieval metrics against the baseline and P0, with the reference judge (GPT-5.6-luna).

For the closing, the **5 metrics of the winner were executed with an independent judge** (`openai/gpt-5.6-luna`, from the OpenAI family, different from the generator, which belongs to the DeepSeek model family). The final results in `vector_only`:

<center>

| Metric | Baseline (all-minilm) | **P1 final (voyage-4-lite)** |
|---|---:|---:|
| Correctness | 50.40% | **51.00%** |
| Faithfulness | **98.91%** | 98.38% |
| AnswerRelevancy | 96.14% | **95.86%** |
| ContextualPrecision | 60.33% | **69.40%** |
| ContextualRecall | 23.66% | **25.91%** |

</center>

The constant-judge comparison between both columns allows sizing the real improvement of the embedding change: ContextualPrecision rises 9 points (60.33% → 69.40%) and ContextualRecall rises about 2.25 (23.66% → 25.91%), while Correctness barely changes (+0.6 pts, something that could fall within judge noise).

## Incorporating Lexical Search and the Validity of the Hybrid System

To put this result in context, it is worth remembering where we come from. On the previous baseline (all-minilm), the hybrid **did contribute** relative to vector-only, measured with the same reference judge:

<center>

| Metric | Baseline vector_only (luna) | Baseline hybrid (luna) | Δ |
|---|---:|---:|---:|
| Correctness | **50.40%** | 46.80% | −3.60 |
| Faithfulness | **98.91%** | 98.78% | −0.13 |
| AnswerRelevancy | 96.14% | **96.77%** | +0.63 |
| ContextualPrecision | 60.33% | **64.54%** | +4.21 |
| ContextualRecall | **23.66%** | 22.20% | −1.46 |

</center>

With the migration of lexical search to **MongoDB Atlas Search** (replacing the local 125 MB BM25 index, impossible to deploy on Vercel), the final run of the winner's `hybrid` was executed with the same independent judge. The previous table under the new conditions yielded the following results:

<center>

| Metric | P1 vector_only (luna) | P1 hybrid (luna) | Δ |
|---|---:|---:|---:|
| Correctness | **51.00%** | 49.80% | −1.20 |
| Faithfulness | **98.38%** | 98.05% | −0.33 |
| AnswerRelevancy | 95.86% | **95.94%** | +0.08 |
| ContextualPrecision | 69.40% | **69.65%** | +0.25 |
| ContextualRecall | **25.91%** | 23.19% | **−2.72** |

</center>

**The hybrid no longer contributes.** In the era of the previous model, chunking and dimensionality (all-minilm), the hybrid added **4.21 points of CP** (60.33% → 64.54%) at the cost of −1.46 of CR, as the table above shows, indicating that the lexical component complemented the semantic search. With `voyage-4-lite`, the semantic search is so good that the lexical component **overlaps** with the dense one: it adds +0.25 of CP but loses −2.72 of CR (lexical results displace relevant vector context).

**What could be going on?** The observed behavior could be associated with what Bruch, Gai & Ingber (2023) find in *An Analysis of Fusion Functions for Hybrid Retrieval*: these authors show that hybrid fusion of results (semantic and lexical) **has no single recipe**. Thus, the way of combining the semantic score and the lexical score for the same document found by both search methods affects the fusion outcome. Moreover, they argue that the parameter that extracts the best of both components **must be calibrated for each domain**, which tells us there is no magic value for the weight.

The union of results implemented here did not calibrate that balance: it assigned fixed scores (0.75 to the vector, 0.8 to the lexical) and gave ordering priority to vector results, without adjusting that relationship to the corpus. The consequence is that when the semantic component is strong (as in the P1 experiments where queries are well covered), that imbalance in favor of the lexical displaces relevant vector context, which could be behind the 2.72 percentage point drop in CR in the tests.

**The practical conclusion**: for the Stack Exchange corpus with voyage-4-lite, `vector_only` is the optimal default configuration. The hybrid, or lexical search directly, remains available for queries with heavy lexical load (error codes, command names, IDs), where exact search is expected to contribute. The decision of when to use it is a natural candidate for the **dynamic routing** that the multi-step diagnostic agent will implement, which will be the subject of a future improvement.

# Synthesis

With this article the system's search configuration is defined, as a result of the decisions evaluated in the experiments conducted here:

<center>

| Component | Final configuration |
|---|---|
| **Embedding model** | `voyage-4-lite` (1024 dimensions) — replaces `all-minilm:22m` (384d) |
| **Chunking** | 1000/100 (suggested by the EDA: 75% of questions fit in a single chunk) |
| **Semantic search** | Vector search over the `tickets-m4-exp-b` index (namespace `kb-se-all`) |
| **Lexical search** | MongoDB Atlas Search (replaces the local 125 MB BM25, impossible to deploy in production) |
| **Default mode** | `vector_only` — the hybrid no longer contributes with the new embedding (it overlaps with the dense one) |
| **Evaluation judge** | `gpt-5.6-luna` (independent of the generator, reference judge of the series) |

</center>

The system's final metrics in its definitive configuration (`vector_only`, GPT-5.6 Luna judge):

<center>

| Metric | Final result |
|---|---:|
| Correctness | **51.00%** |
| Faithfulness | **98.38%** |
| AnswerRelevancy | **95.86%** |
| ContextualPrecision | **69.40%** |
| ContextualRecall | **25.91%** |

</center>

The system thus ends up with an optimized semantic search that improves contextual precision by ~9 points over the constant-judge baseline (60.33% → 69.40%), with chunking aligned with the corpus distribution (which avoids the precision/recall trade-off by not fragmenting the typical document).

## What Comes Next

With the semantic search optimized and the lexical one migrated to MongoDB Atlas Search (which allows it to work in production without the local file), the search improvement stage is considered closed, beyond the fact that it could be deepened with research on more alternatives that validate or qualify the architectural decisions made here.

After this, we will evaluate whether, as the EDA also suggests, we can implement smaller and cheaper models for simpler queries based on knowing the answer length.

Once we have results from that research, we will proceed with an improvement: making the RAG somewhat agentic through a **multi-step diagnostic agent**, which — motivated by the hybrid finding — could route queries better between semantic and lexical search and iterate until it has enough context.

## Caveats That Could Motivate Future Analysis

This article leaves a solid, data-backed search configuration defined, but also several open questions worth exploring to refine or confirm the decisions made:

**1. Isolating the effect of embedding dimensionality.** The change from all-minilm (384 dimensions) to voyage-4-lite (1024) moved both the model and its dimensionality at the same time, and the observed improvements cannot be attributed to a single one of those pieces. Isolating dimensionality is not straightforward: `all-minilm` does not support 1024 dimensions (its architecture fixes it at 384), nor can voyage be easily reduced to 384 (unless some dimensionality reduction technique is implemented). The different dimensionalities that Voyage 4 offers could also be tested to find out which one is ideal.

**2. Mapping chunking around the optimal point.** The conclusion that 1000/100 is the point where the chunk does not fragment the typical document relied on comparing only two strategies (no chunking vs 1000/100). The larger chunking (2000/200) and a smaller one (500/50), plus an intermediate point (1500/150), remain unexplored. Testing them would show whether 1000/100 is a local maximum or whether the dial can be turned further in either direction, and would validate with more evidence the EDA hypothesis that chunk size should align with the corpus length distribution.

**3. Calibrating hybrid fusion instead of discarding it.** The verdict that the hybrid "no longer contributes" was obtained with a "naive merge" (fixed scores, vector-first ordering, no calibration). The cited literature suggests that a calibrated fusion with a domain-tuned weight could recover part of the lexical component's value without the recall cost shown by the current version. Testing a fusion with a calibrated weight (e.g., a vector-dominated alpha) would be the natural counterpart to this article's conclusion.

## References

- **Bruch, S., Gai, S., & Ingber, A. (2023).** *An Analysis of Fusion Functions for Hybrid Retrieval.* ACM TOIS / arXiv:2210.11934. — Analysis of hybrid fusion: the convex combination outperforms RRF and requires calibrating the lexical component weight; naive fusion does not always help.
- **Benham, R., Mackenzie, J., Moffat, A., & Culpepper, J. S. (2019).** *Boosting Search Performance Using Query Variations.* ACM TOIS / arXiv:1811.06147. — Ranking fusion (basis of the RRF used in hybrid search).
- **Reimers, N., & Gurevych, I. (2019).** *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.* arXiv:1908.10084. — Foundations of sentence embeddings (family of `all-minilm`).
- **Muennighoff, N., et al. (2022).** *MTEB: Massive Text Embedding Benchmark.* arXiv:2210.07316. — Benchmark of embedding models (context of the voyage-4-lite vs all-minilm choice).
- **Flax Sentence Embeddings Team (2021).** *Stack Exchange question pairs.* HuggingFace — `flax-sentence-embeddings/stackexchange_titlebody_best_and_down_voted_answer_jsonl`. — Dataset used; originally designed for training embeddings through contrastive learning.

- **Gao, Y., et al. (2023).** *Retrieval-Augmented Generation for Large Language Models: A Survey.* arXiv:2312.10997. — Documents chunk size as a precision/recall trade-off dial and context augmentation techniques for retrieved context.
- **Chen, T., Wang, H., Chen, S., Yu, W., Ma, K., Zhao, X., Zhang, H., & Yu, D. (2023).** *Dense X Retrieval: What Retrieval Granularity Should We Use?* arXiv:2312.06648. — The granularity of the indexing unit impacts retrieval performance: fine, semantically autonomous units (propositions) outperform passages; basis for the argument that a chunk aligned with the semantic unit reduces the trade-off.

**On comparability with other work**: the Stack Exchange dataset was created for **contrastive embedding training**, and we did not find published work using it as an IT-support RAG corpus evaluated with contextual metrics (DeepEval's ContextualPrecision/Recall) — the canonical use of the dataset is model training (e.g., `Hum-Works/lodestone-base-4096-v1`, trained on it). That is why there is no direct comparable baseline for our specific metrics: our numbers are a new reference, and the most solid comparison is the internal one (against the baseline corrected with the same pipeline).

---

*This article is part of the project documentation series. The metrics come from evaluations executed with DeepEval over 50 stratified golden pairs, with index pairs excluded (measuring generalization).*
