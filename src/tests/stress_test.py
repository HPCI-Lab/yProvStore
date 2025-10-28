"""
Locust + Compression test helpers for a FastAPI app that accepts document POSTs (multipart/form-data).

This file contains:
 - A `locust` test user (`DocumentUser`) that uploads files as multipart/form-data using the
   `document_file` field (per your OpenAPI). This is the main document-posting user to use for
   concurrency/load tests.
 - A `CompressionUser` that uploads compressed files (gzip, brotli, zstd if available) as multipart
   uploads while setting the appropriate `Content-Encoding` header.
 - A standalone compression-benchmark CLI to measure compression time & ratio on a single file,
   *and* a folder benchmarking mode that tests every compression level for gzip/brotli/zstd and
   writes results into a JSON file for later plotting.

Design choices
- I extended the script rather than creating a new file so you have a single executable to
  maintain and run. The folder-benchmark mode is invoked with `--bench-folder`.

USAGE (locust):
  pip install locust brotli zstandard
  export DOC_ENDPOINT="/documents"           # path (locust will POST to the host + this path)
  export AUTH_HEADER="Bearer <TOKEN>"
  export DOC_SIZES="1024,16384,65536"      # sizes in bytes to randomly choose from
  export COMP_METHODS="gzip,br,zstd"
  export PARENT_DOCUMENT_PIDS=",parent1,parent2"  # leading empty value means "no parent" is a possible value

  locust -f locust_and_compression_tests.py --headless -u 200 -r 10 --run-time 10m --csv=results

USAGE (compression bench single file):
  python locust_and_compression_tests.py --bench --file sample.pdf --methods gzip,br,zstd

USAGE (compression bench folder, test all levels):
  python locust_and_compression_tests.py --bench-folder --input-folder ./to_test --output results.json

Environment variables used by locust users: see script constants near the top of the file.

JSON output schema (top-level is a list of file results):
[
  {
    "file": "./to_test/sample.pdf",
    "original_size": 41547454,
    "results": [
      {"method": "gzip", "level": 1, "compressed_size": 12345, "ratio": 0.297, "time_s": 0.12},
      {"method": "br",   "level": 11, "compressed_size": 7311658, "ratio": 0.176, "time_s": 54.75},
      {"method": "zstd", "level": 3, "compressed_size": 9000000, "ratio": 0.217, "time_s": 0.09}
    ]
  },
  ...
]

Note: brotli at high quality levels can be significantly slower than gzip/zstd. You can limit
which levels are tested with command-line flags to keep runtime reasonable.

"""

from locust import HttpUser, task, between
import os
import random
import io
import gzip
import time
import json
import pathlib
import sys

# Optional compression libraries
try:
    import brotli
except Exception:
    brotli = None
try:
    import zstandard as zstd
except Exception:
    zstd = None

# Config via environment
DOC_ENDPOINT = os.getenv("DOC_ENDPOINT", "/documents")
AUTH_HEADER = os.getenv("AUTH_HEADER", "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJleHAiOjE3NjAxMTczNzB9.NIpu9j4r-St1xZQfr5ZcaBS82Ar_FliVTxq0Bqc174Q")
DOC_SIZES = [int(s) for s in os.getenv("DOC_SIZES", "1024,16384,65536").split(",") if s.strip()]
CONTENT_TYPE = os.getenv("CONTENT_TYPE", "application/json")
PARENT_DOCUMENT_PIDS = [p for p in os.getenv("PARENT_DOCUMENT_PIDS", ",").split(",")]
COMP_METHODS_ENV = os.getenv("COMP_METHODS", "zstd")
COMP_METHODS = [m.strip().lower() for m in COMP_METHODS_ENV.split(",") if m.strip()]


class DocumentUser(HttpUser):
    """User that uploads a file using multipart/form-data as `document_file`.

    - Chooses a random size from DOC_SIZES
    - Posts the file as multipart with field name `document_file`
    - Optionally includes `parent_document_pid` as a query parameter if provided in env
    """

    # wait_time = between(0.5, 1.5)
    wait_time = between(0.2, 0.5)
    host = os.getenv("TARGET_HOST", "http://localhost:8000")

    @task
    def post_document(self):
        size = random.choice(DOC_SIZES)
        payload = self._generate_payload(size)

        # Build multipart file tuple: (filename, fileobj, content_type)
        files = {"document_file": ("document.bin", io.BytesIO(payload), CONTENT_TYPE)}

        headers = {}
        if AUTH_HEADER:
            headers["Authorization"] = AUTH_HEADER

        # Randomly pick a parent_document_pid value from env list (may contain empty value meaning none)
        parent_pid = random.choice(PARENT_DOCUMENT_PIDS) if PARENT_DOCUMENT_PIDS else ""
        params = {}
        if parent_pid:
            params["parent_document_pid"] = parent_pid

        # Post as multipart/form-data
        with self.client.post(DOC_ENDPOINT, files=files, headers=headers, params=params, name="post_document_multipart", timeout=60, catch_response=True) as resp:
            if resp.status_code >= 500:
                resp.failure(f"server error {resp.status_code}")
            elif resp.status_code >= 400:
                resp.failure(f"client error {resp.status_code}")

    def _generate_payload(self, size):
        return os.urandom(size)


class CompressionUser(HttpUser):
    """User that compresses the document bytes locally and uploads the compressed file as multipart.

    The appropriate Content-Encoding header is set so your API can detect the compressed upload.
    """

    # wait_time = between(1, 2)
    wait_time = between(0.2, 0.5)
    host = os.getenv("TARGET_HOST", "http://localhost:8000")

    @task
    def post_compressed(self):
        method = random.choice(COMP_METHODS) if COMP_METHODS else "gzip"
        size = random.choice(DOC_SIZES)
        payload = os.urandom(size)

        encoding = None
        comp_bytes = payload

        if method == "gzip":
            comp_bytes = gzip.compress(payload)
            encoding = "gzip"
        elif method in ("br", "brotli") and brotli is not None:
            comp_bytes = brotli.compress(payload)
            encoding = "br"
        elif method in ("zstd",) and zstd is not None:
            cctx = zstd.ZstdCompressor()
            comp_bytes = cctx.compress(payload)
            encoding = "zstd"
        else:
            # fallback to uncompressed if library missing
            comp_bytes = payload
            encoding = None

        files = {"document_file": (f"document.{method}", io.BytesIO(comp_bytes), CONTENT_TYPE)}

        headers = {}
        if AUTH_HEADER:
            headers["Authorization"] = AUTH_HEADER
        if encoding:
            headers["Content-Encoding"] = encoding

        with self.client.post(DOC_ENDPOINT, files=files, headers=headers, name=f"post_document_compressed_{method}", timeout=60, catch_response=True) as resp:
            if resp.status_code >= 500:
                resp.failure(f"server error {resp.status_code}")
            elif resp.status_code >= 400:
                resp.failure(f"client error {resp.status_code}")


# ----------------------------
# Standalone compression benchmark CLI
# ----------------------------

def compress_gzip(data: bytes, level: int) -> bytes:
    # gzip.compress supports compresslevel param
    return gzip.compress(data, compresslevel=level)


def compress_brotli(data: bytes, level: int) -> bytes:
    if brotli is None:
        raise RuntimeError("brotli library not available")
    # brotli.compress accepts 'quality' param 0-11
    return brotli.compress(data, quality=level)


def compress_zstd(data: bytes, level: int) -> bytes:
    if zstd is None:
        raise RuntimeError("zstd library not available")
    cctx = zstd.ZstdCompressor(level=level)
    return cctx.compress(data)


def bench_file_levels(path: str, methods: dict) -> dict:
    """Benchmarks a single file for given methods and their levels.

    methods: dict like {"gzip": [1,2,3], "br": [0,1,2], "zstd": [1,2,3]}
    returns a dict with original_size and list of results
    """
    p = pathlib.Path(path)
    data = p.read_bytes()
    original = len(data)
    results = []

    for method, levels in methods.items():
        available = True
        if method == "br" and brotli is None:
            available = False
        if method == "zstd" and zstd is None:
            available = False

        if not available:
            for lvl in levels:
                results.append({
                    "method": method,
                    "level": lvl,
                    "compressed_size": None,
                    "ratio": None,
                    "time_s": None,
                    "available": False,
                })
            continue

        for lvl in levels:
            start = time.perf_counter()
            try:
                if method == "gzip":
                    comp = compress_gzip(data, lvl)
                elif method in ("br", "brotli"):
                    comp = compress_brotli(data, lvl)
                elif method == "zstd":
                    comp = compress_zstd(data, lvl)
                else:
                    raise ValueError(f"Unknown method {method}")
                elapsed = time.perf_counter() - start
                csize = len(comp)
                ratio = csize / original if original > 0 else None
                results.append({
                    "method": method,
                    "level": lvl,
                    "compressed_size": csize,
                    "ratio": ratio,
                    "time_s": elapsed,
                    "available": True,
                })
            except Exception as e:
                elapsed = time.perf_counter() - start
                results.append({
                    "method": method,
                    "level": lvl,
                    "compressed_size": None,
                    "ratio": None,
                    "time_s": elapsed,
                    "available": False,
                    "error": str(e),
                })
    return {"file": str(p), "original_size": original, "results": results}


def bench_folder(input_folder: str, output_json: str, methods: dict, extensions=None):
    p = pathlib.Path(input_folder)
    if not p.is_dir():
        raise FileNotFoundError(f"Input folder {input_folder} not found")

    files = [f for f in p.rglob("*") if f.is_file()]
    if extensions:
        exts = set(e.lower() for e in extensions)
        files = [f for f in files if f.suffix.lower().lstrip('.') in exts]

    out = []
    for f in files:
        print(f"Benchmarking {f} ...")
        res = bench_file_levels(str(f), methods)
        out.append(res)
        # flush intermediate results to avoid data loss on long runs
        with open(output_json, "w") as fh:
            json.dump(out, fh, indent=2)
    print(f"Finished. Results saved to {output_json}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compression benchmark for a sample file or a folder.")
    parser.add_argument("--file", required=False, help="file to compress (if omitted a small generated blob will be used)")
    parser.add_argument("--methods", default="gzip,br,zstd", help="comma-separated methods to try (gzip, br, zstd)")
    parser.add_argument("--bench", action="store_true", help="run bench on single file (when executed directly)")
    parser.add_argument("--bench-folder", action="store_true", help="run bench on all files in a folder and save JSON")
    parser.add_argument("--input-folder", help="folder containing files to benchmark")
    parser.add_argument("--output", help="output JSON file for folder benchmark (default: results.json)")
    parser.add_argument("--gzip-levels", default="1-9", help="range or list for gzip levels, e.g. 1-9 or 1,3,5")
    parser.add_argument("--br-levels", default="0-11", help="range or list for brotli levels, e.g. 0-11")
    parser.add_argument("--zstd-levels", default="1-12", help="range or list for zstd levels, e.g. 1-12")
    parser.add_argument("--extensions", default="", help="comma-separated file extensions to include (e.g. pdf,txt)")

    args = parser.parse_args()

    def parse_levels(s):
        s = s.strip()
        if not s:
            return []
        if ',' in s:
            parts = [int(x) for x in s.split(',')]
            return parts
        if '-' in s:
            a, b = s.split('-')
            return list(range(int(a), int(b) + 1))
        return [int(s)]

    if args.bench:
        methods = [m.strip() for m in args.methods.split(',') if m.strip()]
        if args.file:
            target = args.file
        else:
            sample = os.urandom(200000)  # 200 KB
            tmp = "/tmp/locust_sample.bin"
            with open(tmp, "wb") as f:
                f.write(sample)
            target = tmp

        gzip_levels = parse_levels(args.gzip_levels)
        br_levels = parse_levels(args.br_levels)
        zstd_levels = parse_levels(args.zstd_levels)

        method_levels = {}
        for m in methods:
            if m.lower() == 'gzip':
                method_levels['gzip'] = gzip_levels
            elif m.lower() in ('br', 'brotli'):
                method_levels['br'] = br_levels
            elif m.lower() == 'zstd':
                method_levels['zstd'] = zstd_levels

        result = bench_file_levels(target, method_levels)
        print(json.dumps(result, indent=2))
        sys.exit(0)

    if args.bench_folder:
        if not args.input_folder:
            print("--input-folder is required for --bench-folder", file=sys.stderr)
            sys.exit(1)
        out = args.output or "results.json"
        gzip_levels = parse_levels(args.gzip_levels)
        br_levels = parse_levels(args.br_levels)
        zstd_levels = parse_levels(args.zstd_levels)

        method_levels = {}
        methods = [m.strip() for m in args.methods.split(',') if m.strip()]
        for m in methods:
            if m.lower() == 'gzip':
                method_levels['gzip'] = gzip_levels
            elif m.lower() in ('br', 'brotli'):
                method_levels['br'] = br_levels
            elif m.lower() == 'zstd':
                method_levels['zstd'] = zstd_levels

        exts = [e.strip().lower() for e in args.extensions.split(',')] if args.extensions else None
        bench_folder(args.input_folder, out, method_levels, extensions=exts)
        sys.exit(0)

    print("This file is intended to be used by locust. To run the compression bench use --bench or --bench-folder.")
    sys.exit(0)
