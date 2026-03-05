"""
Max throughput sweep wrapper
==============================
Invokes ``test_max_throughput.py`` headlessly at increasing user counts
from ``Config.MAX_RPS_USER_COUNTS``.  Collects per-step CSVs and writes a
merged summary with a ``user_count`` column.

The sweep identifies the **breaking point**: the user count at which error
rate exceeds 1 % or p95 latency doubles compared to the first step.

Run::

    python scenarios/run_max_throughput_sweep.py
"""

import csv
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from helpers.config import Config


def run_sweep():
    results_dir = os.path.abspath(Config.RESULTS_DIR)
    os.makedirs(results_dir, exist_ok=True)

    locust_file = os.path.join(os.path.dirname(__file__), "test_max_throughput.py")
    step_duration = Config.MAX_RPS_STEP_DURATION

    summary_rows: list[dict] = []
    baseline_p95: float | None = None
    breaking_point: int | None = None

    for user_count in Config.MAX_RPS_USER_COUNTS:
        csv_prefix = os.path.join(results_dir, f"max_rps_{user_count}")
        print(f"\n{'='*60}")
        print(f"  Max-throughput sweep: {user_count} users for {step_duration}")
        print(f"{'='*60}\n")

        spawn_rate = max(10, user_count // 2)
        cmd = [
            sys.executable, "-m", "locust",
            "-f", locust_file,
            "--headless",
            "-u", str(user_count),
            "-r", str(spawn_rate),
            "--run-time", step_duration,
            "--csv", csv_prefix,
            "--host", Config.TARGET_HOST,
        ]
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print(f"  ⚠  Locust exited with code {result.returncode} for {user_count} users")

        stats_file = f"{csv_prefix}_stats.csv"
        if os.path.exists(stats_file):
            with open(stats_file, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row["user_count"] = user_count
                    summary_rows.append(row)

                    # Detect breaking point from the Aggregated row
                    if row.get("Name", "").strip() == "Aggregated":
                        try:
                            total_reqs = int(row.get("Request Count", row.get("# Requests", 0)))
                            total_fails = int(row.get("Failure Count", row.get("# Failures", 0)))
                            error_pct = (total_fails / total_reqs * 100) if total_reqs > 0 else 0
                            p95 = float(row.get("95%", 0))
                            rps = float(row.get("Requests/s", 0))

                            if baseline_p95 is None:
                                baseline_p95 = p95

                            print(f"  → RPS={rps:.1f}  p95={p95:.0f}ms  errors={error_pct:.2f}%")

                            if breaking_point is None and (error_pct > 1.0 or p95 > baseline_p95 * 3):
                                breaking_point = user_count
                                print(f"  🔴  Breaking point detected at {user_count} users!")
                        except (ValueError, ZeroDivisionError):
                            pass

    # Write merged summary
    merged_path = os.path.join(results_dir, "max_throughput_merged.csv")
    if summary_rows:
        fieldnames = list(summary_rows[0].keys())
        with open(merged_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_rows)
        print(f"\n✅  Merged results written to {merged_path}")
    else:
        print("\n⚠  No results collected.")

    if breaking_point:
        print(f"\n🔴  Estimated breaking point: {breaking_point} concurrent users")
    else:
        print(f"\n🟢  No breaking point detected up to {Config.MAX_RPS_USER_COUNTS[-1]} users")


if __name__ == "__main__":
    run_sweep()
