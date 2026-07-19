#!/usr/bin/env python3
"""
BM25 Index Builder for StackExchange enriched corpus.

Reads the full Q&A pairs from MongoDB qa_pairs collection and builds a local
bm25_index.json enriched with `page_content_bm25` (ticketId + title_body +
upvoted_answer[:500]) for better keyword matching. Preserves the legacy `kb`
section from the existing index.

Usage:
    python scripts/build_bm25_index.py

Requires:
    - MONGODB_URI and MONGODB_DB_NAME environment variables set
    - MongoDB qa_pairs collection populated (run ingest_stackexchange_dataset.py first)
"""

import json
import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timezone

sys.path.append(str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient


# Paths
API_DIR = Path(__file__).parent.parent
STATIC_DIR = API_DIR / "static"
BM25_INDEX_PATH = STATIC_DIR / "bm25_index.json"


async def build_bm25_index():
    """Main builder: read MongoDB qa_pairs → write enriched bm25_index.json."""
    # ── 1. Connect to MongoDB ──
    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB_NAME")
    if not uri or not db_name:
        print("ERROR: MONGODB_URI and MONGODB_DB_NAME must be set.")
        sys.exit(1)

    print(f"Connecting to MongoDB: {db_name}")
    client = AsyncIOMotorClient(uri)
    db = client[db_name]

    # ── 2. Count documents ──
    total_docs = await db.qa_pairs.count_documents({})
    print(f"Found {total_docs} documents in qa_pairs")

    if total_docs == 0:
        print("WARNING: No qa_pairs found. Run ingest_stackexchange_dataset.py first.")
        # Still preserve KB section and write minimal tickets
        total_docs = 0

    # ── 3. Load qa_pairs from MongoDB ──
    tickets_for_bm25 = []
    if total_docs > 0:
        cursor = db.qa_pairs.find({})
        batch_size = 1000
        batch = []

        async for doc in cursor:
            batch.append(doc)
            if len(batch) >= batch_size:
                _process_batch(batch, tickets_for_bm25)
                print(f"  Processed {len(tickets_for_bm25)} / {total_docs}", end="\r")
                batch = []

        if batch:
            _process_batch(batch, tickets_for_bm25)

        print(f"\n  Done. Total tickets: {len(tickets_for_bm25)}")

    # ── 4. Preserve legacy KB section ──
    legacy_kb = []
    if BM25_INDEX_PATH.exists():
        with open(BM25_INDEX_PATH, "r", encoding="utf-8") as f:
            legacy_data = json.load(f)
        legacy_kb = legacy_data.get("kb", [])
        print(f"Preserved {len(legacy_kb)} KB documents from legacy index")

    # ── 5. Write enriched index ──
    output = {
        "tickets": tickets_for_bm25,
        "kb": legacy_kb,
    }

    # Count before writing
    ticket_count = len(tickets_for_bm25)

    with open(BM25_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    file_size_mb = BM25_INDEX_PATH.stat().st_size / (1024 * 1024)
    print(f"\n✅ BM25 index written to {BM25_INDEX_PATH}")
    print(f"   Tickets: {ticket_count}")
    print(f"   KB docs: {len(legacy_kb)}")
    print(f"   Size: {file_size_mb:.1f} MB")

    # ── 6. Close connection ──
    client.close()


def _process_batch(batch: list, tickets_for_bm25: list):
    """Transform a batch of MongoDB docs into BM25 ticket entries."""
    for doc in batch:
        ticket_id = doc.get("ticketId", "")
        title_body = doc.get("title_body", "")
        upvoted_answer = doc.get("upvoted_answer", "") or ""
        community = doc.get("community", "")
        priority = doc.get("priority", "")

        # Build enriched page_content for BM25
        page_content_bm25 = (
            f"{ticket_id} {title_body} {upvoted_answer[:500]}"
        )

        tickets_for_bm25.append({
            "ticketId": ticket_id,
            "description": title_body,
            "page_content_bm25": page_content_bm25,
            "community": community,
            "priority": priority,
            "source": "stackexchange",
        })


if __name__ == "__main__":
    asyncio.run(build_bm25_index())
