#!/usr/bin/env python3
"""
Golden QA Builder — stratified sampling from MongoDB qa_pairs.

Samples 200 QA pairs (50 Expert + 150 Operational) from the real StackExchange
corpus in MongoDB, writes DeepEval-compatible golden JSON files, and optionally
excludes the sampled ticketIds from the Pinecone vector index + rebuilds BM25.

Usage:
    # Dry-run: show counts without writing
    python scripts/build_golden_qa.py --dry-run

    # Full run: sample, write goldens, exclude from index
    python scripts/build_golden_qa.py

    # Skip index exclusion (only write goldens)
    python scripts/build_golden_qa.py --skip-index-exclusion

Requires:
    - MONGODB_URI, MONGODB_DB_NAME environment variables
    - MongoDB qa_pairs collection populated (run ingest_stackexchange_dataset.py first)
    - PINECONE_API_KEY, PINECONE_INDEX_NAME env vars (if --skip-index-exclusion not set)
"""

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

sys.path.append(str(Path(__file__).parent.parent))

from langchain_text_splitters import RecursiveCharacterTextSplitter
from motor.motor_asyncio import AsyncIOMotorClient

# ── Paths ──

API_DIR = Path(__file__).parent.parent
GOLDENS_DIR = API_DIR.parent / "evaluation_notebooks" / "goldens"
BM25_SCRIPT = API_DIR / "scripts" / "build_bm25_index.py"

# ── Stratified quotas ──

EXPERT_QUOTAS: Dict[str, int] = {
    "dba": 10,
    "networkengineering": 10,
    "serverfault": 15,
    "security": 10,
    "devops": 5,
}

OPERATIONAL_QUOTAS: Dict[str, int] = {
    "superuser": 50,
    "askubuntu": 50,
    "apple": 25,
    "android": 25,
}

# Fallback communities when quotas can't be met
EXPERT_FALLBACK = "serverfault"
OPERATIONAL_FALLBACK = "superuser"

# Chunking config (must match ingest_stackexchange_dataset.py)
SE_CHUNK_SIZE = 1000
SE_CHUNK_OVERLAP = 100
PINECONE_NAMESPACE = "kb-se-all"
PINECONE_DELETE_BATCH_SIZE = 500

RANDOM_SEED = 42

# ── Sampling ──


async def count_by_community(db, communities: List[str]) -> Dict[str, int]:
    """Count available pairs per community in MongoDB."""
    counts: Dict[str, int] = {}
    for comm in communities:
        c = await db.qa_pairs.count_documents({"community": comm})
        counts[comm] = c
    return counts


async def sample_community(
    db,
    community: str,
    quota: int,
    seed: int,
    excluded_ids: Set[str],
) -> List[dict]:
    """Sample `quota` random pairs from a community, excluding ticketIds."""
    cursor = db.qa_pairs.find(
        {"community": community},
        {
            "ticketId": 1,
            "title_body": 1,
            "upvoted_answer": 1,
            "community": 1,
        },
    )
    docs = []
    async for doc in cursor:
        tid = doc.get("ticketId", "")
        if tid and tid not in excluded_ids:
            docs.append(doc)

    if len(docs) == 0:
        return []

    # Deterministic shuffle
    rng = random.Random(seed + hash(community) % 2**31)
    rng.shuffle(docs)

    selected = docs[:quota]
    return selected


def build_golden_item(doc: dict) -> dict:
    """Transform a MongoDB doc into DeepEval golden format."""
    ticket_id = doc.get("ticketId", "")
    return {
        "question": doc.get("title_body", ""),
        "answer": doc.get("upvoted_answer", ""),
        "ticketId": ticket_id,
        "kb": ticket_id,
    }


# ── Index exclusion helpers ──


def compute_chunk_ids(title_body: str, ticket_id: str) -> List[str]:
    """Compute Pinecone chunk IDs for a ticket, matching ingest logic.

    Reuses the same RecursiveCharacterTextSplitter config as ingestion.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=SE_CHUNK_SIZE,
        chunk_overlap=SE_CHUNK_OVERLAP,
        add_start_index=True,
    )
    if len(title_body) > SE_CHUNK_SIZE:
        chunks = splitter.split_text(title_body)
    else:
        chunks = [title_body]

    return [f"{ticket_id}_chunk-{idx}" for idx in range(len(chunks))]


def delete_from_pinecone(chunk_ids: List[str], dry_run: bool = False) -> int:
    """Delete vectors from Pinecone by chunk ID. Returns count deleted."""
    if dry_run:
        return len(chunk_ids)

    from pinecone import Pinecone

    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    if not api_key or not index_name:
        print("  ⚠  PINECONE_API_KEY or PINECONE_INDEX_NAME not set, skipping deletion")
        return 0

    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)

    total = 0
    for i in range(0, len(chunk_ids), PINECONE_DELETE_BATCH_SIZE):
        batch = chunk_ids[i : i + PINECONE_DELETE_BATCH_SIZE]
        index.delete(ids=batch, namespace=PINECONE_NAMESPACE)
        total += len(batch)
        print(f"    Deleted {total}/{len(chunk_ids)} vectors from Pinecone", end="\r")

    print()
    return total


async def rebuild_bm25(exclude_ids: Set[str], dry_run: bool = False) -> bool:
    """Rebuild BM25 index excluding golden ticketIds."""
    if dry_run:
        print(f"  [DRY-RUN] Would rebuild BM25 index excluding {len(exclude_ids)} IDs")
        return True

    # Write excluded IDs to temp file for build_bm25_index.py
    tmp_path = API_DIR / "scripts" / ".golden_excluded_ids.tmp"
    try:
        with open(tmp_path, "w") as f:
            for tid in sorted(exclude_ids):
                f.write(tid + "\n")

        # Import and run BM25 builder with exclude filter
        sys.path.insert(0, str(API_DIR))
        from scripts.build_bm25_index import build_bm25_index

        # Monkey-patch: add exclude filter to the builder
        original_process = None
        try:
            from scripts import build_bm25_index as bm25_mod

            original_process = bm25_mod._process_batch

            def _filtered_process(batch, tickets_for_bm25):
                filtered = [doc for doc in batch if doc.get("ticketId", "") not in exclude_ids]
                original_process(filtered, tickets_for_bm25)

            bm25_mod._process_batch = _filtered_process
            await build_bm25_index()
            bm25_mod._process_batch = original_process
        finally:
            if original_process:
                from scripts import build_bm25_index as bm25_mod

                bm25_mod._process_batch = original_process
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return True


# ── Main ──


async def main_async(args):
    """Async main pipeline."""
    random.seed(RANDOM_SEED)
    all_ids_sampled: Set[str] = set()

    # ── 1. Connect to MongoDB ──
    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB_NAME")
    if not uri or not db_name:
        print("ERROR: MONGODB_URI and MONGODB_DB_NAME must be set.")
        sys.exit(1)

    print(f"Connecting to MongoDB: {db_name}")
    client = AsyncIOMotorClient(uri)
    db = client[db_name]
    total = await db.qa_pairs.count_documents({})
    print(f"Total qa_pairs: {total:,}")

    if total == 0:
        print("ERROR: qa_pairs collection is empty. Run ingest_stackexchange_dataset.py first.")
        sys.exit(1)

    # ── 2. Show available pairs per target community ──
    all_target_communities = list(set(list(EXPERT_QUOTAS.keys()) + list(OPERATIONAL_QUOTAS.keys())))
    available = await count_by_community(db, all_target_communities)
    print(f"\n{'='*60}")
    print("  Available pairs per target community")
    print(f"{'='*60}")
    for comm in sorted(all_target_communities):
        avail = available.get(comm, 0)
        quota = EXPERT_QUOTAS.get(comm) or OPERATIONAL_QUOTAS.get(comm)
        flag = "OK" if avail >= quota else "SHORT"
        print(f"  {comm:<25} {avail:>6,} available / {quota:>3} needed  [{flag}]")

    # ── 3. Sample Expert pairs ──
    print(f"\n{'='*60}")
    print("  Sampling Expert (50 pairs)")
    print(f"{'='*60}")
    expert_pairs: List[dict] = []
    for community, quota in sorted(EXPERT_QUOTAS.items()):
        avail = available.get(community, 0)
        actual_quota = min(quota, avail)
        if actual_quota < quota:
            deficit = quota - actual_quota
            print(f"  ⚠  {community}: only {actual_quota}/{quota} available. Deficit={deficit}")
            if deficit > 0:
                print(f"      Will compensate from {EXPERT_FALLBACK}")
        else:
            print(f"  {community}: sampling {actual_quota}")
        pairs = await sample_community(db, community, actual_quota, RANDOM_SEED, all_ids_sampled)
        for p in pairs:
            tid = p.get("ticketId", "")
            all_ids_sampled.add(tid)
            expert_pairs.append(build_golden_item(p))

    # Compensate deficits
    for community, quota in sorted(EXPERT_QUOTAS.items()):
        avail = available.get(community, 0)
        if avail < quota:
            deficit = quota - avail
            print(f"  Compensating {deficit} from {EXPERT_FALLBACK}...")
            extra = await sample_community(
                db, EXPERT_FALLBACK, deficit, RANDOM_SEED + 1, all_ids_sampled
            )
            for p in extra:
                tid = p.get("ticketId", "")
                all_ids_sampled.add(tid)
                expert_pairs.append(build_golden_item(p))

    print(f"  → Total expert: {len(expert_pairs)}")

    # ── 4. Sample Operational pairs ──
    print(f"\n{'='*60}")
    print("  Sampling Operational (150 pairs)")
    print(f"{'='*60}")
    operational_pairs: List[dict] = []
    for community, quota in sorted(OPERATIONAL_QUOTAS.items()):
        avail = available.get(community, 0)
        actual_quota = min(quota, avail)
        if actual_quota < quota:
            deficit = quota - actual_quota
            print(f"  ⚠  {community}: only {actual_quota}/{quota} available. Deficit={deficit}")
        print(f"  {community}: sampling {actual_quota}")
        pairs = await sample_community(db, community, actual_quota, RANDOM_SEED, all_ids_sampled)
        for p in pairs:
            tid = p.get("ticketId", "")
            all_ids_sampled.add(tid)
            operational_pairs.append(build_golden_item(p))

    # Compensate deficits
    for community, quota in sorted(OPERATIONAL_QUOTAS.items()):
        avail = available.get(community, 0)
        if avail < quota:
            deficit = quota - avail
            print(f"  Compensating {deficit} from {OPERATIONAL_FALLBACK}...")
            extra = await sample_community(
                db, OPERATIONAL_FALLBACK, deficit, RANDOM_SEED + 2, all_ids_sampled
            )
            for p in extra:
                tid = p.get("ticketId", "")
                all_ids_sampled.add(tid)
                operational_pairs.append(build_golden_item(p))

    print(f"  → Total operational: {len(operational_pairs)}")

    # ── 5. Validate ──
    all_pairs = expert_pairs + operational_pairs
    all_tids = [p["ticketId"] for p in all_pairs]
    dupes = len(all_tids) - len(set(all_tids))

    print(f"\n{'='*60}")
    print(f"  Validation")
    print(f"{'='*60}")
    print(f"  Expert:      {len(expert_pairs)}")
    print(f"  Operational: {len(operational_pairs)}")
    print(f"  Total:       {len(all_pairs)}")
    print(f"  Duplicates:  {dupes}")
    print(f"  All have question: {all(p.get('question') for p in all_pairs)}")
    print(f"  All have answer:   {all(p.get('answer') for p in all_pairs)}")
    print(f"  All have ticketId: {all(p.get('ticketId') for p in all_pairs)}")

    if len(all_pairs) != 200:
        print(f"\n  ⚠  WARNING: Expected 200 pairs, got {len(all_pairs)}")
    if dupes > 0:
        print(f"\n  ⚠  WARNING: Found {dupes} duplicate ticketIds!")
        sys.exit(1)

    # ── 6. Write golden JSONs (with .bak backup) ──
    if args.dry_run:
        print(f"\n  [DRY-RUN] Would write golden JSONs to {GOLDENS_DIR}")
        print(f"  [DRY-RUN] Would backup existing files with .bak")
    else:
        GOLDENS_DIR.mkdir(parents=True, exist_ok=True)

        expert_path = GOLDENS_DIR / "golden_expert.json"
        operational_path = GOLDENS_DIR / "golden_operational.json"

        # Backup existing files
        for path in [expert_path, operational_path]:
            if path.exists():
                bak_path = path.with_suffix(".json.bak")
                path.rename(bak_path)
                print(f"\n  Backed up {path.name} → {bak_path.name}")

        # Write new goldens
        with open(expert_path, "w", encoding="utf-8") as f:
            json.dump(expert_pairs, f, ensure_ascii=False, indent=2)
        print(f"  Written: {expert_path} ({len(expert_pairs)} pairs)")

        with open(operational_path, "w", encoding="utf-8") as f:
            json.dump(operational_pairs, f, ensure_ascii=False, indent=2)
        print(f"  Written: {operational_path} ({len(operational_pairs)} pairs)")

    # ── 7. Exclude golden IDs from index ──
    if not args.skip_index_exclusion:
        print(f"\n{'='*60}")
        print("  Excluding golden IDs from Pinecone index")
        print(f"{'='*60}")

        # Compute chunk IDs for each golden pair
        all_chunk_ids: List[str] = []
        for p in all_pairs:
            tid = p["ticketId"]
            title_body = p["question"]
            chunk_ids = compute_chunk_ids(title_body, tid)
            all_chunk_ids.extend(chunk_ids)

        print(f"  Found {len(all_chunk_ids)} chunk IDs to delete for {len(all_pairs)} golden pairs")

        deleted = delete_from_pinecone(all_chunk_ids, dry_run=args.dry_run)
        if not args.dry_run:
            print(f"  ✓ Deleted {deleted} vectors from Pinecone namespace '{PINECONE_NAMESPACE}'")
        else:
            print(f"  [DRY-RUN] Would delete {deleted} vectors from Pinecone")

        # ── 8. Rebuild BM25 ──
        print(f"\n  Rebuilding BM25 index (excluding {len(all_ids_sampled)} golden IDs)...")
        success = await rebuild_bm25(all_ids_sampled, dry_run=args.dry_run)
        if success and not args.dry_run:
            print("  ✓ BM25 index rebuilt successfully")
    else:
        print("\n  Skipping index exclusion (--skip-index-exclusion)")

    # ── 9. Summary ──
    print(f"\n{'='*60}")
    print("  Summary")
    print(f"{'='*60}")
    print(f"  Expert pairs:      {len(expert_pairs)}")
    print(f"  Operational pairs: {len(operational_pairs)}")
    print(f"  Total golden:      {len(all_pairs)}")
    print(f"  Unique ticketIds:  {len(set(all_tids))}")
    print(f"  Excluded from idx: {'No (--skip-index-exclusion)' if args.skip_index_exclusion else f'{len(all_chunk_ids)} chunk IDs'}")

    client.close()


def main():
    parser = argparse.ArgumentParser(
        description="Build 200-pair stratified golden QA from MongoDB qa_pairs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show counts without writing files or modifying indexes",
    )
    parser.add_argument(
        "--skip-index-exclusion",
        action="store_true",
        help="Skip Pinecone deletion and BM25 rebuild",
    )
    args = parser.parse_args()

    asyncio.run(main_async(args))


if __name__ == "__main__":
    import asyncio
    main()
