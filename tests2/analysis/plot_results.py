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
    tier_order = ["small", "medium", "large", "xlarge", "xxl", "xxxl"]
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
            tier_order = ["small", "medium", "large", "xlarge", "xxl", "xxxl"]
            grouped["tier"] = pd.Categorical(grouped["tier"], categories=tier_order, ordered=True)
            grouped = grouped.sort_values("tier")

            # Map tier to size in KB for x-axis
            size_map = {"small": 1, "medium": 64, "large": 1024, "xlarge": 10240, "xxl": 51200, "xxxl": 102400}
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


# ── 5. Compression algorithm comparison ────────────────────────────────────

def plot_compression_comparison(csv_path: str):
    """Generate plots from the T13 compression comparison CSV.

    Produces:
    - Grouped bar chart: compression ratio by method × level for each tier.
    - Compression speed: time to compress vs ratio scatter.
    - Upload latency comparison across methods.
    """
    df = pd.read_csv(csv_path)

    tier_order = ["small", "medium", "large", "xlarge", "xxl", "xxxl"]
    available_tiers = [t for t in tier_order if t in df["tier"].unique()]
    df["tier"] = pd.Categorical(df["tier"], categories=available_tiers, ordered=True)

    # Filter out "none" (baseline) for compression-specific plots
    comp_df = df[df["method"] != "none"].copy()
    comp_df["method_level"] = comp_df["method"] + " L" + comp_df["level"].astype(str)

    # ---- Plot 1: Compression ratio by method×level, grouped by tier ----
    fig, ax = plt.subplots(figsize=(14, 7))
    grouped = comp_df.groupby(["tier", "method_level"])["ratio"].mean().reset_index()
    pivot = grouped.pivot(index="tier", columns="method_level", values="ratio")
    # Reorder columns: gzip L1..9, brotli L1..11, zstd L1..9
    col_order = []
    for m in ["gzip", "brotli", "zstd"]:
        col_order.extend([c for c in sorted(pivot.columns) if c.startswith(m)])
    pivot = pivot[[c for c in col_order if c in pivot.columns]]
    pivot.plot(kind="bar", ax=ax, width=0.85)
    ax.set_title("Compression Ratio by Algorithm & Level (lower = better)")
    ax.set_xlabel("Document Size Tier")
    ax.set_ylabel("Compression Ratio (compressed / original)")
    ax.legend(title="Method & Level", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
    fig.tight_layout()
    _save(fig, "compression_ratio_comparison")

    # ---- Plot 2: Compression time vs ratio (scatter) ----
    fig, ax = plt.subplots(figsize=(12, 7))
    methods = comp_df["method"].unique()
    markers = {"gzip": "o", "brotli": "s", "zstd": "^"}
    for method in methods:
        m_df = comp_df[comp_df["method"] == method]
        for level in sorted(m_df["level"].unique()):
            sub = m_df[m_df["level"] == level]
            avg = sub.groupby("tier").agg(
                ratio=("ratio", "mean"),
                compress_time=("compress_time_s", "mean"),
                size_bytes=("size_bytes", "first"),
            ).reset_index()
            marker = markers.get(method, "D")
            ax.scatter(
                avg["ratio"], avg["compress_time"],
                marker=marker, s=avg["size_bytes"] / avg["size_bytes"].max() * 300 + 30,
                label=f"{method} L{level}", alpha=0.7,
            )
    ax.set_xlabel("Compression Ratio (lower = smaller)")
    ax.set_ylabel("Compression Time (s)")
    ax.set_title("Compression Speed vs Ratio (size ∝ document size)")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    fig.tight_layout()
    _save(fig, "compression_speed_vs_ratio")

    # ---- Plot 3: Upload latency comparison (bar, per tier) ----
    # Compare uncompressed baseline vs best level of each method
    baseline = df[df["method"] == "none"].groupby("tier")["upload_time_s"].mean()
    fig, ax = plt.subplots(figsize=(14, 7))
    x_labels = list(baseline.index)
    x = range(len(x_labels))
    width = 0.18
    offset = 0

    bars = ax.bar([i + offset * width for i in x], baseline.values, width, label="none (raw)", color="#9E9E9E")
    offset += 1

    colors = {"gzip": "#2196F3", "brotli": "#FF9800", "zstd": "#4CAF50"}
    for method in ["gzip", "brotli", "zstd"]:
        m_df = comp_df[comp_df["method"] == method]
        if m_df.empty:
            continue
        # Use the middle level for each method
        levels = sorted(m_df["level"].unique())
        mid_level = levels[len(levels) // 2]
        avg = m_df[m_df["level"] == mid_level].groupby("tier")["upload_time_s"].mean()
        vals = [avg.get(t, 0) for t in x_labels]
        ax.bar([i + offset * width for i in x], vals, width,
               label=f"{method} L{mid_level}", color=colors.get(method, "#607D8B"))
        offset += 1

    ax.set_xticks([i + width * 1.5 for i in x])
    ax.set_xticklabels(x_labels)
    ax.set_xlabel("Document Size Tier")
    ax.set_ylabel("Avg Upload Latency (s)")
    ax.set_title("Upload Latency: Raw vs Compressed (mid-level)")
    ax.legend()
    fig.tight_layout()
    _save(fig, "compression_upload_latency")

    # ---- Plot 4: Per-tier compression ratio line chart ----
    fig, axes = plt.subplots(1, min(len(available_tiers), 3), figsize=(6 * min(len(available_tiers), 3), 5),
                             sharey=True, squeeze=False)
    # Show at most 3 representative tiers
    show_tiers = [available_tiers[0], available_tiers[len(available_tiers)//2], available_tiers[-1]]
    for idx, tier in enumerate(show_tiers):
        ax = axes[0][idx]
        t_df = comp_df[comp_df["tier"] == tier]
        for method in ["gzip", "brotli", "zstd"]:
            m_df = t_df[t_df["method"] == method]
            if m_df.empty:
                continue
            avg = m_df.groupby("level")["ratio"].mean().reset_index()
            ax.plot(avg["level"], avg["ratio"], "o-", label=method, color=colors.get(method))
        ax.set_title(f"Tier: {tier}")
        ax.set_xlabel("Compression Level")
        if idx == 0:
            ax.set_ylabel("Compression Ratio")
        ax.legend(fontsize=8)
    fig.suptitle("Compression Ratio vs Level by Tier", y=1.02)
    fig.tight_layout()
    _save(fig, "compression_ratio_by_level")


# ── 6. Max throughput / breaking point ──────────────────────────────────────

def plot_max_throughput(merged_csv: str):
    """Generate plots from the T14 max-throughput sweep.

    Produces:
    - RPS vs concurrent users (with error rate overlay).
    - p95 latency vs concurrent users.
    - Combined dashboard view.
    """
    df = pd.read_csv(merged_csv)
    df.columns = [c.strip() for c in df.columns]

    agg = df[df["Name"].str.strip() == "Aggregated"].copy()
    if agg.empty:
        print("  No 'Aggregated' rows found in max throughput CSV.")
        return

    agg["user_count"] = agg["user_count"].astype(int)
    rps_col = "Requests/s" if "Requests/s" in agg.columns else "Current RPS"
    p95_col = "95%" if "95%" in agg.columns else "95%"
    req_col = "Request Count" if "Request Count" in agg.columns else "# Requests"
    fail_col = "Failure Count" if "Failure Count" in agg.columns else "# Failures"

    agg["rps"] = agg[rps_col].astype(float)
    agg["p95"] = agg[p95_col].astype(float)
    agg["total_req"] = agg[req_col].astype(int)
    agg["total_fail"] = agg[fail_col].astype(int)
    agg["error_pct"] = agg["total_fail"] / agg["total_req"] * 100

    users = agg["user_count"].values

    # Detect breaking point
    baseline_p95 = agg["p95"].iloc[0]
    breaking_idx = None
    for i, row in agg.iterrows():
        if row["error_pct"] > 1.0 or row["p95"] > baseline_p95 * 3:
            breaking_idx = row["user_count"]
            break

    # ---- Plot 1: RPS + Error% vs Users ----
    fig, ax1 = plt.subplots(figsize=FIGSIZE)
    color_rps = "#2196F3"
    color_err = "#F44336"

    ax1.plot(users, agg["rps"], "o-", color=color_rps, linewidth=2, markersize=8, label="RPS")
    ax1.set_xlabel("Concurrent Users")
    ax1.set_ylabel("Requests/s", color=color_rps)
    ax1.tick_params(axis="y", labelcolor=color_rps)

    ax2 = ax1.twinx()
    ax2.plot(users, agg["error_pct"], "s--", color=color_err, linewidth=1.5, markersize=6, label="Error %")
    ax2.set_ylabel("Error Rate (%)", color=color_err)
    ax2.tick_params(axis="y", labelcolor=color_err)

    if breaking_idx is not None:
        ax1.axvline(x=breaking_idx, color="#FF9800", linestyle=":", linewidth=2,
                     label=f"Breaking point ({breaking_idx} users)")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
    fig.suptitle("Max Throughput: RPS & Error Rate vs Concurrent Users")
    fig.tight_layout()
    _save(fig, "max_throughput_rps")

    # ---- Plot 2: p95 Latency vs Users ----
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(users, agg["p95"], "o-", color="#FF5722", linewidth=2, markersize=8)
    if breaking_idx is not None:
        ax.axvline(x=breaking_idx, color="#FF9800", linestyle=":", linewidth=2,
                    label=f"Breaking point ({breaking_idx} users)")
    ax.set_xlabel("Concurrent Users")
    ax.set_ylabel("p95 Latency (ms)")
    ax.set_title("Max Throughput: p95 Latency vs Concurrent Users")
    if breaking_idx:
        ax.legend()
    fig.tight_layout()
    _save(fig, "max_throughput_latency")

    # ---- Plot 3: Combined dashboard ----
    fig, (ax_rps, ax_lat, ax_err) = plt.subplots(3, 1, figsize=(12, 12), sharex=True)

    ax_rps.plot(users, agg["rps"], "o-", color="#2196F3", linewidth=2)
    ax_rps.set_ylabel("Requests/s")
    ax_rps.set_title("Throughput")
    ax_rps.grid(True, alpha=0.3)

    ax_lat.plot(users, agg["p95"], "s-", color="#FF5722", linewidth=2)
    ax_lat.set_ylabel("p95 Latency (ms)")
    ax_lat.set_title("Latency")
    ax_lat.grid(True, alpha=0.3)

    ax_err.bar(users, agg["error_pct"], color="#F44336", alpha=0.7, width=max(1, (users[-1] - users[0]) / len(users) * 0.6))
    ax_err.set_ylabel("Error Rate (%)")
    ax_err.set_xlabel("Concurrent Users")
    ax_err.set_title("Errors")
    ax_err.grid(True, alpha=0.3)

    if breaking_idx is not None:
        for a in (ax_rps, ax_lat, ax_err):
            a.axvline(x=breaking_idx, color="#FF9800", linestyle=":", linewidth=2, alpha=0.8)

    fig.suptitle("Max Throughput Dashboard", fontsize=14, y=1.01)
    fig.tight_layout()
    _save(fig, "max_throughput_dashboard")


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Plot performance test results")
    parser.add_argument("--stats", help="Locust _stats.csv (for compressed vs uncompressed)")
    parser.add_argument("--scalability", help="Merged scalability CSV")
    parser.add_argument("--size-impact", help="T11 size_impact.csv")
    parser.add_argument("--sustained", help="Locust _stats_history.csv for sustained load")
    parser.add_argument("--compression", help="T13 compression_comparison.csv")
    parser.add_argument("--max-throughput", help="T14 max_throughput_merged.csv")
    args = parser.parse_args()

    if args.stats:
        plot_compressed_vs_uncompressed(args.stats)

    if args.scalability:
        plot_scalability(args.scalability)

    if args.size_impact:
        plot_size_impact(args.size_impact)

    if args.sustained:
        plot_sustained(args.sustained)

    if args.compression:
        plot_compression_comparison(args.compression)

    if args.max_throughput:
        plot_max_throughput(args.max_throughput)

    if not any([args.stats, args.scalability, args.size_impact, args.sustained,
                args.compression, args.max_throughput]):
        parser.print_help()
