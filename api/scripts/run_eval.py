#!/usr/bin/env python3
"""
Standalone RAG Evaluation Runner — CI/CD ready.

Loads a golden QA JSON, queries the RAG API for each question, runs
DeepEval metrics against the retrieved context, and saves results
as CSV + JSON aggregate.

Usage:
    # Basic evaluation
    python scripts/run_eval.py \\
        --api-url http://localhost:8000 \\
        --golden-json ../evaluation_notebooks/goldens/golden_se_200.json \\
        --scenario-name baseline_vector_only

    # With API key auth
    python scripts/run_eval.py \\
        --api-url http://localhost:8000 \\
        --golden-json ../evaluation_notebooks/goldens/golden_se_200.json \\
        --search-method vector_only \\
        --k 10 \\
        --api-key your-api-key-here

    # Custom output directory
    python scripts/run_eval.py \\
        --api-url http://localhost:8000 \\
        --golden-json ../evaluation_notebooks/goldens/golden_se_200.json \\
        --output-dir ../evaluation_notebooks/raw_results/ \\
        --delay 3.0

Requires:
    - Running RAG API at --api-url
    - OPENROUTER_API_KEY environment variable (or OpenRouter API key in .env)
    - deepeval, langchain-openai, requests installed
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv(str(Path(__file__).parent.parent / ".env"))

import requests
from tqdm import tqdm

# DeepEval imports
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import (
    GEval,
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
)
from deepeval.models.base_model import DeepEvalBaseLLM
from langchain_openai import ChatOpenAI

# ── Constants ──

DEFAULT_JUDGE_MODEL = "deepseek/deepseek-v4-flash"  # Dev: cheap. Final: --judge-model openai/gpt-5-nano
DEFAULT_DELAY = 2.0  # seconds between API calls (rate limit: 10/min)
DEFAULT_K = 5
REQUIRED_METRICS = [
    "correctness",
    "faithfulness",
    "answer_relevancy",
    "contextual_precision",
    "contextual_recall",
]

# Retry config
RETRY_MAX_ATTEMPTS = 4
RETRY_BASE_SECONDS = 2.0
RETRY_MAX_SECONDS = 40.0
RETRY_JITTER_SECONDS = 1.0


# ── Custom DeepEval wrapper ──


class CustomDeepEval(DeepEvalBaseLLM):
    """Adapts a LangChain ChatOpenAI model to DeepEval's LLM interface."""

    def __init__(self, model, model_name: str = "unknown"):
        self.model = model
        self._model_name = model_name

    def load_model(self):
        return self.model

    def generate(self, prompt: str) -> str:
        return self.model.invoke(prompt).content

    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)

    def get_model_name(self):
        return self._model_name

    def generate_raw_response(self, prompt: str, **kwargs):
        """DeepEval's GEval calls this. Falls back to generate_with_schema_and_extract if it raises AttributeError,
        but some metric versions call it directly. We implement it for compatibility."""
        from collections import namedtuple
        result = self.generate(prompt)
        _log_debug(f"generate_raw_response() returning: {repr(result[:300])}")
        # Simulate OpenAI-style response object
        Choice = namedtuple("Choice", ["message"])
        Message = namedtuple("Message", ["content"])
        RawResponse = namedtuple("RawResponse", ["choices"])
        return RawResponse(choices=[Choice(message=Message(content=result))]), 0.0


# ── API client ──


def call_raw_search(
    api_url: str,
    query: str,
    search_method: str,
    search_type: str,
    k: int,
    use_hyde: bool,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Call /api/raw_unified_search and return result list."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-KEY"] = api_key

    payload = {
        "query": query,
        "search_type": search_type,
        "search_method": search_method,
        "k": k,
        "use_hyde": use_hyde,
    }

    try:
        resp = requests.post(
            f"{api_url}/api/raw_unified_search",
            json=payload,
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        # API returns a list of context strings directly
        if isinstance(data, list):
            return [{"id": f"result-{i}", "content": item, "score": 1.0}
                    for i, item in enumerate(data)]
        return data.get("results", [])
    except requests.exceptions.RequestException as e:
        print(f"\n  ⚠  API request failed: {e}")
        return []


def call_augment_search(
    api_url: str,
    query: str,
    search_type: str,
    k: int,
    hybrid_search: bool,
    use_hyde: bool,
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Call /api/augment_search_results and return the LLM-generated summary."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-KEY"] = api_key

    payload = {
        "description": query,
        "search_type": search_type,
        "k": k,
        "hybrid_search": hybrid_search,
        "use_hyde": use_hyde,
    }

    try:
        resp = requests.post(
            f"{api_url}/api/augment_search_results",
            json=payload,
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"\n  ⚠  Augment API request failed: {e}")
        return None


def results_to_context(results: List[Dict[str, Any]]) -> str:
    """Convert API search results to a single context string."""
    if not results:
        return ""

    parts = []
    for i, r in enumerate(results, 1):
        content = r.get("content", "")
        score = r.get("score", 0)
        rid = r.get("id", "")
        parts.append(f"[{i}] ID={rid} (score={score:.4f}): {content}")

    return "\n\n".join(parts)


def results_to_retrieval_context(results: List[Dict[str, Any]]) -> List[str]:
    """Convert API results to list of text chunks for retrieval_context."""
    return [r.get("content", "") for r in results if r.get("content")]


# ── Metric builders ──


def _build_metrics(judge_model) -> dict:
    """Build the 5 evaluation metrics with the given judge model."""
    return {
        "correctness": GEval(
            name="Correctness",
            criteria=(
                "Determine whether the actual output is factually correct "
                "based on the expected output."
            ),
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
            model=judge_model,
        ),
        "faithfulness": FaithfulnessMetric(
            threshold=0.5,
            model=judge_model,
            include_reason=True,
        ),
        "answer_relevancy": AnswerRelevancyMetric(
            threshold=0.5,
            model=judge_model,
            include_reason=True,
        ),
        "contextual_precision": ContextualPrecisionMetric(
            threshold=0.5,
            model=judge_model,
            include_reason=True,
        ),
        "contextual_recall": ContextualRecallMetric(
            threshold=0.5,
            model=judge_model,
            include_reason=True,
        ),
    }


def _measure_metric(metric, test_case: LLMTestCase, attempt: int = 1) -> Optional[float]:
    """Measure a single metric with retry logic (exponential backoff)."""
    import random as _random

    try:
        metric.measure(test_case)
        return metric.score
    except Exception as e:
        status = _extract_status_code(e)
        if status and status in (429, 500, 502, 503, 504):
            if attempt < RETRY_MAX_ATTEMPTS:
                delay = min(
                    RETRY_BASE_SECONDS * (2 ** (attempt - 1)),
                    RETRY_MAX_SECONDS,
                )
                jitter = _random.uniform(0, RETRY_JITTER_SECONDS)
                total_delay = delay + jitter
                print(
                    f"\n  ⚡ Retry {attempt}/{RETRY_MAX_ATTEMPTS} for {metric.__class__.__name__} "
                    f"after {total_delay:.1f}s (HTTP {status})"
                )
                time.sleep(total_delay)
                return _measure_metric(metric, test_case, attempt + 1)
        print(f"\n  ⚠  {metric.__class__.__name__} failed: {e}")
        return None


def _extract_status_code(exc: Exception):
    """Extract HTTP status code from exception."""
    for attr in ("status_code", "http_status", "code"):
        val = getattr(exc, attr, None)
        if isinstance(val, int):
            return val
    response = getattr(exc, "response", None)
    if response is not None:
        status = getattr(response, "status_code", None)
        if isinstance(status, int):
            return status
    return None


# ── CSV output ──


def _csv_path(output_dir: str, scenario_name: str, golden_name: str) -> str:
    """Generate timestamped CSV path."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, f"{scenario_name}_{golden_name}_{ts}.csv")


def _write_csv_header(csv_path: str):
    """Write CSV header if file doesn't exist."""
    if os.path.exists(csv_path):
        return
    fieldnames = [
        "timestamp",
        "question",
        "ticketId",
        "kb",
        "contextual_precision",
        "contextual_recall",
        "faithfulness",
        "answer_relevancy",
        "correctness",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()


def _append_csv_row(csv_path: str, row: dict):
    """Append a single result row to CSV."""
    fieldnames = [
        "timestamp",
        "question",
        "ticketId",
        "kb",
        "contextual_precision",
        "contextual_recall",
        "faithfulness",
        "answer_relevancy",
        "correctness",
    ]
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(row)


# ── JSON aggregate ──


def _json_aggregate_path(csv_path: str) -> str:
    """Derive JSON aggregate path from CSV path."""
    return csv_path.replace(".csv", "_aggregate.json")


def _compute_aggregate(rows: List[Dict]) -> dict:
    """Compute mean, median, std, min, max for each metric."""
    metrics = list(set(
        [m for m in [
            "contextual_precision", "contextual_recall",
            "faithfulness", "answer_relevancy", "correctness",
        ] if any(m in r for r in rows)]
    ))
    aggregate = {"total_questions": len(rows)}
    for m in metrics:
        vals = [r[m] for r in rows if r[m] is not None]
        if not vals:
            aggregate[m] = {"mean": None, "median": None, "count": 0}
            continue
        aggregate[m] = {
            "mean": round(mean(vals), 4),
            "median": round(median(vals), 4),
            "std": round(stdev(vals), 4) if len(vals) > 1 else 0.0,
            "min": round(min(vals), 4),
            "max": round(max(vals), 4),
            "count": len(vals),
        }
    aggregate["timestamp"] = datetime.now(timezone.utc).isoformat()
    return aggregate


# ── Main ──


def main():
    parser = argparse.ArgumentParser(
        description="Standalone RAG evaluation runner — CI/CD ready"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="RAG API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--golden-json",
        required=True,
        help="Path to golden QA JSON file",
    )
    parser.add_argument(
        "--scenario-name",
        default="eval",
        help="Scenario label for output filenames (default: eval)",
    )
    parser.add_argument(
        "--search-method",
        default="hybrid",
        choices=["vector_only", "bm25_only", "hybrid"],
        help="Search method (default: hybrid)",
    )
    parser.add_argument(
        "--search-type",
        default="tickets_only",
        choices=["tickets_only", "kb_only", "both"],
        help="Search type (default: tickets_only — KBs excluded to avoid legacy Spanish content)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=DEFAULT_K,
        help=f"Number of results to retrieve (default: {DEFAULT_K})",
    )
    parser.add_argument(
        "--use-hyde",
        action="store_true",
        help="Enable HyDE for semantic search",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="X-API-KEY for authenticated endpoints",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help=f"Seconds between API calls (default: {DEFAULT_DELAY})",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for CSV/JSON results (default: evaluation_results/)",
    )
    parser.add_argument(
        "--judge-model",
        default=DEFAULT_JUDGE_MODEL,
        help=f"Judge model for DeepEval (default: {DEFAULT_JUDGE_MODEL})",
    )
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=REQUIRED_METRICS,
        choices=REQUIRED_METRICS,
        help=f"Metrics to run (default: all 5)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of questions to evaluate (for testing)",
    )
    args = parser.parse_args()

    # ── Resolve paths ──
    golden_path = Path(args.golden_json)
    if not golden_path.exists():
        print(f"ERROR: Golden file not found: {golden_path}")
        sys.exit(1)

    golden_name = golden_path.stem  # e.g. "golden_se_200"
    output_dir = args.output_dir or os.getenv(
        "EVAL_OUTPUT_DIR",
        str(Path(__file__).parent.parent.parent / "evaluation_notebooks" / "raw_results"),
    )

    # Auto-detect API key from env if not provided via CLI
    api_key = args.api_key or os.getenv("APP_API_KEY")

    # ── Load golden QA ──
    print(f"Loading golden QA from {golden_path}")
    with open(golden_path, "r", encoding="utf-8") as f:
        golden_data = json.load(f)

    if not isinstance(golden_data, list):
        print("ERROR: Golden file must be a JSON list of {question, answer, ticketId, kb}")
        sys.exit(1)

    print(f"  Loaded {len(golden_data)} pairs")

    if args.limit:
        golden_data = golden_data[: args.limit]
        print(f"  Limited to {args.limit} for testing")

    # ── Initialize judge model ──
    print(f"\nInitializing judge: {args.judge_model}")
    or_api_key = os.getenv("OPENROUTER_API_KEY")
    if not or_api_key:
        print("ERROR: OPENROUTER_API_KEY environment variable is required")
        sys.exit(1)

    llm = ChatOpenAI(
        model=args.judge_model,
        api_key=or_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.0,
    )
    judge = CustomDeepEval(llm, model_name=args.judge_model)

    # Build metrics
    metrics_map = _build_metrics(judge)
    selected_metrics = [metrics_map[m] for m in args.metrics]
    print(f"  Metrics: {', '.join(args.metrics)}")

    # ── Prepare CSV ──
    csv_path = _csv_path(output_dir, args.scenario_name, golden_name)
    _write_csv_header(csv_path)
    print(f"  Output CSV: {csv_path}")

    # ── Run evaluation ──
    print(f"\n{'='*60}")
    print(f"  Running evaluation: {args.scenario_name}")
    print(f"  Questions: {len(golden_data)}")
    print(f"  Search: {args.search_method}, k={args.k}")
    print(f"{'='*60}")

    rows: List[Dict] = []
    errors = 0

    for idx, item in enumerate(tqdm(golden_data, desc="Evaluating", unit="q")):
        question = item.get("question", "")
        expected_answer = item.get("answer", "")
        ticket_id = item.get("ticketId", "")
        kb = item.get("kb", "")

        if not question:
            print(f"\n  ⚠  Skipping item {idx}: no question field")
            continue

        # Step 1: retrieve context (raw_unified_search)
        results = call_raw_search(
            api_url=args.api_url,
            query=question,
            search_method=args.search_method,
            search_type=args.search_type,
            k=args.k,
            use_hyde=args.use_hyde,
            api_key=api_key,
        )

        retrieval_context = results_to_retrieval_context(results)

        if not retrieval_context:
            print(f"\n  ⚠  No results for question {idx}: {question[:60]}...")
            rows.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "question": question,
                "ticketId": ticket_id,
                "kb": kb,
                "contextual_precision": None,
                "contextual_recall": None,
                "faithfulness": None,
                "answer_relevancy": None,
                "correctness": None,
            })
            _append_csv_row(csv_path, rows[-1])
            errors += 1
            time.sleep(args.delay)
            continue

        # Step 2: generate answer (augment_search_results)
        augment_result = call_augment_search(
            api_url=args.api_url,
            query=question,
            search_type=args.search_type,
            k=args.k,
            hybrid_search=(args.search_method != "bm25_only"),
            use_hyde=args.use_hyde,
            api_key=api_key,
        )

        actual_output = ""
        if augment_result:
            actual_output = augment_result.get("summary", "")
        else:
            # Fallback: use context string if generation fails
            actual_output = results_to_context(results)
            print(f"\n  ⚠  Generation failed for question {idx}, using context as actual_output")

        # Build test case
        test_case = LLMTestCase(
            input=question,
            actual_output=actual_output,
            expected_output=expected_answer,
            retrieval_context=retrieval_context,
        )

        # Measure each metric
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "question": question,
            "ticketId": ticket_id,
            "kb": kb,
        }
        for metric_name, metric in zip(args.metrics, selected_metrics):
            score = _measure_metric(metric, test_case)
            row[metric_name] = round(score, 4) if score is not None else None
            if score is None:
                errors += 1

        rows.append(row)
        _append_csv_row(csv_path, row)

        # Rate limiting
        if idx < len(golden_data) - 1:
            time.sleep(args.delay)

    # ── Write JSON aggregate ──
    json_path = _json_aggregate_path(csv_path)
    aggregate = _compute_aggregate(rows)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(aggregate, f, ensure_ascii=False, indent=2)

    # ── Summary ──
    print(f"\n{'='*60}")
    print("  Evaluation Complete")
    print(f"{'='*60}")
    print(f"  Questions evaluated: {len(rows)}")
    print(f"  Errors:              {errors}")
    print(f"  CSV:                 {csv_path}")
    print(f"  JSON aggregate:      {json_path}")
    print(f"\n  {'Metric':<25} {'Mean':<10} {'Median':<10} {'Count':<8}")
    print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*8}")
    for m in args.metrics:
        stats = aggregate.get(m, {})
        mean_val = stats.get("mean")
        median_val = stats.get("median")
        count = stats.get("count", 0)
        mean_str = f"{mean_val:.4f}" if mean_val is not None else "N/A"
        median_str = f"{median_val:.4f}" if median_val is not None else "N/A"
        print(f"  {m:<25} {mean_str:<10} {median_str:<10} {count:<8}")

    # Exit code: 0 if no errors, 1 if any metric failed
    sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()
