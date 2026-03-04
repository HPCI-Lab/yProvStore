"""
Scalability sweep wrapper
==========================
Invokes ``test_scalability.py`` headlessly for each user count in
``Config.USER_COUNTS``, collects per-run CSVs, and merges them into a
single summary file.

Run::

    python scenarios/run_scalability_sweep.py
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

    locust_file = os.path.join(os.path.dirname(__file__), "test_scalability.py")
    run_time = os.getenv("SWEEP_RUN_TIME", "3m")
    spawn_rate = int(os.getenv("SWEEP_SPAWN_RATE", "10"))

    summary_rows: list[dict] = []

    for user_count in Config.USER_COUNTS:
        csv_prefix = os.path.join(results_dir, f"scalability_{user_count}")
        print(f"\n{'='*60}")
        print(f"  Running with {user_count} users for {run_time}")
        print(f"{'='*60}\n")

        cmd = [
            sys.executable, "-m", "locust",
            "-f", locust_file,
            "--headless",
            "-u", str(user_count),
            "-r", str(min(spawn_rate, user_count)),
            "--run-time", run_time,
            "--csv", csv_prefix,
            "--host", Config.TARGET_HOST,
        ]
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print(f"  ⚠  Locust exited with code {result.returncode} for {user_count} users")

        # Parse the stats CSV produced by Locust
        stats_file = f"{csv_prefix}_stats.csv"
        if os.path.exists(stats_file):
            with open(stats_file, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row["user_count"] = user_count
                    summary_rows.append(row)

    # Write merged summary
    merged_path = os.path.join(results_dir, "scalability_merged.csv")
    if summary_rows:
        fieldnames = list(summary_rows[0].keys())
        with open(merged_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_rows)
        print(f"\n✅  Merged results written to {merged_path}")
    else:
        print("\n⚠  No results collected.")


if __name__ == "__main__":
    run_sweep()
