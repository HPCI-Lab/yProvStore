"""
T13 — Compression Algorithm Comparison
========================================
Compares gzip, brotli, and zstd at multiple compression levels across all
document size tiers.

Runs **sequentially** (like T11) for precise per-operation measurements.
For each (tier × algorithm × level) combination the script:

1. Compresses the raw PROV-JSON payload and records compression time + ratio.
2. Uploads the compressed payload (using ``Content-Encoding``) and records
   server-side acceptance latency.
3. Downloads the document and records transfer + decompression time.

Results are written to a CSV with columns:

    tier, size_bytes, method, level, compressed_bytes, ratio,
    compress_time_s, upload_time_s, download_time_s, decompress_time_s

Run example::

    python scenarios/test_compression_comparison.py \\
           --iterations 20 --output results/compression_comparison.csv
"""

import csv
import gzip
import io
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import brotli
import requests
import zstandard as zstd

from helpers.config import Config
from helpers.auth import ensure_test_users, auth_header
from helpers.prov_generator import ProvGenerator

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


def _compress(method: str, level: int, data: bytes) -> bytes:
    """Compress *data* using the given method and level."""
    if method == "gzip":
        return gzip.compress(data, compresslevel=level)
    elif method == "brotli":
        return brotli.compress(data, quality=level)
    elif method == "zstd":
        cctx = zstd.ZstdCompressor(level=level)
        return cctx.compress(data)
    else:
        raise ValueError(f"Unknown method: {method}")


def _decompress(method: str, data: bytes) -> bytes:
    if method == "gzip":
        return gzip.decompress(data)
    elif method == "brotli":
        return brotli.decompress(data)
    elif method == "zstd":
        dctx = zstd.ZstdDecompressor()
        return dctx.decompress(data)
    else:
        raise ValueError(f"Unknown method: {method}")


def _content_encoding(method: str) -> str:
    """Return the HTTP Content-Encoding value."""
    # All three use their name as the encoding token
    return method


def run_compression_comparison(
    iterations: int = 20,
    output_csv: str = "results/compression_comparison.csv",
    tiers: list[str] | None = None,
):
    host = Config.TARGET_HOST

    # Auth
    users = ensure_test_users(host, count=1)
    user = users[0]
    if not user.token:
        print("ERROR: could not obtain auth token")
        sys.exit(1)
    headers = auth_header(user.token)

    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)

    # Select tiers
    if tiers:
        doc_tiers = {k: v for k, v in Config.DOC_SIZES.items() if k in tiers}
    else:
        doc_tiers = Config.DOC_SIZES

    methods = Config.COMPRESSION_METHODS
    levels = Config.COMPRESSION_LEVELS

    rows: list[dict] = []

    for tier, target_size in doc_tiers.items():
        raw_payload = ProvGenerator.get(tier)
        raw_size = len(raw_payload)

        print(f"\n{'='*70}")
        print(f"  Tier: {tier}  |  Raw size: {raw_size:,} bytes")
        print(f"{'='*70}")

        # --- Baseline: uncompressed upload & download ---
        for i in range(iterations):
            files = {
                "document_file": (
                    f"cmp_test_{tier}.json",
                    io.BytesIO(raw_payload),
                    "application/json",
                ),
            }
            t0 = time.perf_counter()
            r = requests.post(
                f"{host}/documents",
                files=files,
                headers=headers,
                timeout=Config.REQUEST_TIMEOUT,
            )
            upload_time = time.perf_counter() - t0

            pid = None
            if r.status_code in (200, 201):
                pid = (
                    r.json().get("document_record", {}).get("pid")
                    or r.json().get("pid")
                )

            # Download
            download_time = 0.0
            if pid:
                t0 = time.perf_counter()
                rd = requests.get(
                    f"{host}/documents/{pid}",
                    params={"stream": "true"},
                    headers=headers,
                    timeout=Config.REQUEST_TIMEOUT,
                )
                download_time = time.perf_counter() - t0
                if rd.status_code == 200:
                    _ = rd.content

            rows.append({
                "tier": tier,
                "size_bytes": raw_size,
                "method": "none",
                "level": 0,
                "compressed_bytes": raw_size,
                "ratio": 1.0,
                "compress_time_s": 0.0,
                "upload_time_s": upload_time,
                "download_time_s": download_time,
                "decompress_time_s": 0.0,
                "iteration": i,
                "status": r.status_code,
            })

        print(f"  Baseline (uncompressed): {iterations} iterations done")

        # --- Each compression method × level ---
        for method in methods:
            method_levels = levels.get(method, [1])
            for level in method_levels:
                print(f"  {method} level {level} … ", end="", flush=True)

                # Pre-compress to measure ratio (once)
                t_comp_start = time.perf_counter()
                compressed_payload = _compress(method, level, raw_payload)
                single_compress_time = time.perf_counter() - t_comp_start
                comp_size = len(compressed_payload)
                ratio = comp_size / raw_size if raw_size > 0 else 1.0

                for i in range(iterations):
                    # Compress (measure each time for variance)
                    t0 = time.perf_counter()
                    compressed = _compress(method, level, raw_payload)
                    compress_time = time.perf_counter() - t0

                    # Upload with Content-Encoding
                    encoding = _content_encoding(method)
                    h_upload = {**headers, "Content-Encoding": encoding}
                    files = {
                        "document_file": (
                            f"cmp_test_{tier}_{method}_{level}.json",
                            io.BytesIO(compressed),
                            "application/json",
                        ),
                    }
                    t0 = time.perf_counter()
                    r = requests.post(
                        f"{host}/documents",
                        files=files,
                        headers=h_upload,
                        timeout=Config.REQUEST_TIMEOUT,
                    )
                    upload_time = time.perf_counter() - t0

                    pid = None
                    if r.status_code in (200, 201):
                        pid = (
                            r.json().get("document_record", {}).get("pid")
                            or r.json().get("pid")
                        )

                    # Download + decompress
                    download_time = 0.0
                    decompress_time = 0.0
                    if pid:
                        h_dl = {**headers, "Accept-Encoding": encoding}
                        t0 = time.perf_counter()
                        rd = requests.get(
                            f"{host}/documents/{pid}",
                            params={"stream": "true"},
                            headers=h_dl,
                            timeout=Config.REQUEST_TIMEOUT,
                        )
                        download_time = time.perf_counter() - t0

                        if rd.status_code == 200:
                            body = rd.content
                            # Decompress if served compressed
                            if body[:4] == ZSTD_MAGIC or len(body) < raw_size * 0.95:
                                t0 = time.perf_counter()
                                try:
                                    _ = _decompress("zstd", body)
                                except Exception:
                                    pass  # server may have returned raw
                                decompress_time = time.perf_counter() - t0

                    rows.append({
                        "tier": tier,
                        "size_bytes": raw_size,
                        "method": method,
                        "level": level,
                        "compressed_bytes": len(compressed),
                        "ratio": len(compressed) / raw_size if raw_size > 0 else 1.0,
                        "compress_time_s": compress_time,
                        "upload_time_s": upload_time,
                        "download_time_s": download_time,
                        "decompress_time_s": decompress_time,
                        "iteration": i,
                        "status": r.status_code,
                    })

                print(f"{iterations} iterations (ratio={ratio:.3f}, comp_size={comp_size:,})")

    # Write CSV
    fieldnames = [
        "tier", "size_bytes", "method", "level", "compressed_bytes", "ratio",
        "compress_time_s", "upload_time_s", "download_time_s", "decompress_time_s",
        "iteration", "status",
    ]
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅  Compression comparison results written to {output_csv}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compression algorithm comparison (T13)")
    parser.add_argument("--iterations", type=int, default=20, help="Iterations per combination")
    parser.add_argument("--output", default="results/compression_comparison.csv", help="Output CSV")
    parser.add_argument(
        "--tiers",
        default=None,
        help="Comma-separated tier list (default: all). E.g. small,medium,large",
    )
    args = parser.parse_args()

    tier_list = args.tiers.split(",") if args.tiers else None
    run_compression_comparison(
        iterations=args.iterations,
        output_csv=args.output,
        tiers=tier_list,
    )
