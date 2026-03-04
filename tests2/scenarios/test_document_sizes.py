"""
T11 — Document Size Impact
============================
Isolates the effect of document size on upload and download latency.

Runs **sequentially** (one user, no concurrency) for clean measurements.
Uploads and downloads each size tier N times, recording per-request timing
in a custom CSV alongside Locust stats.

Also compares compressed vs uncompressed for each size tier.

Run example::

    python scenarios/test_document_sizes.py --iterations 50 --output results/size_impact.csv
"""

import csv
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
import zstandard as zstd

from helpers.config import Config
from helpers.auth import ensure_test_users, auth_header
from helpers.prov_generator import ProvGenerator


def run_size_impact_test(iterations: int = 50, output_csv: str = "results/size_impact.csv"):
    host = Config.TARGET_HOST

    # Auth setup
    users = ensure_test_users(host, count=1)
    user = users[0]
    if not user.token:
        print("ERROR: could not obtain auth token")
        sys.exit(1)
    headers = auth_header(user.token)

    compressor = zstd.ZstdCompressor(level=Config.ZSTD_LEVEL)
    decompressor = zstd.ZstdDecompressor()

    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)

    rows: list[dict] = []

    for tier, target_size in Config.DOC_SIZES.items():
        raw_payload = ProvGenerator.get(tier)
        compressed_payload = compressor.compress(raw_payload)
        actual_size = len(raw_payload)
        compressed_size = len(compressed_payload)

        print(f"\n{'='*60}")
        print(f"  Tier: {tier} | Raw: {actual_size:,} bytes | Compressed: {compressed_size:,} bytes")
        print(f"{'='*60}")

        # --- Uncompressed upload ---
        pids_raw: list[str] = []
        for i in range(iterations):
            files = {"document_file": (f"size_test_{tier}.json", io.BytesIO(raw_payload), "application/json")}
            t0 = time.perf_counter()
            r = requests.post(f"{host}/documents", files=files, headers=headers, timeout=Config.REQUEST_TIMEOUT)
            elapsed = time.perf_counter() - t0
            pid = None
            if r.status_code in (200, 201):
                pid = r.json().get("document_record", {}).get("pid") or r.json().get("pid")
                if pid:
                    pids_raw.append(pid)
            rows.append({
                "tier": tier, "size_bytes": actual_size, "operation": "upload",
                "compressed": False, "transfer_bytes": actual_size,
                "iteration": i, "status": r.status_code, "time_s": elapsed,
            })
        print(f"  Uncompressed upload: {iterations} iterations done")

        # --- Compressed upload ---
        pids_comp: list[str] = []
        for i in range(iterations):
            files = {"document_file": (f"size_test_{tier}.json", io.BytesIO(compressed_payload), "application/json")}
            h = {**headers, "Content-Encoding": "zstd"}
            t0 = time.perf_counter()
            r = requests.post(f"{host}/documents", files=files, headers=h, timeout=Config.REQUEST_TIMEOUT)
            elapsed = time.perf_counter() - t0
            if r.status_code in (200, 201):
                pid = r.json().get("document_record", {}).get("pid") or r.json().get("pid")
                if pid:
                    pids_comp.append(pid)
            rows.append({
                "tier": tier, "size_bytes": actual_size, "operation": "upload",
                "compressed": True, "transfer_bytes": compressed_size,
                "iteration": i, "status": r.status_code, "time_s": elapsed,
            })
        print(f"  Compressed upload: {iterations} iterations done")

        # --- Uncompressed download ---
        for i in range(min(iterations, len(pids_raw))):
            pid = pids_raw[i % len(pids_raw)]
            t0 = time.perf_counter()
            r = requests.get(f"{host}/documents/{pid}", params={"stream": "true"}, timeout=Config.REQUEST_TIMEOUT)
            elapsed = time.perf_counter() - t0
            body_len = len(r.content) if r.status_code == 200 else 0
            rows.append({
                "tier": tier, "size_bytes": actual_size, "operation": "download",
                "compressed": False, "transfer_bytes": body_len,
                "iteration": i, "status": r.status_code, "time_s": elapsed,
            })
        print(f"  Uncompressed download: {min(iterations, len(pids_raw))} iterations done")

        # --- Compressed download ---
        for i in range(min(iterations, len(pids_comp))):
            pid = pids_comp[i % len(pids_comp)]
            h_dl = {"Accept-Encoding": "zstd"}
            t0 = time.perf_counter()
            r = requests.get(f"{host}/documents/{pid}", params={"stream": "true"}, headers=h_dl, timeout=Config.REQUEST_TIMEOUT)
            transfer_bytes = len(r.content) if r.status_code == 200 else 0
            # Decompress to include that cost in total time
            if r.status_code == 200 and r.content[:4] == b"\x28\xb5\x2f\xfd":
                _ = decompressor.decompress(r.content)
            elapsed = time.perf_counter() - t0
            rows.append({
                "tier": tier, "size_bytes": actual_size, "operation": "download",
                "compressed": True, "transfer_bytes": transfer_bytes,
                "iteration": i, "status": r.status_code, "time_s": elapsed,
            })
        print(f"  Compressed download: {min(iterations, len(pids_comp))} iterations done")

    # Write CSV
    fieldnames = ["tier", "size_bytes", "operation", "compressed", "transfer_bytes", "iteration", "status", "time_s"]
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n✅  Results written to {output_csv}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Document size impact test (sequential)")
    parser.add_argument("--iterations", type=int, default=50, help="Iterations per tier/mode")
    parser.add_argument("--output", default="results/size_impact.csv", help="Output CSV path")
    args = parser.parse_args()

    run_size_impact_test(iterations=args.iterations, output_csv=args.output)
