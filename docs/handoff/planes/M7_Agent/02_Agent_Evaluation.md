# Issue: Evaluate Multi-Step Agent vs Baseline RAG

## Meta

- **Milestone**: M7 — Multi-Step Diagnosis Agent
- **Labels**: `initiative:agentic-diagnosis`, `phase:eval`, `type:task`, `priority:high`, `area:notebooks`
- **Depends on**: M7 issue 01 (graph implementation)
- **Estimate**: 1 day

## Description

Run the M7 multi-step agent against the same 50 golden QA pairs used in M4 and compare the results. The comparison isolates the effect of multi-step reasoning: M4's retrieval pipeline is identical (same embeddings, same lexical search), the only variable is the agent's ability to iterate and reformulate.

## Evaluation protocol

1. Sample 50 questions from `golden_se_200.json` (same seed=42, same sample as M4)
2. For each question, call the agent's `/chat/` endpoint with `{"message": question}`
3. The agent runs autonomously (no human-in-the-loop)
4. Extract the final answer from the agent's response
5. Evaluate with DeepEval using the same judge model as M4 (`openai/gpt-5.6-luna`)

### Metrics (generation-stage only — same rationale as M6)

| Metric | Why |
|--------|-----|
| Correctness | End-to-end quality |
| Faithfulness | Does multi-step introduce hallucinations or reduce them? |
| AnswerRelevancy | Does reformulation help or hurt relevance? |

ContextualPrecision/Recall excluded — retrieval pipeline unchanged from M4.

### Additional agent-specific metrics (not DeepEval, manual calculation)

| Metric | How to measure |
|--------|---------------|
| Avg iterations per query | Count rounds in agent trace |
| % queries that required > 1 iteration | Proportion of multi-step cases |
| Avg latency | Wall clock time from request to final answer |
| Avg context documents retrieved | Cumulative across iterations |

## Comparative analysis

```markdown
| Métrica | M4 (RAG directo) | M7 (Agente multi-paso) | Δ |
|---------|:---:|:---:|:---:|
| Correctness | ? | ? | ? |
| Faithfulness | ? | ? | ? |
| AnswerRelevancy | ? | ? | ? |
| Avg iterations | 1 | ? | — |
| Avg latency | ~3s | ? | — |
```

## Acceptance criteria

- [ ] 50 golden QA pairs evaluated through M7 agent
- [ ] DeepEval metrics (Correctness, Faithfulness, AnswerRelevancy) computed
- [ ] Agent-specific metrics (iterations, latency, context volume) extracted from traces
- [ ] Comparative table: M4 baseline vs M7 agent
- [ ] Analysis: which query types benefit most from multi-step?
- [ ] `M7_results.md` committed with full analysis

## Cost estimate

| Item | Cost |
|------|------|
| Agent LLM calls (analyze + evaluate + refine + generate, ~3 calls/query avg, 50 queries) | ~$0.30 |
| Judge LLM calls (3 metrics × 50 queries) | ~$0.30 |
| **Total** | **~$0.60** |

## References

- M4 evaluation results: `evaluation_notebooks/raw_results/`
- Golden QA: `evaluation_notebooks/goldens/golden_se_200.json`
- Overview: `plans/M7_Agent/00_Agent_Overview.md`
