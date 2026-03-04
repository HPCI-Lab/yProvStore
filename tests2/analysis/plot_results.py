"""
Plotting for performance test results.

Generates publication-quality charts from Locust CSV output and the
custom T11 size-impact CSV.

Usage::

    python analysis/plot_results.py --stats results/compressed_upload_stats.csv
    python analysis/plot_results.py --size-impact results/size_impact.csv
    python analysis/plot_results.py --scalability results/scalability_merged.csv
    python analysis/plot_results.py --sustained results/sustained_stats_history.csv
"""

import csv
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

sns.set_theme(style="whitegrid", font_scale=1.1)
FIGSIZE = (12, 6)
OUTPUT_DIR = os.getenv("PLOT_OUTPUT_DIR", "results/plots")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _save(fig, name: str):
    path = os.path.join(OUTPUT_DIR, f"{name}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  Saved {path}")
    plt.close(fig)


# ── 1. Compressed vs Uncompressed (from Locust stats) ──────────────────────

def plot_compressed_vs_uncompressed(stats_csv: str):
    """Bar chart comparing latency for compressed vs uncompressed operations.

    Expects Locust stats CSV where ``Name`` column contains patterns like
    ``upload_compressed_medium`` and ``upload_uncompressed_medium``.
    """
    df = pd.read_csv(stats_csv)
    # Normalize column names (Locust versions vary)
    df.columns = [c.strip() for c in df.columns]

    # Filter rows matching our naming convention
    pattern = re.compile(r"(upload|download)_(compressed|uncompressed)_(\w+)")
    records = []
    for _, row in df.iterrows():
        name = str(row.get("Name", ""))
        m = pattern.search(name)
        if m:
            op, mode, tier = m.groups()
            avg_col = "Average Response Time" if "Average Response Time" in df.columns else "Average (ms)"
            p95_col = "95%" if "95%" in df.columns else "95%"
            records.append({
                "operation": op,
                "mode": mode,
                "tier": tier,
                "avg_ms": float(row.get(avg_col, 0)),
                "p95_ms": float(row.get(p95_col, 0)),
            })

    if not records:
        print("  No compressed/uncompressed data found in stats CSV.")
        return

    rdf = pd.DataFrame(records)
    tier_order = ["small", "medium", "large", "xlarge"]
    rdf["tier"] = pd.Categorical(rdf["tier"], categories=tier_order, ordered=True)

    for op in rdf["operation"].unique():
        subset = rdf[rdf["operation"] == op].sort_values("tier")
        fig, ax = plt.subplots(figsize=FIGSIZE)
        sns.barplot(data=subset, x="tier", y="avg_ms", hue="mode", ax=ax)
        ax.set_title(f"{op.title()} — Avg Latency: Compressed vs Uncompressed")
        ax.set_xlabel("Document Size Tier")
        ax.set_ylabel("Average Latency (ms)")
        _save(fig, f"compressed_vs_uncompressed_{op}")


# ── 2. Scalability curve ───────────────────────────────────────────────────

def plot_scalability(merged_csv: str):
    """RPS and p95 latency vs user count from the scalability sweep."""
    df = pd.read_csv(merged_csv)
    df.columns = [c.strip() for c in df.columns]

    # Keep only 'Aggregated' rows
    agg = df[df["Name"] == "Aggregated"].copy()
    if agg.empty:
        print("  No 'Aggregated' rows found in scalability CSV.")
        return

    agg["user_count"] = agg["user_count"].astype(int)
    rps_col = "Requests/s" if "Requests/s" in agg.columns else "Current RPS"
    p95_col = "95%" if "95%" in agg.columns else "95%"

    fig, ax1 = plt.subplots(figsize=FIGSIZE)
    color_rps = "#2196F3"
    color_p95 = "#FF5722"

    ax1.plot(agg["user_count"], agg[rps_col].astype(float), "o-", color=color_rps, label="RPS")
    ax1.set_xlabel("Concurrent Users")
    ax1.set_ylabel("Requests/s", color=color_rps)
    ax1.tick_params(axis="y", labelcolor=color_rps)

    ax2 = ax1.twinx()
    ax2.plot(agg["user_count"], agg[p95_col].astype(float), "s--", color=color_p95, label="p95 latency")
    ax2.set_ylabel("p95 Latency (ms)", color=color_p95)
    ax2.tick_params(axis="y", labelcolor=color_p95)

    fig.suptitle("Scalability: RPS and p95 Latency vs Concurrent Users")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    _save(fig, "scalability_curve")


# ── 3. Size impact ─────────────────────────────────────────────────────────

def plot_size_impact(csv_path: str):
    """Latency vs document size for upload and download, compressed vs not."""
    df = pd.read_csv(csv_path)

    for op in ["upload", "download"]:
        subset = df[df["operation"] == op].copy()
        if subset.empty:
            continue

        fig, ax = plt.subplots(figsize=FIGSIZE)
        for compressed in [False, True]:
            label = "compressed" if compressed else "uncompressed"
            s = subset[subset["compressed"] == compressed]
            grouped = s.groupby("tier")["time_s"].agg(["mean", "std"]).reset_index()
            tier_order = ["small", "medium", "large", "xlarge"]
            grouped["tier"] = pd.Categorical(grouped["tier"], categories=tier_order, ordered=True)
            grouped = grouped.sort_values("tier")

            # Map tier to size in KB for x-axis
            size_map = {"small": 1, "medium": 64, "large": 1024, "xlarge": 10240}
            grouped["size_kb"] = grouped["tier"].map(size_map)

            ax.errorbar(
                grouped["size_kb"], grouped["mean"], yerr=grouped["std"],
                marker="o", label=label, capsize=4,
            )

        ax.set_xscale("log")
        ax.set_xlabel("Document Size (KB, log scale)")
        ax.set_ylabel("Latency (s)")
        ax.set_title(f"{op.title()} Latency vs Document Size")
        ax.legend()
        _save(fig, f"size_impact_{op}")


# ── 4. Sustained load timeline ──────────────────────────────────────────────

def plot_sustained(history_csv: str):
    """RPS and latency over time from Locust ``_stats_history.csv``."""
    df = pd.read_csv(history_csv)
    df.columns = [c.strip() for c in df.columns]

    # Locust history has "Timestamp" and per-request-type rows; filter "Aggregated"
    ts_col = "Timestamp" if "Timestamp" in df.columns else df.columns[0]
    if "Name" in df.columns:
        agg = df[df["Name"] == "Aggregated"].copy()
    else:
        agg = df.copy()

    if agg.empty:
        print("  No aggregated data in history CSV.")
        return

    agg[ts_col] = pd.to_datetime(agg[ts_col].astype(float), unit="s", errors="coerce")
    agg = agg.dropna(subset=[ts_col])

    rps_col = next((c for c in agg.columns if "requests/s" in c.lower() or "current rps" in c.lower()), None)
    fail_col = next((c for c in agg.columns if "failures/s" in c.lower()), None)
    p95_col = "95%" if "95%" in agg.columns else None

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    if rps_col:
        axes[0].plot(agg[ts_col], agg[rps_col].astype(float), color="#2196F3", alpha=0.8)
        axes[0].set_ylabel("Requests/s")
        axes[0].set_title("Sustained Load — RPS Over Time")

    if p95_col:
        axes[1].plot(agg[ts_col], agg[p95_col].astype(float), color="#FF5722", alpha=0.8)
        axes[1].set_ylabel("p95 Latency (ms)")
        axes[1].set_xlabel("Time")
        axes[1].set_title("Sustained Load — p95 Latency Over Time")

    fig.tight_layout()
    _save(fig, "sustained_load_timeline")


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Plot performance test results")
    parser.add_argument("--stats", help="Locust _stats.csv (for compressed vs uncompressed)")
    parser.add_argument("--scalability", help="Merged scalability CSV")
    parser.add_argument("--size-impact", help="T11 size_impact.csv")
    parser.add_argument("--sustained", help="Locust _stats_history.csv for sustained load")
    args = parser.parse_args()

    if args.stats:
        plot_compressed_vs_uncompressed(args.stats)

    if args.scalability:
        plot_scalability(args.scalability)

    if args.size_impact:
        plot_size_impact(args.size_impact)

    if args.sustained:
        plot_sustained(args.sustained)

    if not any([args.stats, args.scalability, args.size_impact, args.sustained]):
        parser.print_help()
