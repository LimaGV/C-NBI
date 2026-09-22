"""Create the final cardinality curves and the explicit MaF13 scale audit.

This module only reads saved fronts.  It never reruns an optimizer and never
overwrites the campaign tables that contain the primary, native-front results.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from .pilot import metrics
from .reuse import METRICS


METHODS = ("CNBI_spectral", "VRF-NBI", "NSGA-III", "MOEA/D")
COLORS = {
    "CNBI_spectral": "#0072B2",
    "VRF-NBI": "#D55E00",
    "NSGA-III": "#009E73",
    "MOEA/D": "#CC79A7",
}
LABELS = {"CNBI_spectral": "CNBI", "VRF-NBI": "VRF-NBI",
          "NSGA-III": "NSGA-III", "MOEA/D": "MOEA/D"}


def _front_path(root: Path, scenario: str, seed: int, method: str) -> Path:
    return root / f"{scenario}_seed{seed}_{method.replace('/', '_')}_front.npz"


def cardinality_curves(doe: Path, cardinalities=(2, 5, 10, 20)) -> pd.DataFrame:
    """Re-evaluate saved DOE fronts at fixed, declared cardinalities.

    A scenario/seed contributes at a cardinality only when every method has at
    least that many points.  Thus no method is silently allowed to contribute
    to a different comparison block.
    """
    output = doe / "cardinality_curves"
    output.mkdir(exist_ok=True)
    complete = pd.read_csv(doe / "campaign_complete.csv")
    complete = complete[complete.scenario_id.str.startswith("doe_")]
    rows = []
    for (scenario, seed), block in complete.groupby(["scenario_id", "seed"]):
        if set(block.method) != set(METHODS):
            continue
        ref = np.load(doe / f"{scenario}_reference.npz")
        rn = (ref["F"] - ref["ideal"]) / ref["amplitude"]
        fronts = {}
        for method in METHODS:
            f = np.load(_front_path(doe, scenario, int(seed), method))["F"]
            fronts[method] = (f - ref["ideal"]) / ref["amplitude"]
        for n_points in cardinalities:
            if any(len(f) < n_points for f in fronts.values()):
                continue
            block_metrics = {}
            for method, f in fronts.items():
                reduced = (METRICS["hierarchical_equal_cardinality"](f, n_points)
                           if len(f) > n_points else f)
                value = metrics(reduced, rn, int(seed))
                block_metrics[method] = value
                rows.append(dict(scenario_id=scenario, seed=int(seed),
                                 method=method, points=n_points,
                                 original_points=len(f), **value))
            best_igd = min(v["IGD"] for v in block_metrics.values())
            best_hv = max(v["HV"] for v in block_metrics.values())
            for row in rows[-len(METHODS):]:
                row["IGD_ratio_to_best"] = row["IGD"] / max(best_igd, 1e-15)
                row["HV_ratio_to_best"] = best_hv / max(row["HV"], 1e-15)

    values = pd.DataFrame(rows)
    values.to_csv(output / "cardinality_metrics.csv", index=False)
    scenario_summary = values.groupby(
        ["scenario_id", "method", "points"], as_index=False
    ).agg(runs=("seed", "size"), IGD_median=("IGD", "median"),
          IGD_min=("IGD", "min"), IGD_max=("IGD", "max"),
          HV_median=("HV", "median"), HV_min=("HV", "min"),
          HV_max=("HV", "max"))
    scenario_summary.to_csv(output / "cardinality_summary_by_scenario.csv", index=False)
    aggregate = values.groupby(["method", "points"], as_index=False).agg(
        blocks=("seed", "size"), scenarios=("scenario_id", "nunique"),
        IGD_relative_median=("IGD_ratio_to_best", "median"),
        HV_relative_median=("HV_ratio_to_best", "median"))
    aggregate.to_csv(output / "cardinality_summary_relative.csv", index=False)

    for metric, ylabel, filename in (
        ("IGD_median", "IGD mediano (menor é melhor)", "IGD_por_cenario.png"),
        ("HV_median", "HV mediano (maior é melhor)", "HV_por_cenario.png"),
    ):
        scenarios = sorted(scenario_summary.scenario_id.unique())
        fig, axes = plt.subplots(5, 6, figsize=(18, 14), layout="constrained")
        axes = axes.ravel()
        for ax, scenario in zip(axes, scenarios):
            part = scenario_summary[scenario_summary.scenario_id.eq(scenario)]
            for method in METHODS:
                line = part[part.method.eq(method)].sort_values("points")
                ax.plot(line.points, line[metric], marker="o", linewidth=1.25,
                        markersize=3, color=COLORS[method], label=LABELS[method])
            ax.set_title(scenario.replace("doe_", ""), fontsize=8)
            ax.set_xticks(cardinalities)
            ax.grid(alpha=.2)
        for ax in axes[len(scenarios):]:
            ax.axis("off")
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False)
        fig.supxlabel("Quantidade fixa de pontos")
        fig.supylabel(ylabel)
        fig.suptitle(f"{metric.split('_')[0]} por quantidade de pontos e cenário",
                     fontsize=15, fontweight="bold")
        fig.savefig(output / filename, dpi=200)
        plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
    for method in METHODS:
        line = aggregate[aggregate.method.eq(method)].sort_values("points")
        axes[0].plot(line.points, line.IGD_relative_median, marker="o",
                     color=COLORS[method], label=LABELS[method])
        axes[1].plot(line.points, line.HV_relative_median, marker="o",
                     color=COLORS[method], label=LABELS[method])
    axes[0].set(title="IGD relativo ao melhor do bloco",
                ylabel="Razão (1 = melhor)")
    axes[1].set(title="HV relativo ao melhor do bloco",
                ylabel="Razão (1 = melhor)")
    for ax in axes:
        ax.set_xlabel("Quantidade fixa de pontos")
        ax.set_xticks(cardinalities)
        ax.axhline(1, color="black", linewidth=.8, alpha=.5)
        ax.grid(alpha=.2)
        ax.legend(frameon=False)
    fig.suptitle("Síntese das curvas de cardinalidade")
    fig.savefig(output / "curvas_relativas_agregadas.png", dpi=200)
    plt.close(fig)

    availability = values[["scenario_id", "seed", "points"]].drop_duplicates()
    availability = availability.groupby("points", as_index=False).agg(
        paired_blocks=("seed", "size"), scenarios=("scenario_id", "nunique"))
    availability.to_csv(output / "availability.csv", index=False)
    note = """# Curvas de qualidade por quantidade de pontos

As frentes completas continuam sendo o resultado principal. Estas curvas são
uma análise de sensibilidade. Em cada quantidade, um bloco cenário/semente só
entra quando os quatro métodos possuem pontos suficientes. A redução usa o
mesmo agrupamento hierárquico da análise de cardinalidade já existente.

Os gráficos por cenário mostram os valores reais de IGD e HV. O gráfico
agregado usa a razão para o melhor método dentro do mesmo bloco, pois não é
correto tirar a média direta de HV entre problemas com números diferentes de
objetivos. Razão 1 indica o melhor resultado naquele bloco.
"""
    (output / "README.md").write_text(note, encoding="utf-8")
    return values


def maf13_scale_audit(maf: Path) -> pd.DataFrame:
    """Keep current MaF13 values and add raw/normalized point-distance detail."""
    rows = []
    complete = pd.read_csv(maf / "campaign_complete.csv")
    complete = complete[complete.scenario_id.str.startswith("maf13_")]
    for row in complete.itertuples(index=False):
        ref = np.load(maf / f"{row.scenario_id}_reference.npz")
        f = np.load(_front_path(maf, row.scenario_id, int(row.seed), row.method))["F"]
        r = ref["F"]
        fn = (f - ref["ideal"]) / ref["amplitude"]
        rn = (r - ref["ideal"]) / ref["amplitude"]
        raw_distance = cKDTree(r).query(f, k=1)[0]
        normalized_distance = cKDTree(rn).query(fn, k=1)[0]
        normalized = metrics(fn, rn, int(row.seed))
        rows.append(dict(
            scenario_id=row.scenario_id, seed=int(row.seed), m=int(row.m), n=len(f),
            IGD_current=float(row.IGD), GD_current=float(row.GD), HV_current=float(row.HV),
            IGD_raw=float(cKDTree(f).query(r, k=1)[0].mean()),
            GD_raw=float(raw_distance.mean()),
            IGD_normalized=normalized["IGD"], GD_normalized=normalized["GD"],
            HV_normalized=normalized["HV"],
            point_distance_normalized_median=float(np.median(normalized_distance)),
            point_distance_normalized_p90=float(np.quantile(normalized_distance, .90)),
            point_distance_normalized_p95=float(np.quantile(normalized_distance, .95)),
            point_distance_normalized_max=float(normalized_distance.max()),
            points_distance_above_1=int((normalized_distance > 1).sum()),
            fraction_points_distance_above_1=float((normalized_distance > 1).mean()),
            fraction_objective_values_outside_pf_range=float(
                np.mean((fn < 0) | (fn > 1))),
        ))
    values = pd.DataFrame(rows)
    values.to_csv(maf / "MAF13_METRICS_RAW_AND_NORMALIZED.csv", index=False)
    summary = values.groupby(["scenario_id", "m"], as_index=False).median(numeric_only=True)
    summary = summary.sort_values("m").reset_index(drop=True)
    summary.to_csv(maf / "MAF13_METRICS_RAW_AND_NORMALIZED_SUMMARY.csv", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), layout="constrained")
    x = summary.m
    axes[0].plot(x, summary.IGD_normalized, marker="o", color="#0072B2")
    axes[0].set(title="IGD normalizado", ylabel="Distância")
    axes[1].semilogy(x, summary.GD_normalized, marker="o", color="#D55E00")
    axes[1].set(title="GD normalizado", ylabel="Distância (escala log)")
    axes[2].semilogy(x, summary.point_distance_normalized_median, marker="o",
                    label="mediana", color="#009E73")
    axes[2].semilogy(x, summary.point_distance_normalized_p95, marker="o",
                    label="percentil 95", color="#CC79A7")
    axes[2].semilogy(x, summary.point_distance_normalized_max, marker="o",
                    label="máximo", color="#000000")
    axes[2].set(title="Distância dos pontos do CNBI à fronteira",
                ylabel="Distância normalizada")
    axes[2].legend(frameon=False)
    for ax in axes:
        ax.set_xlabel("Objetivos (M)")
        ax.set_xticks(x)
        ax.grid(alpha=.2)
    fig.suptitle("MaF13: métricas normalizadas e efeito das soluções extremas")
    figures = maf / "figures_x"
    figures.mkdir(exist_ok=True)
    fig.savefig(figures / "MaF13_metricas_normalizadas.png", dpi=200)
    plt.close(fig)
    lines = [
        "# MaF13: escala e soluções extremas", "",
        "Os valores atuais de IGD, GD e HV já usam a faixa teórica da fronteira "
        "real para normalizar cada objetivo. Por isso, recalcular essa normalização "
        "reproduz os valores atuais; o GD alto não é causado pela falta de escala.", "",
        "| M | IGD normalizado | GD normalizado | Distância mediana dos pontos | "
        "Distância p95 | Fração de pontos com distância > 1 |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            f"| {int(row.m)} | {row.IGD_normalized:.4f} | {row.GD_normalized:.3g} | "
            f"{row.point_distance_normalized_median:.4f} | "
            f"{row.point_distance_normalized_p95:.3g} | "
            f"{row.fraction_points_distance_above_1:.1%} |"
        )
    lines.extend([
        "", "A distância mediana é pequena, mas a cauda é extrema. Assim, a "
        "maioria mais próxima descreve razoavelmente a fronteira enquanto um grupo "
        "de soluções muito afastadas eleva fortemente o GD médio. O artigo deve "
        "mostrar IGD, GD e os quantis de distância em conjunto.",
    ])
    (maf / "MAF13_NORMALIZATION_NOTE.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--doe", type=Path,
                        default=Path("experimental_results/doe_final_unlimited_calibrated"))
    parser.add_argument("--maf", type=Path,
                        default=Path("experimental_results/maf_cnbi_unlimited"))
    args = parser.parse_args()
    cardinality_curves(args.doe)
    maf13_scale_audit(args.maf)
    print("Curvas de cardinalidade e auditoria normalizada do MaF13 concluídas.")


if __name__ == "__main__":
    main()
