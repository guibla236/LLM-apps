#!/usr/bin/env python3
"""Backfill metadata de tickets-m4-exp-a (P0, voyage-4-lite no-chunk).

Agrega `ticketId` y `text` a la metadata de los 59,961 vectores que se
ingestaron antes del fix del contrato metadata↔retriever. Los embeddings
NO se recalculan: se hace fetch del vector (values + metadata) y upsert
con el mismo vector + metadata nueva (mismos IDs determinísticos).

Uso:
    PINECONE_INDEX_NAME=tickets-m4-exp-a python scripts/backfill_exp_a_metadata.py
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, List, Set

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(str(Path(__file__).parent.parent / ".env"))

from modules.third_party_clients import pinecone_client

NAMESPACE = "kb-se-all"
BATCH_LIST = 100      # límite del SDK para list()
BATCH_IO = 100        # fetch/upsert batch


def strip_chunk_suffix(vector_id: str) -> str:
    """Derive el ticket_id del vector ID."""
    return vector_id.rsplit("_chunk-", 1)[0] if "_chunk-" in vector_id else vector_id


async def fetch_qa_docs(ticket_ids: Set[str]) -> Dict[str, dict]:
    """Batch fetch de qa_pairs desde MongoDB."""
    import motor.motor_asyncio

    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB_NAME")
    client = motor.motor_asyncio.AsyncIOMotorClient(uri)
    db = client[db_name]

    docs = {}
    ids = list(ticket_ids)
    for i in range(0, len(ids), 500):
        batch = ids[i : i + 500]
        cursor = db.qa_pairs.find(
            {"ticketId": {"$in": batch}},
            {"ticketId": 1, "title_body": 1, "community": 1, "_id": 0},
        )
        async for doc in cursor:
            docs[doc["ticketId"]] = doc
        print(f"  Mongo: {len(docs)}/{len(ids)} docs", end="\r")
    print()
    client.close()
    return docs


async def main():
    index = pinecone_client.Index(os.getenv("PINECONE_INDEX_NAME"))

    # ── 1. Listar todos los IDs del namespace (paginado) ──
    print("Listing vector IDs from Pinecone...")
    vector_ids: List[str] = []
    token = None
    while True:
        kwargs = {"namespace": NAMESPACE, "limit": BATCH_LIST}
        if token:
            kwargs["pagination_token"] = token
        response = index.list(**kwargs)
        items = list(response)
        if not items:
            break
        for batch in items:
            vector_ids.extend(batch)
        pagination = getattr(response, "pagination", None)
        token = pagination.next if pagination else None
        if not token:
            break
    print(f"  {len(vector_ids):,} vector IDs listados")

    # ── 2. Derivar ticket_ids y buscar textos en Mongo ──
    ticket_ids = {strip_chunk_suffix(v) for v in vector_ids}
    print(f"  {len(ticket_ids):,} ticket_ids únicos — fetching from MongoDB...")
    qa_docs = await fetch_qa_docs(ticket_ids)
    missing = [t for t in ticket_ids if t not in qa_docs]
    print(f"  {len(missing)} ticket_ids sin doc en Mongo")

    # ── 3. Fetch de vectores (values + metadata) por lotes ──
    print("Fetching vectors (values + metadata)...")
    fetched = {}  # vid -> (values, metadata)
    for i in range(0, len(vector_ids), BATCH_IO):
        batch_ids = vector_ids[i : i + BATCH_IO]
        resp = index.fetch(ids=batch_ids, namespace=NAMESPACE)
        for vid, v in resp.vectors.items():
            fetched[vid] = (v.values, dict(v.metadata))
        print(f"  Fetched {len(fetched)}/{len(vector_ids)}", end="\r")
    print()

    # ── 4. Upsert: mismo vector + metadata completa ──
    print("Upserting with full metadata...")
    total = 0
    for i in range(0, len(vector_ids), BATCH_IO):
        batch_ids = vector_ids[i : i + BATCH_IO]
        upsert_data = []
        for vid in batch_ids:
            values, old = fetched[vid]
            tid = strip_chunk_suffix(vid)
            qa = qa_docs.get(tid, {})
            title_body = qa.get("title_body", "")
            text = title_body if title_body else vid
            meta = {
                "ticketId": tid,
                "text": text,
                "community": qa.get("community", "") or old.get("community", ""),
                "expected_output": old.get("expected_output", ""),
                "priority": old.get("priority", ""),
            }
            upsert_data.append((vid, values, meta))
        index.upsert(vectors=upsert_data, namespace=NAMESPACE)
        total += len(upsert_data)
        print(f"  Upserted {total}/{len(vector_ids)}", end="\r")
    print()

    # ── 5. Verificación ──
    print("Verifying...")
    check = index.fetch(ids=vector_ids[:3], namespace=NAMESPACE)
    for vid, v in check.vectors.items():
        print(f"  {vid}: keys={list(v.metadata.keys())} text[:50]={v.metadata.get('text','')[:50]!r}")
    stats = index.describe_index_stats()
    print(f"  exp-a total: {stats['namespaces'].get(NAMESPACE, {}).get('vector_count', 0):,}")
    print("DONE")


if __name__ == "__main__":
    asyncio.run(main())
