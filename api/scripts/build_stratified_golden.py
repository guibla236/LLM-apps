#!/usr/bin/env python3
"""
Build a stratified golden set for the model-routing hypothesis (M6-OptC).

Balances queries by expected-answer length (the EDA log-normal percentiles):
  - short  (<= 467 chars, P50)
  - medium  (467 < len <= 887, P50-P75)
  - long  (> 887 chars, P75)

Reuses the 50 queries already evaluated in M6 (k=5) and samples the missing
queries to complete 25/25/25.

Outputs (in evaluation_notebooks/goldens/):
  - golden_se_75_estratificado.json  : full 75-set, each entry tagged with
                                       "bucket" and "eval_state" (done/pending)
  - golden_se_25_new.json            : only the 25 pending queries (for run_eval)

Usage:
  python api/scripts/build_stratified_golden.py
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent  # Tarea_2
GOLDEN_200 = ROOT / "evaluation_notebooks" / "goldens" / "golden_se_200.json"
GOLDEN_50 = ROOT / "evaluation_notebooks" / "goldens" / "golden_se_50_m4.json"
OUT_75 = ROOT / "evaluation_notebooks" / "goldens" / "golden_se_75_estratificado.json"
OUT_25 = ROOT / "evaluation_notebooks" / "goldens" / "golden_se_25_new.json"

P50, P75 = 467, 887  # EDA log-normal percentiles (chars, expected answer)

SEED = 42
TARGET_PER_BUCKET = 25


def bucket_for(answer_len: int) -> str:
    if answer_len <= P50:
        return "corto"
    if answer_len <= P75:
        return "medio"
    return "largo"


def main() -> None:
    rng = random.Random(SEED)

    golden200 = json.loads(GOLDEN_200.read_text(encoding="utf-8"))
    golden50 = json.loads(GOLDEN_50.read_text(encoding="utf-8"))
    used_ids = {g["ticketId"] for g in golden50}

    # Tag the 50 reused queries with their bucket
    done = []
    for g in golden50:
        g["bucket"] = bucket_for(len(g["answer"]))
        g["eval_state"] = "done"
        done.append(g)

    # Pool of unused queries, bucketed
    pools = {"corto": [], "medio": [], "largo": []}
    for g in golden200:
        if g["ticketId"] in used_ids:
            continue
        pools[bucket_for(len(g["answer"]))].append(g)

    counts = {"corto": 0, "medio": 0, "largo": 0}
    for g in done:
        counts[g["bucket"]] += 1

    print("=== Reusadas (ya evaluadas k=5) ===")
    for b in ("corto", "medio", "largo"):
        print(f"  {b:6s}: {counts[b]}")

    print("\n=== Pool disponible (no usadas) ===")
    for b in ("corto", "medio", "largo"):
        print(f"  {b:6s}: {len(pools[b])}")

    # Sample the missing queries to reach 25 per bucket
    pending = []
    for b in ("corto", "medio", "largo"):
        needed = TARGET_PER_BUCKET - counts[b]
        if needed <= 0:
            continue
        if needed > len(pools[b]):
            raise SystemExit(f"ERROR: bucket '{b}' necesita {needed} pero solo hay {len(pools[b])}")
        sample = rng.sample(pools[b], needed)
        for g in sample:
            g["bucket"] = b
            g["eval_state"] = "pending"
            pending.append(g)

    full = done + pending
    full.sort(key=lambda g: g["ticketId"])

    OUT_75.write_text(
        json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    OUT_25.write_text(
        json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n=== Golden estratificado final ===")
    final_counts = {"corto": 0, "medio": 0, "largo": 0}
    for g in full:
        final_counts[g["bucket"]] += 1
    for b in ("corto", "medio", "largo"):
        print(f"  {b:6s}: {final_counts[b]}  (pendientes: {sum(1 for g in pending if g['bucket']==b)})")

    print(f"\nTotal: {len(full)} | Pendientes de evaluar: {len(pending)}")
    print(f"Escrito: {OUT_75.name}")
    print(f"         {OUT_25.name}")


if __name__ == "__main__":
    main()
