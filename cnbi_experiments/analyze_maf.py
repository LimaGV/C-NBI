"""Paired, cardinality-controlled analysis of the completed MaF benchmark campaign."""
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, wilcoxon
from statsmodels.stats.multitest import multipletests


SOURCE = Path("experimental_results/full_campaign/MaF_benchmarks_results.csv")
OUTPUT = Path("experimental_results/full_campaign/maf_analysis")
METHODS = ["CNBI_spectral", "VRF-NBI", "NSGA-III", "MOEA/D"]
COLORS = {
    "CNBI_spectral": "#0072B2", "VRF-NBI": "#D55E00",
    "NSGA-III": "#009E73", "MOEA/D": "#CC79A7",
}


def valid_paired(data, comparison):
    frame = data[(data.comparison == comparison) & (data.n > 0) &
                 data.IGD.notna() & data.HV.notna()].copy()
    counts = frame.groupby(["scenario_id", "seed"]).method.nunique()
    blocks = counts[counts.eq(len(METHODS))].index
    return frame.set_index(["scenario_id", "seed"]).loc[blocks].reset_index()


def paired_statistics(frame):
    summaries, pairs = [], []
    for metric, ascending in (("IGD", True), ("HV", False)):
        pivot = frame.pivot(index=["scenario_id", "seed"], columns="method", values=metric)[METHODS]
        ranks = pivot.rank(axis=1, ascending=ascending, method="average")
        wins = ranks.eq(ranks.min(axis=1), axis=0).sum()
        friedman = friedmanchisquare(*[pivot[method] for method in METHODS])
        for method in METHODS:
            values = pivot[method]
            summaries.append({
                "metric": metric, "method": method, "blocks": len(pivot),
                "mean": values.mean(), "median": values.median(),
                "mean_rank": ranks[method].mean(), "best_or_tied_blocks": int(wins[method]),
                "friedman_statistic": friedman.statistic, "friedman_p": friedman.pvalue,
            })
        pending = []
        for left, right in combinations(METHODS, 2):
            difference = pivot[left] - pivot[right]
            test = wilcoxon(difference, zero_method="wilcox", alternative="two-sided")
            pending.append({
                "metric": metric, "left": left, "right": right,
                "median_left_minus_right": difference.median(),
                "left_lower_blocks": int((difference < 0).sum()),
                "left_higher_blocks": int((difference > 0).sum()),
                "p_raw": test.pvalue,
            })
        adjusted = multipletests([row["p_raw"] for row in pending], method="holm")[1]
        for row, p_holm in zip(pending, adjusted):
            row["p_holm"] = p_holm
            pairs.append(row)
    return pd.DataFrame(summaries), pd.DataFrame(pairs)


def plot_scenario_medians(frame, metric):
    med = frame.groupby(["scenario_id", "method", "m"], as_index=False)[metric].median()
    med["family"] = med.scenario_id.str.extract(r"(maf\d+)", expand=False).str.upper()
    families = ["MAF8", "MAF9", "MAF13"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), layout="constrained")
    for ax, family in zip(axes, families):
        part = med[med.family == family]
        for method in METHODS:
            line = part[part.method == method].sort_values("m")
            ax.plot(line.m, line[metric], marker="o", linewidth=1.7,
                    color=COLORS[method], label=method)
        ax.set(title=family, xlabel="Número de objetivos (m)", ylabel=f"Mediana do {metric}")
        if metric == "IGD":
            ax.set_yscale("log")
        ax.grid(alpha=.2)
    axes[-1].legend(frameon=False, fontsize=8)
    fig.suptitle(f"{metric} com a mesma quantidade de pontos", fontsize=14, fontweight="bold")
    fig.savefig(OUTPUT / f"{metric}_mediana_por_MaF.png", dpi=200)
    plt.close(fig)


def plot_ranks(summary):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True, layout="constrained")
    for ax, metric in zip(axes, ("IGD", "HV")):
        part = summary[summary.metric == metric].set_index("method").loc[METHODS]
        ax.bar(METHODS, part.mean_rank, color=[COLORS[m] for m in METHODS])
        ax.axhline(2.5, color="#777777", linestyle="--", linewidth=1)
        ax.set(title=metric, ylabel="Posição média (1 é melhor)", ylim=(1, 4))
        ax.tick_params(axis="x", rotation=20)
        ax.grid(axis="y", alpha=.2)
    fig.suptitle("Posição média nos 125 blocos válidos", fontsize=14, fontweight="bold")
    fig.savefig(OUTPUT / "posicao_media_metodos.png", dpi=200)
    plt.close(fig)


def plot_cardinality_and_cost(data, equal):
    blocks = equal.groupby(["scenario_id", "seed"]).n.first()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
    axes[0].hist(blocks, bins=np.arange(.5, blocks.max()+1.5), color="#5B9BD5", edgecolor="white")
    axes[0].set(title="Pontos usados na comparação igualada", xlabel="Pontos por método",
                ylabel="Número de blocos")
    complete = valid_paired(data, "complete")
    times = complete.groupby("method").seconds.median().reindex(METHODS)
    axes[1].bar(METHODS, times, color=[COLORS[m] for m in METHODS])
    axes[1].set_yscale("log")
    axes[1].set(title="Tempo mediano da frente completa", xlabel="Método", ylabel="Segundos (escala log)")
    axes[1].tick_params(axis="x", rotation=20)
    for ax in axes:
        ax.grid(axis="y", alpha=.2)
    fig.savefig(OUTPUT / "cardinalidade_e_tempo.png", dpi=200)
    plt.close(fig)


def run():
    OUTPUT.mkdir(exist_ok=True)
    data = pd.read_csv(SOURCE)
    equal = valid_paired(data, "equal_cardinality")
    complete = valid_paired(data, "complete")
    summary, pairwise = paired_statistics(equal)
    summary.to_csv(OUTPUT / "paired_summary.csv", index=False)
    pairwise.to_csv(OUTPUT / "pairwise_wilcoxon_holm.csv", index=False)
    scenario = equal.groupby(["scenario_id", "method"])[["IGD", "HV", "n"]].agg(
        ["count", "mean", "median", "std"]
    )
    scenario.columns = [f"{metric}_{stat}" for metric, stat in scenario.columns]
    scenario.reset_index().to_csv(OUTPUT / "scenario_summary.csv", index=False)
    cost = complete.groupby("method")[["seconds", "evaluations", "n"]].agg(
        ["mean", "median", "std"]
    )
    cost.columns = [f"{metric}_{stat}" for metric, stat in cost.columns]
    cost.reset_index().to_csv(OUTPUT / "cost_and_front_size.csv", index=False)

    all_equal = data[data.comparison == "equal_cardinality"]
    quality = pd.DataFrame([{
        "requested_blocks": 130,
        "valid_paired_blocks": equal.groupby(["scenario_id", "seed"]).ngroups,
        "blocked_blocks": 130 - equal.groupby(["scenario_id", "seed"]).ngroups,
        "blocks_with_one_point": int(equal.groupby(["scenario_id", "seed"]).n.first().eq(1).sum()),
        "empty_complete_fronts": int(((data.comparison == "complete") & (data.n == 0)).sum()),
        "equal_rows_pass": int(all_equal.cardinality_status.eq("PASS").sum()),
    }])
    quality.to_csv(OUTPUT / "data_quality.csv", index=False)

    plot_scenario_medians(equal, "IGD")
    plot_scenario_medians(equal, "HV")
    plot_ranks(summary)
    plot_cardinality_and_cost(data, equal)
    print(f"Análise MaF gravada em {OUTPUT}")


if __name__ == "__main__":
    run()
