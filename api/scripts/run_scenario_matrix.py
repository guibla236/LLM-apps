#!/usr/bin/env python3
"""
Scenario Matrix Orchestrator — runs 4 RAG scenarios against golden QA datasets.

Invokes `run_eval.py` for each scenario × golden combination, then generates
a comparative summary table.

Usage:
    # Run all available scenarios
    python scripts/run_scenario_matrix.py

    # Dry-run (show what would be executed)
    python scripts/run_scenario_matrix.py --dry-run

    # Run only vector_only and hybrid
    python scripts/run_scenario_matrix.py --scenarios 1 2

Requires:
    - GROQ_API_KEY environment variable
    - Running RAG API at --api-url
    - run_eval.py in the same directory
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Load .env
from dotenv import load_dotenv
load_dotenv(str(Path(__file__).parent.parent / ".env"))

# ── Paths ──

API_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = API_DIR / "scripts"
RUN_EVAL = SCRIPTS_DIR / "run_eval.py"
GOLDENS_DIR = API_DIR.parent / "evaluation_notebooks" / "goldens"
RAW_RESULTS_DIR = API_DIR.parent / "evaluation_notebooks" / "raw_results"

# ── Scenario definitions ──

SCENARIOS = [
    {
        "id": 1,
        "name": "baseline_vector_only",
        "label": "1. Baseline (Vector Only, Recursive Chunking)",
        "search_method": "vector_only",
        "available": True,
        "note": None,
    },
    {
        "id": 2,
        "name": "hybrid_no_rrf",
        "label": "2. Hybrid, No RRF (BM25 + Vector)",
        "search_method": "hybrid",
        "available": True,
        "note": None,
    },
    {
        "id": 3,
        "name": "hybrid_rrf_semantic",
        "label": "3. Hybrid + RRF + Semantic Chunking",
        "search_method": "hybrid",
        "available": False,
        "note": "Requires kb-se-semantic namespace — not created in M1. Deferred to M4.",
    },
    {
        "id": 4,
        "name": "hybrid_rrf_markdown",
        "label": "4. Hybrid + RRF + Markdown Headers Chunking",
        "search_method": "hybrid",
        "available": False,
        "note": "Requires kb-se-markdown namespace — not created in M1. Deferred to M4.",
    },
]

GOLDEN_FILES = [
    {
        "name": "golden_se_200",
        "path": GOLDENS_DIR / "golden_se_200.json",
        "label": "StackExchange 200 pairs (9 communities)",
    },
]


def _check_goldens() -> bool:
    """Verify golden files exist."""
    all_ok = True
    for g in GOLDEN_FILES:
        exists = g["path"].exists()
        if not exists:
            print(f"  ⚠  Missing: {g['path']}")
            all_ok = False
        else:
            size = g["path"].stat().st_size
            print(f"  ✓ {g['label']}: {g['path'].name} ({size:,} bytes)")
    return all_ok


def _build_comparison_table(results: List[Dict]) -> str:
    """Build a Markdown comparison table from scenario results."""
    lines = [
        "### M2 — Pure Data Migration Delta",
        "",
        "| Scenario | Golden | Correctness | Faithfulness | AnswerRelevancy | ContextualPrecision | ContextualRecall |",
        "|----------|--------|------------:|-------------:|----------------:|--------------------:|-----------------:|",
    ]

    for r in results:
        lines.append(
            f"| {r['scenario_label']} | {r['golden_label']} "
            f"| {r.get('correctness', 'N/A')} "
            f"| {r.get('faithfulness', 'N/A')} "
            f"| {r.get('answer_relevancy', 'N/A')} "
            f"| {r.get('contextual_precision', 'N/A')} "
            f"| {r.get('contextual_recall', 'N/A')} |"
        )

    lines.extend([
        "",
        "**Notes:**",
        "- Scenarios 3-4 unavailable — alternate chunking namespaces not created in M1.",
        "- Golden QA pairs excluded from vector index (measures generalization).",
        "- Judge: `meta-llama/llama-4-scout-17b-16e-instruct` via Groq.",
    ])

    return "\n".join(lines)


def _load_aggregate(csv_path: str) -> Optional[Dict]:
    """Load JSON aggregate for a CSV path."""
    json_path = csv_path.replace(".csv", "_aggregate.json")
    if not os.path.exists(json_path):
        return None
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _format_metric(agg: Optional[Dict], metric: str) -> str:
    """Format a metric value from aggregate dict."""
    if agg is None:
        return "ERR"
    stats = agg.get(metric, {})
    mean_val = stats.get("mean")
    if mean_val is None:
        return "N/A"
    return f"{mean_val:.2%}"


def main():
    parser = argparse.ArgumentParser(
        description="Run scenario matrix against golden QA datasets"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="RAG API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="X-API-KEY for authenticated endpoints",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running",
    )
    parser.add_argument(
        "--scenarios",
        type=int,
        nargs="+",
        default=None,
        help="Scenario IDs to run (default: all available)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Seconds between individual eval questions (default: 3.0)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=10,
        help="Number of search results per question (default: 10)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit questions per golden (for testing)",
    )
    args = parser.parse_args()

    # ── Validate environment ──
    print("=" * 60)
    print("  M2 — Scenario Matrix Orchestrator")
    print(f"  Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    if not os.getenv("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY environment variable is required")
        sys.exit(1)

    # Auto-detect API key from .env for local runs
    api_key = args.api_key or os.getenv("APP_API_KEY")
    if not api_key:
        print("WARNING: No API key provided. Use --api-key or set APP_API_KEY in .env")

    # ── Check goldens ──
    print("\nVerifying golden files...")
    if not _check_goldens():
        print("\nERROR: Missing golden files. Run build_golden_qa.py first.")
        sys.exit(1)

    # ── Select scenarios ──
    available = [s for s in SCENARIOS if s["available"]]
    if args.scenarios:
        selected = [s for s in available if s["id"] in args.scenarios]
    else:
        selected = available

    unavailable = [s for s in SCENARIOS if not s["available"]]
    if unavailable:
        print(f"\nUnavailable scenarios (skipped):")
        for s in unavailable:
            print(f"  ⏭  {s['label']}")
            print(f"      Reason: {s['note']}")

    if not selected:
        print("\nERROR: No available scenarios to run.")
        sys.exit(1)

    print(f"\nScenarios to execute:")
    for s in selected:
        print(f"  [{s['id']}] {s['label']} ({s['search_method']})")

    # ── Execute scenarios ──
    all_results: List[Dict] = []
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    total_start = time.time()

    for scenario in selected:
        for golden in GOLDEN_FILES:
            label = f"{scenario['label']} × {golden['label']}"
            print(f"\n{'─' * 60}")
            print(f"  Running: {label}")
            print(f"{'─' * 60}")

            cmd = [
                sys.executable,
                str(RUN_EVAL),
                "--api-url", args.api_url,
                "--golden-json", str(golden["path"]),
                "--scenario-name", scenario["name"],
                "--search-method", scenario["search_method"],
                "--k", str(args.k),
                "--delay", str(args.delay),
            ]

            if api_key:
                cmd.extend(["--api-key", api_key])
            if args.limit:
                cmd.extend(["--limit", str(args.limit)])

            if args.dry_run:
                print(f"  [DRY-RUN] Would execute:")
                print(f"    {' '.join(cmd)}")
                continue

            print(f"  Command: {' '.join(cmd)}")
            print()

            start = time.time()
            result = subprocess.run(cmd, capture_output=False)
            elapsed = time.time() - start

            if result.returncode != 0:
                print(f"\n  ⚠  {label} completed with errors (exit code {result.returncode})")
            else:
                print(f"\n  ✓ {label} completed in {elapsed:.1f}s")

            # Find the latest CSV for this scenario+golden
            csv_pattern = f"{scenario['name']}_{golden['name']}_*.csv"
            csv_dir = Path(RAW_RESULTS_DIR)
            csv_files = sorted(csv_dir.glob(csv_pattern), key=os.path.getmtime)
            if csv_files:
                latest_csv = csv_files[-1]
                agg = _load_aggregate(str(latest_csv))
                if agg:
                    all_results.append({
                        "scenario": scenario["name"],
                        "scenario_label": scenario["label"],
                        "golden": golden["name"],
                        "golden_label": golden["label"],
                        "csv": str(latest_csv),
                        "correctness": _format_metric(agg, "correctness"),
                        "faithfulness": _format_metric(agg, "faithfulness"),
                        "answer_relevancy": _format_metric(agg, "answer_relevancy"),
                        "contextual_precision": _format_metric(agg, "contextual_precision"),
                        "contextual_recall": _format_metric(agg, "contextual_recall"),
                    })

    # ── Generate comparison ──
    if not args.dry_run and all_results:
        # Write comparison CSV
        comparison_csv = RAW_RESULTS_DIR / f"comparison_{timestamp}.csv"
        import csv as _csv

        with open(comparison_csv, "w", newline="", encoding="utf-8") as f:
            writer = _csv.DictWriter(f, fieldnames=[
                "scenario", "scenario_label", "golden", "golden_label",
                "correctness", "faithfulness", "answer_relevancy",
                "contextual_precision", "contextual_recall", "csv",
            ])
            writer.writeheader()
            writer.writerows(all_results)

        # Write comparison Markdown
        comparison_md = RAW_RESULTS_DIR / f"comparison_{timestamp}.md"
        md_content = _build_comparison_table(all_results)
        with open(comparison_md, "w", encoding="utf-8") as f:
            f.write(md_content)

        print(f"\n{'=' * 60}")
        print("  Scenario Matrix Complete")
        print(f"{'=' * 60}")
        print(f"  Total time: {time.time() - total_start:.1f}s")
        print(f"  Results CSV: {comparison_csv}")
        print(f"  Results MD:  {comparison_md}")
        print(f"\n  Table preview:")
        print(md_content)

    total_elapsed = time.time() - total_start
    print(f"\nTotal elapsed: {total_elapsed:.1f}s")


if __name__ == "__main__":
    main()
