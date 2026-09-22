"""Minitab-style diagnostic and factorial plots for the completed synthetic DOE."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
import warnings


OUTPUT = Path("experimental_results/doe_legacy_generator")
FIGURES = OUTPUT / "figures_minitab"
LEVELS = {
    "nx": [2, 3, 5],
    "delta": [1, 3, 5],
    "dependence_level": ["low", "medium", "high"],
}
LABELS = {
    "nx": "Dimensão (nx)",
    "delta": "Excesso dimensional (delta)",
    "dependence_level": "Dependência",
}
DISPLAY = {"low": "Baixa", "medium": "Média", "high": "Alta"}
COLORS = ["#1f77b4", "#d95f02", "#2ca02c"]


def display_level(value):
    return DISPLAY.get(value, str(value))


def fit_model(data, response):
    terms = ("C(nx, Helmert)*C(delta, Helmert)*"
             "C(dependence_level, Helmert) + C(seed, Helmert)")
    return smf.ols(f"{response} ~ {terms}", data).fit()


def main_effects(data, response):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.7), sharey=True, layout="constrained")
    overall = data[response].mean()
    for ax, factor in zip(axes, LEVELS):
        means = data.groupby(factor)[response].mean().reindex(LEVELS[factor])
        ax.plot(range(3), means, color="#1f4e79", marker="o", linewidth=1.8, markersize=6)
        ax.axhline(overall, color="#a61c00", linestyle="--", linewidth=1, label="Média geral")
        ax.set_xticks(range(3), [display_level(v) for v in LEVELS[factor]])
        ax.set_xlabel(LABELS[factor])
        ax.grid(axis="y", alpha=.22)
    axes[0].set_ylabel(f"Média de {response}")
    axes[-1].legend(frameon=False, loc="best")
    fig.suptitle(f"Gráfico de efeitos principais para {response}", fontsize=14, fontweight="bold")
    fig.savefig(FIGURES / f"{response}_01_efeitos_principais.png", dpi=200)
    plt.close(fig)


def interaction_panel(ax, data, response, xfactor, linefactor):
    xlevels, linelevels = LEVELS[xfactor], LEVELS[linefactor]
    for color, linelevel in zip(COLORS, linelevels):
        subset = data[data[linefactor].eq(linelevel)]
        means = subset.groupby(xfactor)[response].mean().reindex(xlevels)
        ax.plot(range(len(xlevels)), means, marker="o", linewidth=1.6, color=color,
                label=f"{LABELS[linefactor]}: {display_level(linelevel)}")
    ax.set_xticks(range(len(xlevels)), [display_level(v) for v in xlevels])
    ax.set_xlabel(LABELS[xfactor])
    ax.set_ylabel(f"Média de {response}")
    ax.grid(alpha=.22)
    ax.legend(frameon=False, fontsize=8)


def interactions(data, response):
    pairs = [("nx", "delta"), ("nx", "dependence_level"),
             ("delta", "dependence_level")]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.9), layout="constrained")
    for ax, (x, lines) in zip(axes, pairs):
        interaction_panel(ax, data, response, x, lines)
    fig.suptitle(f"Gráficos de interação para {response}", fontsize=14, fontweight="bold")
    fig.savefig(FIGURES / f"{response}_02_interacoes.png", dpi=200)
    plt.close(fig)


def residuals_four_in_one(model, response):
    residual = np.asarray(model.resid)
    fitted = np.asarray(model.fittedvalues)
    standardized = residual / residual.std(ddof=1)
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), layout="constrained")

    osm, osr = stats.probplot(standardized, dist="norm", fit=False)
    slope, intercept, *_ = stats.linregress(osm, osr)
    axes[0, 0].scatter(osm, osr, s=18, facecolor="#5b9bd5", edgecolor="white", linewidth=.3)
    axes[0, 0].plot(osm, intercept + slope * np.asarray(osm), color="#c00000", linewidth=1.2)
    axes[0, 0].set(title="Gráfico de probabilidade normal", xlabel="Percentil normal",
                   ylabel="Resíduo padronizado")

    axes[0, 1].scatter(fitted, standardized, s=20, facecolor="#5b9bd5", edgecolor="white", linewidth=.3)
    axes[0, 1].axhline(0, color="#c00000", linewidth=1)
    axes[0, 1].set(title="Resíduos versus valores ajustados", xlabel="Valor ajustado",
                   ylabel="Resíduo padronizado")

    axes[1, 0].hist(standardized, bins=14, color="#5b9bd5", edgecolor="white")
    axes[1, 0].set(title="Histograma dos resíduos", xlabel="Resíduo padronizado", ylabel="Frequência")

    axes[1, 1].plot(np.arange(1, len(standardized) + 1), standardized, color="#5b9bd5",
                    marker="o", markersize=2.8, linewidth=.65)
    axes[1, 1].axhline(0, color="#c00000", linewidth=1)
    axes[1, 1].set(title="Resíduos versus ordem", xlabel="Ordem de observação",
                   ylabel="Resíduo padronizado")
    for ax in axes.flat:
        ax.grid(alpha=.16)
    fig.suptitle(f"Quatro gráficos de resíduos para {response}", fontsize=14, fontweight="bold")
    fig.savefig(FIGURES / f"{response}_03_residuos_4_em_1.png", dpi=200)
    plt.close(fig)


def term_name(term):
    mapping = {
        "C(nx, Helmert)": "Dimensão",
        "C(delta, Helmert)": "Delta",
        "C(dependence_level, Helmert)": "Dependência",
        "C(nx, Helmert):C(delta, Helmert)": "Dimensão × Delta",
        "C(nx, Helmert):C(dependence_level, Helmert)": "Dimensão × Dependência",
        "C(delta, Helmert):C(dependence_level, Helmert)": "Delta × Dependência",
        "C(nx, Helmert):C(delta, Helmert):C(dependence_level, Helmert)":
            "Dimensão × Delta × Dependência",
    }
    return mapping.get(term, term)


def pareto_terms(model, response):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        table = model.wald_test_terms(skip_single=False).table.reset_index()
    table = table.rename(columns={table.columns[0]: "term"})
    table = table[~table.term.isin(["Intercept", "C(seed, Helmert)"])].copy()
    table["pvalue"] = table["pvalue"].map(lambda value: float(np.asarray(value)))
    table["strength"] = -np.log10(table["pvalue"].clip(lower=1e-300))
    table["label"] = table.term.map(term_name)
    table = table.sort_values("strength")
    colors = np.where(table.pvalue < .05, "#4472c4", "#a5a5a5")

    fig, ax = plt.subplots(figsize=(9, 5.5), layout="constrained")
    ax.barh(table.label, table.strength, color=colors, edgecolor="white")
    ax.axvline(-np.log10(.05), color="#c00000", linestyle="--", linewidth=1.3,
               label="Limite de 5%")
    ax.set(xlabel="Força estatística: −log10(p)", ylabel="Termo")
    ax.set_title(f"Pareto dos termos para {response}", fontsize=14, fontweight="bold")
    ax.legend(frameon=False)
    ax.grid(axis="x", alpha=.2)
    fig.savefig(FIGURES / f"{response}_04_pareto_termos.png", dpi=200)
    plt.close(fig)
    table[["term", "label", "pvalue", "strength"]].to_csv(
        FIGURES / f"{response}_pareto_dados.csv", index=False
    )


def run():
    FIGURES.mkdir(exist_ok=True)
    data = pd.read_csv(OUTPUT / "master_results.csv")
    data = data[(data.comparison == "equal_cardinality") &
                (data.method == "CNBI_spectral") &
                data.scenario_id.str.startswith("doe")].copy()
    for response in ("IGD", "HV"):
        model = fit_model(data, response)
        main_effects(data, response)
        interactions(data, response)
        residuals_four_in_one(model, response)
        pareto_terms(model, response)
    (FIGURES / "LEIA-ME.txt").write_text(
        "Gráficos no estilo Minitab para o DOE sintético do CNBI spectral, "
        "na comparação com quantidade igual de pontos.\n"
        "IGD: menor é melhor. HV: maior é melhor. A linha vermelha do Pareto "
        "corresponde a p=0,05 na ANOVA em blocos do modelo com interação tripla.\n",
        encoding="utf-8",
    )
    print(f"Gerados 8 gráficos em {FIGURES}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", nargs="?", type=Path, default=OUTPUT)
    args = parser.parse_args()
    OUTPUT = args.output
    FIGURES = OUTPUT / "figures_minitab"
    run()
