"""
run_all_tests.py — Sequential test runner
==========================================
Runs all (or a filtered subset of) performance tests T1–T14 sequentially,
collecting results in the ``results/`` directory.

Filter which tests to run via the ``RUN_TESTS`` environment variable:

    # Run all tests (default)
    python run_all_tests.py

    # Run only T1, T3, and T13
    RUN_TESTS=1,3,13 python run_all_tests.py          # bash
    $env:RUN_TESTS="1,3,13"; python run_all_tests.py   # PowerShell

    # Run T1 through T6
    RUN_TESTS=1-6 python run_all_tests.py

    # Mix ranges and individual IDs
    RUN_TESTS=1-4,8,13,14 python run_all_tests.py

Additional env-var overrides:

    LOCUST_USERS     — concurrent users for Locust tests  (default: 50)
    LOCUST_SPAWN     — spawn rate                         (default: 5)
    LOCUST_RUNTIME   — run duration for Locust tests      (default: 5m)
    T11_ITERATIONS   — iterations for T11 size-impact     (default: 50)
    T13_ITERATIONS   — iterations for T13 compression     (default: 20)
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from helpers.config import Config

# ── Configurable via env ────────────────────────────────────────────────────
LOCUST_USERS  = int(os.getenv("LOCUST_USERS", "50"))
LOCUST_SPAWN  = int(os.getenv("LOCUST_SPAWN", "5"))
LOCUST_RUNTIME = os.getenv("LOCUST_RUNTIME", "5m")
T11_ITERATIONS = int(os.getenv("T11_ITERATIONS", "50"))
T13_ITERATIONS = int(os.getenv("T13_ITERATIONS", "20"))

SCENARIOS_DIR = os.path.join(os.path.dirname(__file__), "scenarios")
RESULTS_DIR   = os.path.abspath(Config.RESULTS_DIR)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _locust(scenario_file: str, csv_prefix: str,
            users: int | None = None, spawn: int | None = None,
            run_time: str | None = None) -> list[str]:
    """Build a Locust CLI command."""
    u = users or LOCUST_USERS
    r = spawn or LOCUST_SPAWN
    rt = run_time or LOCUST_RUNTIME
    return [
        sys.executable, "-m", "locust",
        "-f", os.path.join(SCENARIOS_DIR, scenario_file),
        "--headless",
        "-u", str(u),
        "-r", str(min(r, u)),
        "--run-time", rt,
        "--csv", os.path.join(RESULTS_DIR, csv_prefix),
        "--host", Config.TARGET_HOST,
    ]


def _python(script: str, *args: str) -> list[str]:
    """Build a python script command."""
    return [sys.executable, os.path.join(SCENARIOS_DIR, script), *args]


def _run(cmd: list[str], label: str) -> bool:
    """Execute a command, return True on success."""
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  CMD: {' '.join(cmd)}")
    print(f"{'='*70}\n")
    t0 = time.time()
    result = subprocess.run(cmd)
    elapsed = time.time() - t0
    ok = result.returncode == 0
    status = "✅ PASSED" if ok else f"❌ FAILED (exit {result.returncode})"
    print(f"\n  {status}  [{elapsed:.0f}s]\n")
    return ok


# ── Test definitions ────────────────────────────────────────────────────────

@dataclass
class TestDef:
    id: int
    name: str
    run: Callable[[], bool]


def _make_tests() -> list[TestDef]:
    return [
        # TestDef(1,  "T1  — Document Upload Throughput",
        #         lambda: _run(_locust("test_upload_documents.py", "upload_docs"), "T1 — Upload Throughput")),

        # TestDef(2,  "T2  — Document Download Throughput",
        #         lambda: _run(_locust("test_download_documents.py", "download_docs"), "T2 — Download Throughput")),

        # TestDef(3,  "T3  — Compressed vs Uncompressed Upload",
        #         lambda: _run(_locust("test_compressed_upload.py", "compressed_upload"), "T3 — Compressed Upload")),

        # TestDef(4,  "T4  — Compressed vs Uncompressed Download",
        #         lambda: _run(_locust("test_compressed_download.py", "compressed_download"), "T4 — Compressed Download")),

        # TestDef(5,  "T5  — Artifact Upload Throughput",
        #         lambda: _run(_locust("test_upload_artifacts.py", "upload_artifacts", users=30), "T5 — Artifact Upload")),

        # TestDef(6,  "T6  — Artifact Download Throughput",
        #         lambda: _run(_locust("test_download_artifacts.py", "download_artifacts", users=30), "T6 — Artifact Download")),

        # TestDef(7,  "T7  — Scalability Sweep",
        #         lambda: _run(_python("run_scalability_sweep.py"), "T7 — Scalability Sweep")),

        # TestDef(8,  "T8  — Mixed Workload",
        #         lambda: _run(_locust("test_mixed_workload.py", "mixed_workload", run_time="10m"), "T8 — Mixed Workload")),

        # TestDef(9,  "T9  — Metadata Operations",
        #         lambda: _run(_locust("test_metadata_operations.py", "metadata_ops", users=30), "T9 — Metadata Ops")),

        # TestDef(10, "T10 — Pagination & Listing",
        #         lambda: _run(_locust("test_pagination_listing.py", "pagination", users=30), "T10 — Pagination")),

        # TestDef(11, "T11 — Document Size Impact",
        #         lambda: _run(
        #             _python("test_document_sizes.py",
        #                     "--iterations", str(T11_ITERATIONS),
        #                     "--output", os.path.join(RESULTS_DIR, "size_impact.csv")),
        #             "T11 — Size Impact")),

        TestDef(12, "T12 — Sustained Load / Endurance",
                lambda: _run(
                    _locust("test_sustained_load.py", "sustained",
                            users=Config.SUSTAINED_USERS, run_time="5m"),
                    "T12 — Sustained Load")),

        # TestDef(13, "T13 — Compression Algorithm Comparison",
        #         lambda: _run(
        #             _python("test_compression_comparison.py",
        #                     "--iterations", str(T13_ITERATIONS),
        #                     "--output", os.path.join(RESULTS_DIR, "compression_comparison.csv")),
        #             "T13 — Compression Comparison")),

        # TestDef(14, "T14 — Maximum Throughput / Breaking Point",
        #         lambda: _run(_python("run_max_throughput_sweep.py"), "T14 — Max Throughput Sweep")),
    ]


# ── Parse RUN_TESTS filter ─────────────────────────────────────────────────

def _parse_run_tests(raw: str) -> set[int]:
    """Parse ``RUN_TESTS`` value like ``1,3-6,13`` into a set of ints."""
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            ids.update(range(int(lo), int(hi) + 1))
        else:
            ids.add(int(part))
    return ids


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    all_tests = _make_tests()

    # Filter
    raw_filter = os.getenv("RUN_TESTS", "").strip()
    if raw_filter:
        selected = _parse_run_tests(raw_filter)
        tests = [t for t in all_tests if t.id in selected]
        if not tests:
            print(f"No tests matched RUN_TESTS={raw_filter!r}. Available: 1–{len(all_tests)}")
            sys.exit(1)
    else:
        tests = all_tests

    print(f"\n{'#'*70}")
    print(f"  yProvStore Performance Test Runner")
    print(f"  Host:    {Config.TARGET_HOST}")
    print(f"  Tests:   {', '.join(f'T{t.id}' for t in tests)}")
    print(f"  Results: {RESULTS_DIR}")
    print(f"{'#'*70}\n")

    results: list[tuple[str, bool]] = []
    t_start = time.time()

    for test in tests:
        ok = test.run()
        results.append((test.name, ok))

    total_time = time.time() - t_start

    # Summary
    print(f"\n{'#'*70}")
    print(f"  SUMMARY  ({total_time:.0f}s total)")
    print(f"{'#'*70}")
    passed = 0
    for name, ok in results:
        icon = "✅" if ok else "❌"
        print(f"  {icon}  {name}")
        if ok:
            passed += 1
    print(f"\n  {passed}/{len(results)} passed\n")

    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
