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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze Locust test results")
    parser.add_argument("--stats", help="Path to a Locust _stats.csv file")
    parser.add_argument("--sweep-dir", help="Directory containing scalability CSV files")
    parser.add_argument("--prefix", default="scalability", help="Filename prefix for sweep merge")
    parser.add_argument("--size-impact", help="Path to T11 size_impact.csv")
    args = parser.parse_args()

    if args.stats:
        rows = parse_locust_stats(args.stats)
        summarize_stats(rows)

    if args.sweep_dir:
        merge_scalability_csvs(args.sweep_dir, args.prefix)

    if args.size_impact:
        analyze_size_impact(args.size_impact)

    if not any([args.stats, args.sweep_dir, args.size_impact]):
        parser.print_help()
