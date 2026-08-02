#!/usr/bin/env python3
"""
Embedding Latency Benchmark — OpenRouter API vs local Ollama.

Measures per-call and batch latency for the configured embedding models
using the project's own clients (get_embeddings_model). Used to document
the latency impact of switching from local Ollama to OpenRouter-hosted
embeddings (M4 — Search Optimization).

Usage:
    python scripts/benchmark_embeddings.py
    python scripts/benchmark_embeddings.py --samples 20
    python scripts/benchmark_embeddings.py --ollama-model all-minilm:22m --openrouter-model voyage-4-lite
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

# Results are persisted to the evaluation raw_results folder by default,
# alongside the other evaluation artifacts (run_eval.py CSVs/aggregates).
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent / "evaluation_notebooks" / "raw_results"


# ── Sample texts ─────────────────────────────────────────────────────────────
# Representative of the real corpus: StackExchange-style technical questions
# (~500-1000 chars, IT support domain).
_SAMPLE_TEXTS = [
    "How do I configure a static IP address on Ubuntu Server 22.04 using netplan? "
    "I edited /etc/netplan/00-installer-config.yaml but after netplan apply the "
    "network goes down and I lose SSH access. My interface is enp3s0 and my router "
    "is at 192.168.1.1 with a /24 subnet. I need the server to keep the IP after reboot.",
    "My Windows 10 machine keeps showing a blue screen with error code 0x0000007B "
    "after I changed the SATA mode from IDE to AHCI in the BIOS. I have an SSD with "
    "Windows installed and I cannot boot into safe mode either. What registry "
    "settings need to be changed to allow AHCI drivers to load?",
    "Is it possible to restrict SSH access by IP address using TCP wrappers on a "
    "Linux server? I have several users connecting from different subnets and I "
    "want to allow only specific IP ranges to connect to port 22 while keeping "
    "other services accessible. Does /etc/hosts.allow support CIDR notation?",
    "I need to migrate a PostgreSQL 12 database to a new server with PostgreSQL 15. "
    "The database is about 200GB with several large tables. What is the safest "
    "approach? Should I use pg_dump and pg_restore or is there a faster way using "
    "logical replication? The new server has more RAM and NVMe storage.",
    "My macOS laptop does not connect to the corporate Wi-Fi network with 802.1X "
    "authentication. The certificate was installed via Jamf but the connection "
    "fails with a certificate error. Other devices on the same network work fine. "
    "I already deleted and re-added the Wi-Fi profile but the issue persists.",
    "How can I check which process is listening on a specific port in Linux? "
    "I have an application that fails to start because port 8080 is already in "
    "use, but netstat does not show the process name. I need to find the PID "
    "and the command line arguments of the process occupying the port.",
    "What is the difference between a managed switch and an unmanaged switch for "
    "a small office network with 30 devices? I need VLAN support for separating "
    "guest traffic and I want to know if a layer 2 managed switch is sufficient "
    "or if I need layer 3 capabilities for inter-VLAN routing.",
    "My Android phone keeps disconnecting from the office Wi-Fi network every few "
    "minutes even though the signal is strong. I already forgot the network and "
    "reconnected. The issue started after the IT department enabled MAC address "
    "randomization. Could the DHCP lease time or the captive portal be the cause?",
    "How do I set up a cron job to run a Python script every day at 2 AM on "
    "Ubuntu? The script writes logs to a file and I need the environment "
    "variables to be available when it runs. I tried crontab -e but the script "
    "fails silently. Where should I check the cron logs?",
    "We are planning to replace our on-premises Exchange server with Microsoft "
    "365. The domain has about 120 mailboxes and several shared mailboxes with "
    "large PST files. What is the recommended migration path and how long does "
    "the cutover typically take? Are there any known issues with iOS mail clients?",
]


def _benchmark(client, texts: list[str], label: str) -> dict:
    """Measure per-call and batch latency for an embeddings client."""
    # Warm-up (model load / connection pool)
    client.embed_query("warmup")

    # Per-call latency (single text, repeated)
    per_call_times = []
    for text in texts:
        t0 = time.perf_counter()
        client.embed_query(text)
        per_call_times.append(time.perf_counter() - t0)

    # Batch latency (all texts in one call)
    t0 = time.perf_counter()
    client.embed_documents(texts)
    batch_time = time.perf_counter() - t0

    results = {
        "label": label,
        "per_call_mean_ms": sum(per_call_times) / len(per_call_times) * 1000,
        "per_call_min_ms": min(per_call_times) * 1000,
        "per_call_max_ms": max(per_call_times) * 1000,
        "batch_total_ms": batch_time * 1000,
        "batch_per_doc_ms": batch_time / len(texts) * 1000,
    }
    return results


def _print_results(results: list[dict], samples: int) -> None:
    print(f"\n{'='*70}")
    print(f"  Embedding Latency Benchmark ({samples} samples, {len(results)} providers)")
    print(f"{'='*70}")
    print(f"\n  {'Provider':<38} {'mean/call':>10} {'min':>8} {'max':>8} {'batch total':>12} {'per doc':>9}")
    print(f"  {'-'*38} {'-'*10} {'-'*8} {'-'*8} {'-'*12} {'-'*9}")
    for r in results:
        print(
            f"  {r['label']:<38} {r['per_call_mean_ms']:>8.0f}ms "
            f"{r['per_call_min_ms']:>6.0f}ms {r['per_call_max_ms']:>6.0f}ms "
            f"{r['batch_total_ms']:>10.0f}ms {r['batch_per_doc_ms']:>7.0f}ms"
        )
    print()


def _save_results(results: list[dict], samples: int, output_dir: Path) -> Path:
    """Persist benchmark results as JSON with timestamp (for reproducibility)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "samples": samples,
        "results": results,
    }
    out_path = output_dir / f"embedding_latency_{timestamp}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"  Results saved to: {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=10, help="Number of sample texts (max 10)")
    parser.add_argument("--ollama-model", default="all-minilm:22m", help="Local Ollama model")
    parser.add_argument("--openrouter-model", default="voyage-4-lite", help="OpenRouter model")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for the persisted JSON results (default: evaluation_notebooks/raw_results)",
    )
    args = parser.parse_args()

    from modules.third_party_clients import get_embeddings_model

    texts = _SAMPLE_TEXTS[: args.samples]

    print(f"  Benchmarking {len(texts)} samples...")
    print(f"  Ollama model: {args.ollama_model}")
    print(f"  OpenRouter model: {args.openrouter_model}")

    results = []

    # 1. Local Ollama
    print("\n  → Testing local Ollama...")
    try:
        from langchain_ollama import OllamaEmbeddings

        ollama = OllamaEmbeddings(model=args.ollama_model)
        results.append(_benchmark(ollama, texts, f"Ollama local ({args.ollama_model})"))
        print("  ✓ done")
    except Exception as e:
        print(f"  ✗ Ollama failed: {e}")

    # 2. OpenRouter API (via get_embeddings_model — sends strings, not tokens)
    print("\n  → Testing OpenRouter API...")
    try:
        openrouter = get_embeddings_model(args.openrouter_model)
        results.append(_benchmark(openrouter, texts, f"OpenRouter ({args.openrouter_model})"))
        print("  ✓ done")
    except Exception as e:
        print(f"  ✗ OpenRouter failed: {e}")

    if results:
        _print_results(results, len(texts))
        _save_results(results, len(texts), args.output_dir)
    else:
        print("\n  No results — both providers failed.")


if __name__ == "__main__":
    main()
