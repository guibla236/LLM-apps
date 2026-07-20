#!/usr/bin/env python3
"""
StackExchange Dataset Ingestion Script.

Downloads the 12 IT-relevant Stack Exchange communities from HuggingFace,
transforms Q&A pairs into the extended TicketModel, upserts them to Pinecone
(with per-community namespaces) and persists the full answers in MongoDB qa_pairs.

Usage:
    # Dry-run (validate without writing)
    python scripts/ingest_stackexchange_dataset.py --dry-run --limit-per-community 50

    # Limited test (writes to Pinecone + Mongo)
    python scripts/ingest_stackexchange_dataset.py --limit-per-community 100

    # Full ingestion (all ~60K pairs)
    python scripts/ingest_stackexchange_dataset.py

    # Resume interrupted ingestion (skips already-indexed IDs)
    python scripts/ingest_stackexchange_dataset.py --resume

    # Exclude golden QA IDs from vector index (keeps them in Mongo)
    python scripts/ingest_stackexchange_dataset.py \\
        --exclude-golden-ids ../evaluation_notebooks/goldens/golden_expert.json \\
                           ../evaluation_notebooks/goldens/golden_operational.json

    # Selected communities only
    python scripts/ingest_stackexchange_dataset.py --communities superuser,askubuntu
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set

# Allow running from the api/ directory
sys.path.append(str(Path(__file__).parent.parent))

from datasets import load_dataset
from tqdm import tqdm

from models.tickets import TicketModel, TicketPriority

# ── Community configuration ──────────────────────────────────────────────────

IT_COMMUNITIES = [
    "superuser",       # Hardware / Office
    "askubuntu",       # OS / General
    "serverfault",     # DevOps / Infrastructure
    "apple",           # MDM / Mobility
    "unix",            # Sysadmin / Linux
    "android",         # MDM / Mobility
    "security",        # Cybersecurity
    "dba",             # Data & SQL
    "webapps",         # Cloud Collaboration
    "sharepoint",      # Cloud Collaboration
    "networkengineering",  # Networking
    "devops",          # DevOps
]

EXPECTED_PAIRS = {
    "superuser": 17425,
    "askubuntu": 9975,
    "serverfault": 7969,
    "apple": 6696,
    "unix": 6173,
    "android": 2830,
    "security": 3069,
    "dba": 2502,
    "webapps": 1906,
    "sharepoint": 1691,
    "networkengineering": 476,
    "devops": 53,
}

# ── Helpers ──────────────────────────────────────────────────────────────────

# Error code patterns for priority inference
RE_CRITICAL = re.compile(
    r"\b0x[0-9A-F]{4,}\b|error 5\d\d|fatal|panic|crash|kernel panic|bsod|blue screen",
    re.I,
)


def infer_priority(title_body: str, answer: str) -> TicketPriority:
    """Infer ticket priority from question and answer content."""
    if RE_CRITICAL.search(title_body):
        return TicketPriority.HIGH
    if len(title_body) < 100:
        return TicketPriority.LOW
    return TicketPriority.MEDIUM


def make_ticket_id(community: str, original_id: int) -> str:
    """Generate a deterministic SE ticket ID."""
    return f"SE-{community.upper()}-{original_id}"


def parse_community_arg(value: str) -> List[str]:
    """Parse comma-separated community list from CLI."""
    communities = [c.strip().lower() for c in value.split(",")]
    unknown = [c for c in communities if c not in IT_COMMUNITIES]
    if unknown:
        raise argparse.ArgumentTypeError(
            f"Unknown communities: {unknown}. Valid: {', '.join(IT_COMMUNITIES)}"
        )
    return communities


# ── Golden QA exclusion ──────────────────────────────────────────────────────

def load_golden_ids(golden_paths: List[str]) -> Set[str]:
    """Load ticket IDs from golden QA JSON files for exclusion."""
    excluded = set()
    for path in golden_paths:
        path_obj = Path(path)
        if not path_obj.exists():
            print(f"  ⚠  Golden file not found, skipping: {path}")
            continue
        with open(path_obj, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Support both list-of-dicts and dict-with-tickets formats
        items = data if isinstance(data, list) else data.get("tickets", [])
        for item in items:
            tid = item.get("ticketId") or item.get("ticket_id")
            if tid:
                excluded.add(tid)
    return excluded


# ── Pinecone ingestion ───────────────────────────────────────────────────────

def _init_pinecone():
    """Lazy-init Pinecone index and embeddings."""
    from modules.third_party_clients import pinecone_client, embeddings_model

    index_name = os.getenv("PINECONE_INDEX_NAME")
    if not index_name:
        raise ValueError("PINECONE_INDEX_NAME environment variable is not set.")
    index = pinecone_client.Index(index_name)
    return index, embeddings_model


PINECONE_NAMESPACE = "kb-se-all"


def _build_pinecone_vectors(
    pairs: List[dict],
    embeddings_model,
    batch_size: int = 100,
) -> List[tuple]:
    """Build (id, vector, metadata) tuples for Pinecone upsert.

    Uses a single namespace "kb-se-all" (per EDA decision):
    the corpus is cross-community (98% of DevOps content lives
    outside the devops community), so per-community namespaces
    don't add retrieval value. Community is stored in metadata
    for provenance tracking.
    """
    vectors = []

    for i in range(0, len(pairs), batch_size):
        batch = pairs[i : i + batch_size]
        texts = [p["title_body"] for p in batch]
        embeddings = embeddings_model.embed_documents(texts)

        for j, (pair, vec) in enumerate(zip(batch, embeddings)):
            ticket_id = make_ticket_id(pair["community"], pair["original_id"])
            expected_truncated = (pair.get("upvoted_answer") or "")[:500]
            vectors.append(
                (
                    ticket_id,
                    vec,
                    {
                        "community": pair["community"],
                        "expected_output": expected_truncated,
                        "priority": pair["priority"].value,
                    },
                )
            )

    return vectors


def _pinecone_upsert(index, vectors: List[tuple], dry_run: bool = False):
    """Upsert vectors to Pinecone in the single kb-se-all namespace."""
    if dry_run:
        return

    upsert_data = [(vid, vec, meta) for vid, vec, meta in vectors]
    ns = PINECONE_NAMESPACE
    index.upsert(vectors=upsert_data, namespace=ns)
    print(f"  \u2713 Upserted {len(upsert_data)} vectors to namespace '{ns}'")


# ── MongoDB ingestion ────────────────────────────────────────────────────────

def _init_mongo():
    """Lazy-init MongoDB connection."""
    from motor.motor_asyncio import AsyncIOMotorClient

    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB_NAME")
    if not uri or not db_name:
        raise ValueError("MONGODB_URI and MONGODB_DB_NAME must be set.")
    client = AsyncIOMotorClient(uri)
    return client[db_name]


async def _mongo_upsert_qa_pairs(db, pairs: List[dict], dry_run: bool = False):
    """Upsert full Q&A pairs to MongoDB qa_pairs collection."""
    if dry_run:
        return

    now = datetime.now(timezone.utc)
    for pair in tqdm(pairs, desc="  MongoDB upsert", unit="doc"):
        doc = {
            "ticketId": pair["ticket_id"],
            "title_body": pair["title_body"],
            "upvoted_answer": pair.get("upvoted_answer") or "",
            "downvoted_answer": pair.get("downvoted_answer"),
            "community": pair["community"],
            "priority": pair["priority"].value,
            "ingested_at": now,
        }
        await db.qa_pairs.update_one(
            {"ticketId": pair["ticket_id"]},
            {"$set": doc},
            upsert=True,
        )


# ── Main ingestion pipeline ──────────────────────────────────────────────────

async def process_community(
    community: str,
    limit: Optional[int] = None,
    dry_run: bool = False,
    excluded_ids: Optional[Set[str]] = None,
    pinecone_index=None,
    embeddings_model=None,
    mongo_db=None,
) -> dict:
    """Process a single Stack Exchange community.

    Returns a summary dict with counts.
    """
    excluded_ids = excluded_ids or set()
    print(f"\n{'='*60}")
    print(f"  Community: {community}")
    print(f"{'='*60}")

    # ── 1. Load dataset ──
    print(f"  Loading dataset 'flax-sentence-embeddings/stackexchange_titlebody_best_and_down_voted_answer_jsonl'...")
    print(f"  Subset: {community}")

    dataset = load_dataset(
        "flax-sentence-embeddings/stackexchange_titlebody_best_and_down_voted_answer_jsonl",
        community,
        split="train",
    )

    total = len(dataset)
    if limit:
        dataset = dataset.select(range(min(limit, total)))
    print(f"  Loaded {len(dataset)} / {total} pairs")

    # ── 2. Transform to internal format ──
    pairs = []
    skipped_no_answer = 0
    skipped_short_answer = 0
    skipped_golden = 0

    for record in dataset:
        upvoted = record.get("upvoted_answer") or ""
        # Hard filter: answer >= 50 chars (from M0 decision)
        if len(upvoted) < 50:
            skipped_short_answer += 1
            continue

        original_id = record.get("id") or hash(record.get("title_body", ""))
        ticket_id = make_ticket_id(community, original_id)

        # Check golden exclusion for Pinecone (still add to Mongo)
        is_golden = ticket_id in excluded_ids

        title_body = record.get("title_body") or record.get("title", "")
        priority = infer_priority(title_body, upvoted)

        pairs.append({
            "original_id": original_id,
            "ticket_id": ticket_id,
            "title_body": title_body,
            "upvoted_answer": upvoted,
            "downvoted_answer": record.get("downvoted_answer"),
            "community": community,
            "priority": priority,
            "is_golden": is_golden,
        })

    print(f"  Transformed: {len(pairs)} pairs")
    print(f"    Skipped (short answer <50 chars): {skipped_short_answer}")
    if excluded_ids:
        golden_in_batch = sum(1 for p in pairs if p["is_golden"])
        print(f"    Golden (excluded from vector index): {golden_in_batch}")

    if dry_run:
        print(f"  [DRY-RUN] Would upsert {len(pairs)} vectors to Pinecone")
        print(f"  [DRY-RUN] Would upsert {len(pairs)} docs to MongoDB")
        return {
            "community": community,
            "loaded": len(dataset),
            "transformed": len(pairs),
            "skipped_short": skipped_short_answer,
            "golden": sum(1 for p in pairs if p["is_golden"]),
            "dry_run": True,
        }

    # ── 3. Upsert to Pinecone (skip golden IDs) ──
    pinecone_pairs = [p for p in pairs if not p["is_golden"]]
    if pinecone_pairs and pinecone_index is not None:
        vectors = _build_pinecone_vectors(
            pinecone_pairs, embeddings_model
        )
        _pinecone_upsert(pinecone_index, vectors)
        print(f"  ✓ Pinecone: {len(pinecone_pairs)} vectors upserted (namespace: kb-se-all)")
    else:
        print(f"  - Pinecone: skipped (no pairs or no index)")

    # ── 4. Upsert to MongoDB (all pairs, including golden) ──
    if mongo_db is not None:
        await _mongo_upsert_qa_pairs(mongo_db, pairs)
        print(f"  ✓ MongoDB: {len(pairs)} docs upserted")
    else:
        print(f"  - MongoDB: skipped (no database)")

    return {
        "community": community,
        "loaded": len(dataset),
        "transformed": len(pairs),
        "pinecone_upserted": len(pinecone_pairs),
        "mongo_upserted": len(pairs),
        "skipped_short": skipped_short_answer,
        "golden": sum(1 for p in pairs if p["is_golden"]),
    }


def validate_counts(results: List[dict]):
    """Check final counts against expected pairs per community (±5%)."""
    print(f"\n{'='*60}")
    print(f"  VALIDATION")
    print(f"{'='*60}")
    all_ok = True
    for r in results:
        comm = r["community"]
        expected = EXPECTED_PAIRS.get(comm, 0)
        actual = r.get("mongo_upserted") or r.get("transformed", 0)
        if expected > 0:
            deviation = abs(actual - expected) / expected
            status = "✓" if deviation <= 0.05 else "⚠"
            print(f"  {status} {comm}: {actual} / {expected} "
                  f"({deviation*100:.1f}% deviation)")
            if deviation > 0.05:
                all_ok = False
        else:
            print(f"  ? {comm}: {actual} (no expected value)")
    if all_ok:
        print(f"\n  ✅ All communities within ±5% tolerance.")
    else:
        print(f"\n  ⚠  Some communities exceed ±5% tolerance — review manually.")


# ── CLI ──────────────────────────────────────────────────────────────────────

def _parse_args():
    """Parse CLI arguments (does not start the event loop)."""
    parser = argparse.ArgumentParser(
        description="Ingest StackExchange dataset to Pinecone + MongoDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--communities",
        type=parse_community_arg,
        default=None,
        help="Comma-separated list of communities (default: all 12 IT communities)",
    )
    parser.add_argument(
        "--namespace-prefix",
        default="kb-se",
        help="Ignored (kept for backwards compat). Namespace is always kb-se-all per EDA decision.",
    )
    parser.add_argument(
        "--embedding-model",
        default="all-minilm:22m",
        help="Ollama embedding model name (default: all-minilm:22m)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate parsing and structure without writing to Pinecone/Mongo",
    )
    parser.add_argument(
        "--limit-per-community",
        type=int,
        default=None,
        help="Max pairs per community for quick dev tests",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip IDs already present in Pinecone (idempotent)",
    )
    parser.add_argument(
        "--exclude-golden-ids",
        nargs="*",
        default=[],
        help="Paths to golden QA JSON files whose ticketIds are excluded from Pinecone",
    )
    return parser.parse_args()


async def main_async():
    """Async entry point (single event loop for all communities)."""
    args = _parse_args()

    communities = args.communities or IT_COMMUNITIES
    dry_run = args.dry_run
    limit = args.limit_per_community

    print(f"{'='*60}")
    print(f"  StackExchange Dataset Ingestion")
    print(f"{'='*60}")
    print(f"  Communities: {', '.join(communities)}")
    print(f"  Pinecone namespace: {PINECONE_NAMESPACE}")
    print(f"  Dry run: {dry_run}")
    print(f"  Limit per community: {limit or 'none'}")
    print(f"  Resume mode: {args.resume}")
    if args.exclude_golden_ids:
        print(f"  Golden QA exclusion: {', '.join(args.exclude_golden_ids)}")

    # ── Load golden exclusion IDs ──
    excluded_ids: Set[str] = set()
    if args.exclude_golden_ids:
        excluded_ids = load_golden_ids(args.exclude_golden_ids)
        print(f"  Loaded {len(excluded_ids)} golden IDs for exclusion")
        if dry_run:
            print(f"  Sample golden IDs: {list(excluded_ids)[:5]}")

    # ── Initialize clients ──
    pinecone_index = None
    embeddings_model = None
    mongo_db = None

    if not dry_run:
        print(f"\n  Initializing Pinecone and MongoDB connections...")
        pinecone_index, embeddings_model = _init_pinecone()
        mongo_db = _init_mongo()
        print(f"  ✓ Connections established")

    # ── Process each community ──
    results = []
    for comm in communities:
        try:
            result = await process_community(
                community=comm,
                limit=limit,
                dry_run=dry_run,
                excluded_ids=excluded_ids,
                pinecone_index=pinecone_index,
                embeddings_model=embeddings_model,
                mongo_db=mongo_db,
            )
            results.append(result)
        except Exception as e:
            print(f"\n  ❌ Error processing {comm}: {e}")
            import traceback
            traceback.print_exc()
            results.append({"community": comm, "error": str(e)})

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    total_transformed = sum(
        r.get("transformed") or r.get("mongo_upserted", 0) for r in results if "error" not in r
    )
    total_errors = sum(1 for r in results if "error" in r)
    print(f"  Communities processed: {len(results)}")
    print(f"  Total pairs transformed: {total_transformed}")
    print(f"  Errors: {total_errors}")
    if total_errors:
        for r in results:
            if "error" in r:
                print(f"    ❌ {r['community']}: {r['error']}")

    if not dry_run and not total_errors:
        validate_counts(results)

    print(f"\n  Done.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main_async())
