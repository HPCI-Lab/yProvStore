"""
Post-processing for Locust CSV results.

Parses Locust ``_stats.csv`` and ``_stats_history.csv`` files, computes
summary statistics, and optionally merges scalability sweep data.

Usage::

    python analysis/analyze_results.py --stats results/upload_docs_stats.csv
    python analysis/analyze_results.py --sweep-dir results/ --prefix scalability
"""

import csv
import glob
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def parse_locust_stats(stats_csv: str) -> list[dict]:
    """Read a Locust ``_stats.csv`` and return rows as dicts."""
    with open(stats_csv, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def summarize_stats(rows: list[dict]) -> None:
    """Print a summary table from Locust stats rows."""
    print(f"\n{'Name':<40} {'Reqs':>8} {'Fails':>8} {'Avg(ms)':>10} {'p50':>8} {'p95':>8} {'p99':>8} {'RPS':>10}")
    print("-" * 110)
    for row in rows:
        name = row.get("Name", "")
        if name == "Aggregated":
            print("-" * 110)
        print(
            f"{name:<40} "
            f"{row.get('Request Count', row.get('# Requests', '')):>8} "
            f"{row.get('Failure Count', row.get('# Failures', '')):>8} "
            f"{row.get('Average Response Time', row.get('Average (ms)', '')):>10} "
            f"{row.get('50%', ''):>8} "
            f"{row.get('95%', ''):>8} "
            f"{row.get('99%', ''):>8} "
            f"{row.get('Requests/s', ''):>10}"
        )


def merge_scalability_csvs(results_dir: str, prefix: str = "scalability") -> str:
    """Merge multiple ``{prefix}_{N}_stats.csv`` files into one CSV with a ``user_count`` column."""
    pattern = os.path.join(results_dir, f"{prefix}_*_stats.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"No files matching {pattern}")
        return ""

    merged_rows: list[dict] = []
    for fpath in files:
        # Extract user count from filename: scalability_25_stats.csv -> 25
        stem = Path(fpath).stem  # scalability_25_stats
        parts = stem.replace("_stats", "").split("_")
        user_count = parts[-1] if parts else "?"

        rows = parse_locust_stats(fpath)
        for row in rows:
            row["user_count"] = user_count
            merged_rows.append(row)

    output = os.path.join(results_dir, f"{prefix}_merged.csv")
    if merged_rows:
        fieldnames = list(merged_rows[0].keys())
        with open(output, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(merged_rows)
        print(f"Merged {len(files)} files → {output}")
    return output


def analyze_size_impact(csv_path: str) -> None:
    """Print summary of the T11 size-impact CSV."""
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Group by (tier, operation, compressed)
    groups: dict[tuple, list[float]] = {}
    for row in rows:
        key = (row["tier"], row["operation"], row["compressed"])
        groups.setdefault(key, []).append(float(row["time_s"]))

    print(f"\n{'Tier':<10} {'Op':<12} {'Compressed':<12} {'Count':>6} {'Avg(s)':>10} {'p50(s)':>10} {'p95(s)':>10}")
    print("-" * 80)
    for key, times in sorted(groups.items()):
        times_sorted = sorted(times)
        n = len(times_sorted)
        avg = sum(times_sorted) / n
        p50 = times_sorted[int(n * 0.5)]
        p95 = times_sorted[min(int(n * 0.95), n - 1)]
        tier, op, comp = key
        print(f"{tier:<10} {op:<12} {comp:<12} {n:>6} {avg:>10.4f} {p50:>10.4f} {p95:>10.4f}")


def analyze_compression_comparison(csv_path: str) -> None:
    """Print summary of the T13 compression comparison CSV."""
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Group by (tier, method, level)
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        key = (row["tier"], row["method"], row["level"])
        groups.setdefault(key, []).append(row)

    print(f"\n{'Tier':<10} {'Method':<10} {'Level':>5} {'Count':>6} {'Ratio':>8} "
          f"{'Comp(s)':>10} {'Upload(s)':>10} {'Download(s)':>10}")
    print("-" * 90)

    for key, entries in sorted(groups.items()):
        tier, method, level = key
        n = len(entries)
        avg_ratio = sum(float(e["ratio"]) for e in entries) / n
        avg_comp = sum(float(e["compress_time_s"]) for e in entries) / n
        avg_up = sum(float(e["upload_time_s"]) for e in entries) / n
        avg_dl = sum(float(e["download_time_s"]) for e in entries) / n
        print(f"{tier:<10} {method:<10} {level:>5} {n:>6} {avg_ratio:>8.4f} "
              f"{avg_comp:>10.4f} {avg_up:>10.4f} {avg_dl:>10.4f}")


def analyze_max_throughput(csv_path: str) -> None:
    """Print summary of the T14 max-throughput sweep CSV."""
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Filter to Aggregated rows
    agg_rows = [r for r in rows if r.get("Name", "").strip() == "Aggregated"]
    if not agg_rows:
        print("  No 'Aggregated' rows found.")
        return

    rps_key = "Requests/s" if "Requests/s" in agg_rows[0] else "Current RPS"
    p95_key = "95%" if "95%" in agg_rows[0] else "95%"
    req_key = "Request Count" if "Request Count" in agg_rows[0] else "# Requests"
    fail_key = "Failure Count" if "Failure Count" in agg_rows[0] else "# Failures"

    print(f"\n{'Users':>8} {'RPS':>10} {'p50(ms)':>10} {'p95(ms)':>10} {'p99(ms)':>10} {'Error%':>10}")
    print("-" * 65)

    baseline_p95 = None
    breaking_point = None

    for row in agg_rows:
        users = row.get("user_count", "?")
        rps = float(row.get(rps_key, 0))
        p50 = float(row.get("50%", 0))
        p95 = float(row.get(p95_key, 0))
        p99 = float(row.get("99%", 0))
        total = int(row.get(req_key, 0))
        fails = int(row.get(fail_key, 0))
        err_pct = (fails / total * 100) if total > 0 else 0

        if baseline_p95 is None:
            baseline_p95 = p95

        marker = ""
        if breaking_point is None and (err_pct > 1.0 or p95 > baseline_p95 * 3):
            breaking_point = users
            marker = " ← BREAKING POINT"

        print(f"{users:>8} {rps:>10.1f} {p50:>10.0f} {p95:>10.0f} {p99:>10.0f} {err_pct:>9.2f}%{marker}")

    if breaking_point:
        print(f"\n  🔴  Breaking point at {breaking_point} concurrent users")
    else:
        print(f"\n  🟢  No breaking point detected")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze Locust test results")
    parser.add_argument("--stats", help="Path to a Locust _stats.csv file")
    parser.add_argument("--sweep-dir", help="Directory containing scalability CSV files")
    parser.add_argument("--prefix", default="scalability", help="Filename prefix for sweep merge")
    parser.add_argument("--size-impact", help="Path to T11 size_impact.csv")
    parser.add_argument("--compression", help="Path to T13 compression_comparison.csv")
    parser.add_argument("--max-throughput", help="Path to T14 max_throughput_merged.csv")
    args = parser.parse_args()

    if args.stats:
        rows = parse_locust_stats(args.stats)
        summarize_stats(rows)

    if args.sweep_dir:
        merge_scalability_csvs(args.sweep_dir, args.prefix)

    if args.size_impact:
        analyze_size_impact(args.size_impact)

    if args.compression:
        analyze_compression_comparison(args.compression)

    if args.max_throughput:
        analyze_max_throughput(args.max_throughput)

    if not any([args.stats, args.sweep_dir, args.size_impact, args.compression, args.max_throughput]):
        parser.print_help()
