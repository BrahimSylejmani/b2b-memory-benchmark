"""
generate_thesis_charts.py
Reads all collected CSV stats and generates publication-quality charts for the thesis.
Run after all experiments are complete.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
CHARTS_DIR = os.path.join(RESULTS_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

SCENARIOS = ["idle", "steady", "rampup", "extended"]
SCENARIO_LABELS = {
    "idle":     "Idle (Pa ngarkesë)",
    "steady":   "Steady 50u (Ngarkesë e qëndrueshme)",
    "rampup":   "Ramp-up 0→200u (Rritje graduale)",
    "extended": "Extended 100u/30min (Ngarkesë e zgjatur)",
}
MEMORY_LAYERS = ["heap_used", "nonheap_used", "metaspace", "code_cache", "container_rss", "container_total"]
LAYER_LABELS  = ["Heap", "Non-Heap", "Metaspace", "Code Cache", "Container RSS", "Container Total"]


def load_stats(arch: str, scenario: str) -> pd.DataFrame | None:
    path = os.path.join(RESULTS_DIR, f"{arch}_{scenario}_stats.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path).set_index("metric")


# ── Chart 1: Side-by-side bar chart per scenario ─────────────────────────────
def chart_per_scenario(scenario: str):
    mono = load_stats("monolith", scenario)
    micro = load_stats("microservices", scenario)
    if mono is None or micro is None:
        print(f"  Skipping {scenario} (data missing)")
        return

    x = np.arange(len(MEMORY_LAYERS))
    width = 0.35

    mono_means = [mono.loc[m, "mean_mib"] if m in mono.index else 0 for m in MEMORY_LAYERS]
    micro_means = [micro.loc[m, "mean_mib"] if m in micro.index else 0 for m in MEMORY_LAYERS]
    mono_ci    = [mono.loc[m, "ci95_high"] - mono.loc[m, "mean_mib"] if m in mono.index else 0 for m in MEMORY_LAYERS]
    micro_ci   = [micro.loc[m, "ci95_high"] - micro.loc[m, "mean_mib"] if m in micro.index else 0 for m in MEMORY_LAYERS]

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.bar(x - width / 2, mono_means, width, yerr=mono_ci, capsize=4,
           label="Monolit Modular", color="#1976D2", alpha=0.88)
    ax.bar(x + width / 2, micro_means, width, yerr=micro_ci, capsize=4,
           label="Mikroshërbime", color="#F57C00", alpha=0.88)

    ax.set_xlabel("Shtresa e Memories", fontsize=12)
    ax.set_ylabel("Memorie (MiB)", fontsize=12)
    ax.set_title(f"Krahasimi i Konsumit të Memories\n{SCENARIO_LABELS[scenario]} (mesatare ± CI 95%)", fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(LAYER_LABELS, rotation=20, ha="right")
    ax.legend(fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f MiB"))
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, f"bar_{scenario}.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved → {path}")


# ── Chart 2: Heap consumption across all scenarios (line chart) ───────────────
def chart_heap_across_scenarios():
    scenarios_data_mono  = []
    scenarios_data_micro = []
    labels_present = []

    for sc in SCENARIOS:
        mono  = load_stats("monolith", sc)
        micro = load_stats("microservices", sc)
        if mono is None or micro is None:
            continue
        if "heap_used" not in mono.index or "heap_used" not in micro.index:
            continue
        scenarios_data_mono.append(mono.loc["heap_used", "mean_mib"])
        scenarios_data_micro.append(micro.loc["heap_used", "mean_mib"])
        labels_present.append(SCENARIO_LABELS[sc])

    if not labels_present:
        print("  Skipping heap line chart (no data)")
        return

    x = np.arange(len(labels_present))
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x, scenarios_data_mono,  "o-", color="#1976D2", linewidth=2, markersize=7, label="Monolit Modular")
    ax.plot(x, scenarios_data_micro, "s-", color="#F57C00", linewidth=2, markersize=7, label="Mikroshërbime")
    ax.fill_between(x, scenarios_data_mono,  alpha=0.1, color="#1976D2")
    ax.fill_between(x, scenarios_data_micro, alpha=0.1, color="#F57C00")

    ax.set_xticks(x)
    ax.set_xticklabels(labels_present, rotation=15, ha="right", fontsize=10)
    ax.set_ylabel("Heap i Përdorur (MiB)", fontsize=12)
    ax.set_title("Konsumi i Heap-it JVM nëpër Skenare\nMonolit vs Mikroshërbime", fontsize=13)
    ax.legend(fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f MiB"))
    ax.grid(linestyle="--", alpha=0.4)
    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, "heap_across_scenarios.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved → {path}")


# ── Chart 3: Container RSS comparison (the cAdvisor key metric) ───────────────
def chart_rss_comparison():
    mono_vals, micro_vals, sc_labels = [], [], []

    for sc in SCENARIOS:
        mono  = load_stats("monolith", sc)
        micro = load_stats("microservices", sc)
        if mono is None or micro is None:
            continue
        mono_vals.append(mono.loc["container_rss", "mean_mib"] if "container_rss" in mono.index else 0)
        micro_vals.append(micro.loc["container_rss", "mean_mib"] if "container_rss" in micro.index else 0)
        sc_labels.append(SCENARIO_LABELS[sc])

    if not sc_labels:
        return

    x = np.arange(len(sc_labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width / 2, mono_vals,  width, label="Monolit - Container RSS", color="#1976D2", alpha=0.88)
    ax.bar(x + width / 2, micro_vals, width, label="Mikroshërbime - Container RSS (total)", color="#F57C00", alpha=0.88)
    ax.set_xticks(x)
    ax.set_xticklabels(sc_labels, rotation=15, ha="right", fontsize=10)
    ax.set_ylabel("Container RSS (MiB)", fontsize=12)
    ax.set_title("Container RSS Memory (cAdvisor)\nMonolit vs Mikroshërbime nëpër Skenare", fontsize=13)
    ax.legend(fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f MiB"))
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, "rss_comparison.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved → {path}")


# ── Table: Full statistics for thesis ─────────────────────────────────────────
def build_thesis_table():
    rows = []
    for sc in SCENARIOS:
        for arch in ["monolith", "microservices"]:
            df = load_stats(arch, sc)
            if df is None:
                continue
            for m in MEMORY_LAYERS:
                if m not in df.index:
                    continue
                row = df.loc[m]
                rows.append({
                    "Skenari": SCENARIO_LABELS[sc],
                    "Arkitektura": "Monolit" if arch == "monolith" else "Mikroshërbime",
                    "Metrika": m,
                    "Mesatarja (MiB)": round(row["mean_mib"], 1),
                    "Min (MiB)":  round(row["min_mib"], 1),
                    "Max (MiB)":  round(row["max_mib"], 1),
                    "StdDev":     round(row["std_mib"], 1),
                    "CI95 ±":     round(row["ci95_high"] - row["mean_mib"], 1),
                })

    if not rows:
        print("  No data for thesis table yet.")
        return

    out = pd.DataFrame(rows)
    path = os.path.join(RESULTS_DIR, "thesis_full_table.csv")
    out.to_csv(path, index=False)
    print(f"  Saved full thesis table → {path}")
    print(out.to_string(index=False))


if __name__ == "__main__":
    print("Generating thesis charts and tables...")
    for sc in SCENARIOS:
        print(f"\n── Scenario: {sc} ──")
        chart_per_scenario(sc)
    print("\n── Cross-scenario charts ──")
    chart_heap_across_scenarios()
    chart_rss_comparison()
    print("\n── Full thesis table ──")
    build_thesis_table()
    print(f"\nAll output saved to: {CHARTS_DIR}")
