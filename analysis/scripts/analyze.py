"""
B2B Memory Benchmark - Statistical Analysis
Collects metrics from Prometheus, computes statistics, generates graphs and tables.
Run after each experiment: python analyze.py --arch monolith --scenario steady --run 1
"""

import argparse
import json
import os
import time
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import requests
from scipy import stats

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "results")

# Memory metric queries per architecture
MONOLITH_QUERIES = {
    "heap_used":       'jvm_memory_used_bytes{job="monolith", area="heap"}',
    "heap_committed":  'jvm_memory_committed_bytes{job="monolith", area="heap"}',
    "nonheap_used":    'jvm_memory_used_bytes{job="monolith", area="nonheap"}',
    "metaspace":       'jvm_memory_used_bytes{job="monolith", id="Metaspace"}',
    "code_cache":      'jvm_memory_used_bytes{job="monolith", id="CodeCache"}',
    "container_rss":   'container_memory_rss{name="monolith-app"}',
    "container_total": 'container_memory_usage_bytes{name="monolith-app"}',
    "gc_count":        'increase(jvm_gc_pause_seconds_count{job="monolith"}[5m])',
}

MICROSERVICES_QUERIES = {
    "heap_used":       'sum(jvm_memory_used_bytes{area="heap"})',
    "heap_committed":  'sum(jvm_memory_committed_bytes{area="heap"})',
    "nonheap_used":    'sum(jvm_memory_used_bytes{area="nonheap"})',
    "metaspace":       'sum(jvm_memory_used_bytes{id="Metaspace"})',
    "code_cache":      'sum(jvm_memory_used_bytes{id="CodeCache"})',
    "container_rss":   'sum(container_memory_rss{name=~"partner-service|order-service|invoice-service"})',
    "container_total": 'sum(container_memory_usage_bytes{name=~"partner-service|order-service|invoice-service"})',
    "gc_count":        'sum(increase(jvm_gc_pause_seconds_count[5m]))',
}


def query_prometheus_range(query: str, start: datetime, end: datetime, step: str = "5s") -> pd.DataFrame:
    """Fetch a range query from Prometheus and return as DataFrame."""
    resp = requests.get(
        f"{PROMETHEUS_URL}/api/v1/query_range",
        params={
            "query": query,
            "start": start.isoformat() + "Z",
            "end": end.isoformat() + "Z",
            "step": step,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    results = data.get("data", {}).get("result", [])
    if not results:
        return pd.DataFrame(columns=["timestamp", "value"])
    rows = []
    for series in results:
        for ts, val in series["values"]:
            rows.append({"timestamp": datetime.utcfromtimestamp(float(ts)), "value": float(val)})
    return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)


def compute_stats(series: pd.Series) -> dict:
    """Compute mean, min, max, stddev, 95% CI for a numeric series."""
    n = len(series)
    mean = series.mean()
    std = series.std(ddof=1)
    se = std / np.sqrt(n)
    ci95 = stats.t.ppf(0.975, df=n - 1) * se if n > 1 else 0
    return {
        "n": n,
        "mean": mean,
        "min": series.min(),
        "max": series.max(),
        "std": std,
        "ci95": ci95,
        "ci95_low": mean - ci95,
        "ci95_high": mean + ci95,
    }


def bytes_to_mib(val: float) -> float:
    return val / (1024 ** 2)


def collect_run(arch: str, scenario: str, run: int, duration_minutes: int = 10) -> dict:
    """
    Collect metric data for one experiment run.
    Skips first 5 minutes (warmup), then collects 'duration_minutes'.
    """
    warmup = timedelta(minutes=5)
    now = datetime.utcnow()
    start = now - timedelta(minutes=duration_minutes) - warmup + warmup
    end = now

    queries = MONOLITH_QUERIES if arch == "monolith" else MICROSERVICES_QUERIES
    run_data = {}
    for metric, query in queries.items():
        df = query_prometheus_range(query, start, end)
        if df.empty:
            print(f"  WARNING: no data for {metric}")
            run_data[metric] = pd.Series(dtype=float)
        else:
            run_data[metric] = df["value"].apply(bytes_to_mib) if "gc" not in metric else df["value"]
    return run_data


def aggregate_runs(all_runs: list[dict]) -> dict:
    """Combine 5 repetition runs into aggregated stats per metric."""
    metrics = all_runs[0].keys()
    aggregated = {}
    for metric in metrics:
        combined = pd.concat([r[metric] for r in all_runs if not r[metric].empty])
        aggregated[metric] = compute_stats(combined)
    return aggregated


def save_csv(stats_dict: dict, arch: str, scenario: str):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    rows = []
    for metric, s in stats_dict.items():
        rows.append({
            "architecture": arch,
            "scenario": scenario,
            "metric": metric,
            "mean_mib": round(s["mean"], 2),
            "min_mib": round(s["min"], 2),
            "max_mib": round(s["max"], 2),
            "std_mib": round(s["std"], 2),
            "ci95_low": round(s["ci95_low"], 2),
            "ci95_high": round(s["ci95_high"], 2),
        })
    df = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, f"{arch}_{scenario}_stats.csv")
    df.to_csv(path, index=False)
    print(f"Saved stats → {path}")
    return df


def plot_comparison(monolith_stats: dict, micro_stats: dict, scenario: str):
    """Bar chart comparing monolith vs microservices for each memory layer."""
    metrics = ["heap_used", "nonheap_used", "metaspace", "code_cache", "container_rss", "container_total"]
    labels = ["Heap", "Non-Heap", "Metaspace", "Code Cache", "Container RSS", "Container Total"]

    mono_means = [monolith_stats[m]["mean"] for m in metrics]
    mono_ci = [monolith_stats[m]["ci95"] for m in metrics]
    micro_means = [micro_stats[m]["mean"] for m in metrics]
    micro_ci = [micro_stats[m]["ci95"] for m in metrics]

    x = np.arange(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))
    bars1 = ax.bar(x - width / 2, mono_means, width, yerr=mono_ci, capsize=4,
                   label="Monolith", color="#2196F3", alpha=0.85)
    bars2 = ax.bar(x + width / 2, micro_means, width, yerr=micro_ci, capsize=4,
                   label="Microservices", color="#FF5722", alpha=0.85)

    ax.set_xlabel("Memory Layer")
    ax.set_ylabel("Memory (MiB)")
    ax.set_title(f"Memory Consumption: Monolith vs Microservices\nScenario: {scenario} (mean ± 95% CI)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.legend()
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f MiB"))
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, f"comparison_{scenario}.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved chart → {path}")


def plot_memory_over_time(time_series: pd.Series, arch: str, scenario: str, metric: str):
    """Line chart of a single memory metric over time."""
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(time_series.index, time_series.values, linewidth=1.5, color="#1565C0")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Memory (MiB)")
    ax.set_title(f"{arch.capitalize()} - {metric} over time\nScenario: {scenario}")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f MiB"))
    ax.grid(linestyle="--", alpha=0.5)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, f"{arch}_{scenario}_{metric}_timeline.png")
    plt.savefig(path, dpi=150)
    plt.close()


def build_comparison_table(monolith_csv: str, micro_csv: str, scenario: str):
    """Generate a combined comparison table (for thesis) from two CSVs."""
    mono = pd.read_csv(monolith_csv)
    micro = pd.read_csv(micro_csv)
    merged = mono.merge(micro, on="metric", suffixes=("_monolith", "_micro"))
    merged["overhead_pct"] = ((merged["mean_mib_micro"] - merged["mean_mib_monolith"])
                               / merged["mean_mib_monolith"] * 100).round(1)
    path = os.path.join(OUTPUT_DIR, f"comparison_table_{scenario}.csv")
    merged.to_csv(path, index=False)
    print(f"Saved comparison table → {path}")
    print(merged[["metric", "mean_mib_monolith", "mean_mib_micro", "overhead_pct"]].to_string(index=False))
    return merged


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="B2B Memory Benchmark Analyzer")
    parser.add_argument("--arch", choices=["monolith", "microservices"], required=True)
    parser.add_argument("--scenario", choices=["idle", "steady", "rampup", "extended"], required=True)
    parser.add_argument("--run", type=int, default=1, help="Run number (1-5)")
    parser.add_argument("--duration", type=int, default=10, help="Measurement duration in minutes")
    parser.add_argument("--compare", action="store_true", help="Build comparison table from saved CSVs")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.compare:
        mono_csv = os.path.join(OUTPUT_DIR, f"monolith_{args.scenario}_stats.csv")
        micro_csv = os.path.join(OUTPUT_DIR, f"microservices_{args.scenario}_stats.csv")
        build_comparison_table(mono_csv, micro_csv, args.scenario)
    else:
        print(f"Collecting run {args.run} | arch={args.arch} | scenario={args.scenario}")
        print("Waiting 5 minutes for warmup to complete..." if args.run == 1 else "")
        run_data = collect_run(args.arch, args.scenario, args.run, args.duration)

        # Save raw run data
        raw_path = os.path.join(OUTPUT_DIR, f"{args.arch}_{args.scenario}_run{args.run}.json")
        serializable = {k: v.tolist() for k, v in run_data.items()}
        with open(raw_path, "w") as f:
            json.dump(serializable, f)
        print(f"Saved raw data → {raw_path}")

        # If all 5 runs collected, aggregate
        run_files = [
            os.path.join(OUTPUT_DIR, f"{args.arch}_{args.scenario}_run{i}.json")
            for i in range(1, 6)
        ]
        if all(os.path.exists(p) for p in run_files):
            print("All 5 runs collected — computing aggregate statistics...")
            all_runs = []
            for p in run_files:
                with open(p) as f:
                    raw = json.load(f)
                all_runs.append({k: pd.Series(v) for k, v in raw.items()})
            agg = aggregate_runs(all_runs)
            df = save_csv(agg, args.arch, args.scenario)
            print(df.to_string(index=False))
        else:
            remaining = sum(1 for p in run_files if not os.path.exists(p))
            print(f"Run {args.run} saved. {remaining} more run(s) needed before aggregation.")
