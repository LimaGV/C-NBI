"""Tables and decision-space plots for the separate CNBI-only MaF benchmark."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

from cnbi.pareto import postprocess_frontier
from .benchmarks import MaF


def objective_projection(real_f, cnbi_f, ideal, amplitude):
    """Project normalized objectives on the first two PCs of the real front."""
    real = (real_f - ideal) / amplitude
    cnbi = (cnbi_f - ideal) / amplitude
    center = real.mean(axis=0)
    _, _, directions = np.linalg.svd(real - center, full_matrices=False)
    basis = directions[:2].T
    return (real - center) @ basis, (cnbi - center) @ basis


def plot_objective_comparison(output, figures, number, settings):
    fig, axes = plt.subplots(2, len(settings), figsize=(4 * len(settings), 8),
                             layout="constrained")
    if len(settings) == 1:
        axes = np.asarray(axes).reshape(2, 1)
    for column, m in enumerate(settings):
        problem = MaF(number, int(m))
        _, real_f = problem.pareto_sample(5000, 404)
        cnbi_f = np.load(
            output / f"maf{number}_m{m}_seed101_CNBI_spectral_front.npz"
        )["F"]
        reference = np.load(output / f"maf{number}_m{m}_reference.npz")
        real_2d, cnbi_2d = objective_projection(
            real_f, cnbi_f, reference["ideal"], reference["amplitude"]
        )
        for row, ax in enumerate(axes[:, column]):
            ax.scatter(real_2d[:, 0], real_2d[:, 1], s=5, alpha=.18,
                       color="#737373", label="Fronteira real (amostra)")
            ax.scatter(cnbi_2d[:, 0], cnbi_2d[:, 1], s=22, alpha=.9,
                       color="#0072B2", label="CNBI", zorder=3)
            ax.set(title=f"M={m}", xlabel="Componente 1", ylabel="Componente 2")
            ax.grid(alpha=.2)
            if row == 1:
                low = real_2d.min(axis=0)
                high = real_2d.max(axis=0)
                margin = np.maximum((high - low) * .12, 1e-6)
                ax.set_xlim(low[0] - margin[0], high[0] + margin[0])
                ax.set_ylim(low[1] - margin[1], high[1] + margin[1])
    axes[0, 0].set_ylabel("Componente 2\nescala completa")
    axes[1, 0].set_ylabel("Componente 2\nampliação da fronteira real")
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle(
        f"MaF{number}: fronteira real × CNBI\nprojeção 2D dos objetivos normalizados",
        fontsize=13, fontweight="bold"
    )
    fig.savefig(figures / f"MaF{number}_fronteira_real_vs_CNBI.png", dpi=200)
    plt.close(fig)


def run(output: Path):
    data = pd.read_csv(output / "campaign_complete.csv")
    if len(data) != 130 or set(data.method) != {"CNBI_spectral"}:
        raise ValueError("Esperadas 130 execuções contendo somente CNBI spectral.")
    front_errors = []
    for row in data.itertuples(index=False):
        path = output / f"{row.scenario_id}_seed{row.seed}_CNBI_spectral_front.npz"
        with np.load(path) as front:
            valid = (
                front["X"].shape == (int(row.n), int(row.nx))
                and front["F"].shape == (int(row.n), int(row.m))
                and np.isfinite(front["X"]).all()
                and np.isfinite(front["F"]).all()
            )
        if not valid:
            front_errors.append(str(path))
    audit = {
        "status": "PASS" if (
            data.status.eq("COMPLETED").all()
            and data.budget.isna().all()
            and data.n.gt(0).all()
            and not front_errors
        ) else "FAIL",
        "checks": {
            "130_completed": bool(len(data) == 130 and data.status.eq("COMPLETED").all()),
            "cnbi_unlimited": bool(data.budget.isna().all()),
            "no_empty_fronts": bool(data.n.gt(0).all()),
            "front_files_finite_and_dimensionally_valid": not front_errors,
        },
        "front_errors": front_errors,
    }
    (output / "MAF_AUDIT.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    if audit["status"] != "PASS":
        raise ValueError("A auditoria do benchmark MaF falhou.")

    summary = data.groupby(["scenario_id", "m"], as_index=False).agg(
        runs=("seed", "size"),
        front_points_median=("n", "median"),
        evaluations_min=("evaluations", "min"),
        evaluations_median=("evaluations", "median"),
        evaluations_max=("evaluations", "max"),
        IGD_median=("IGD", "median"),
        IGD_min=("IGD", "min"),
        IGD_max=("IGD", "max"),
        GD_median=("GD", "median"),
        GD_min=("GD", "min"),
        GD_max=("GD", "max"),
        HV_median=("HV", "median"),
        HV_min=("HV", "min"),
        HV_max=("HV", "max"),
    )
    summary.to_csv(output / "MAF_CNBI_SUMMARY.csv", index=False)

    postprocess_rows = []
    for row in data[data.scenario_id.str.startswith("maf13_")].itertuples(index=False):
        path = output / f"{row.scenario_id}_seed{row.seed}_CNBI_spectral.json"
        result = json.loads(path.read_text(encoding="utf-8"))
        accepted = [item for item in result["rows"] if item.get("accepted") and "x" in item]
        x = np.asarray([item["x"] for item in accepted], dtype=float)
        f = np.asarray([item["F"] for item in accepted], dtype=float)
        processed = postprocess_frontier(
            x, f, duplicate_tolerance=1e-5, dominance_tolerance=1e-10
        )
        postprocess_rows.append({
            "scenario_id": row.scenario_id,
            "seed": row.seed,
            "accepted_by_subproblems": processed["input_count"],
            "distinct_decisions": processed["after_duplicates"],
            "final_nondominated": processed["output_count"],
            "duplicates_removed": processed["input_count"] - processed["after_duplicates"],
            "dominated_removed": processed["after_duplicates"] - processed["output_count"],
        })
    postprocess = pd.DataFrame(postprocess_rows)
    postprocess.to_csv(output / "MAF13_POSTPROCESS_AUDIT.csv", index=False)

    figures = output / "figures_x"
    figures.mkdir(exist_ok=True)
    for number in (8, 9):
        settings = sorted(data[data.scenario_id.str.startswith(f"maf{number}_")].m.unique())
        fig, axes = plt.subplots(1, len(settings), figsize=(4 * len(settings), 4),
                                 sharex=True, sharey=True, layout="constrained")
        for ax, m in zip(axes, settings):
            problem = MaF(number, int(m))
            real_x, _ = problem.pareto_sample(5000, 404)
            path = output / f"maf{number}_m{m}_seed101_CNBI_spectral_front.npz"
            x = np.load(path)["X"]
            ax.scatter(real_x[:, 0], real_x[:, 1], s=5, alpha=.14,
                       color="#737373", label="Pareto real")
            ax.scatter(x[:, 0], x[:, 1], s=14, alpha=.75, color="#1f77b4")
            ax.set(title=f"M={m}", xlabel="x1", ylabel="x2")
            ax.grid(alpha=.2)
        axes[0].legend(handles=[
            Line2D([0], [0], marker="o", linestyle="", color="#737373",
                   label="Pareto real", markersize=5),
            Line2D([0], [0], marker="o", linestyle="", color="#1f77b4",
                   label="CNBI", markersize=5),
        ], frameon=False, fontsize=8)
        fig.suptitle(f"MaF{number}: soluções do CNBI no espaço x (semente 101)",
                     fontsize=14, fontweight="bold")
        fig.savefig(figures / f"MaF{number}_espaco_x.png", dpi=200)
        plt.close(fig)
        plot_objective_comparison(output, figures, number, settings)

    settings = sorted(data[data.scenario_id.str.startswith("maf13_")].m.unique())
    fig, axes = plt.subplots(1, len(settings), figsize=(5 * len(settings), 5),
                             sharey=True, layout="constrained")
    for ax, m in zip(axes, settings):
        problem = MaF(13, int(m))
        real_x, _ = problem.pareto_sample(5000, 404)
        real_x = real_x[np.linspace(0, len(real_x) - 1, 300, dtype=int)]
        path = output / f"maf13_m{m}_seed101_CNBI_spectral_front.npz"
        x = np.load(path)["X"]
        for row in real_x:
            ax.plot(range(1, real_x.shape[1] + 1), row, alpha=.07,
                    linewidth=.45, color="#737373")
        for row in x:
            ax.plot(range(1, x.shape[1] + 1), row, alpha=.72, linewidth=1.2,
                    color="#0072B2")
        ax.set(title=f"M={m}", xlabel="Variável de decisão", ylabel="Valor de x",
               xticks=range(1, x.shape[1] + 1))
        ax.grid(alpha=.2)
    axes[0].legend(handles=[
        Line2D([0], [0], color="#737373", alpha=.6, label="Pareto real"),
        Line2D([0], [0], color="#0072B2", label="CNBI"),
    ], frameon=False, fontsize=8)
    fig.suptitle("MaF13: soluções do CNBI no espaço x (semente 101)",
                 fontsize=14, fontweight="bold")
    fig.savefig(figures / "MaF13_espaco_x.png", dpi=200)
    plt.close(fig)
    plot_objective_comparison(output, figures, 13, settings)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), layout="constrained")
    for number, group in summary.groupby(summary.scenario_id.str.extract(r"maf(\d+)")[0]):
        ordered = group.sort_values("m")
        axes[0].plot(ordered.m, ordered.IGD_median, marker="o", label=f"MaF{number}")
        axes[1].plot(ordered.m, ordered.HV_median, marker="o", label=f"MaF{number}")
    axes[0].set(title="IGD mediano", xlabel="Objetivos (M)", ylabel="IGD")
    axes[1].set(title="HV mediano", xlabel="Objetivos (M)", ylabel="HV")
    for ax in axes:
        ax.grid(alpha=.2)
        ax.legend(frameon=False)
    fig.suptitle("CNBI nos benchmarks MaF")
    fig.savefig(figures / "MaF_metricas_por_M.png", dpi=200)
    plt.close(fig)

    audit_medians = postprocess.groupby("scenario_id")[[
        "accepted_by_subproblems", "distinct_decisions", "final_nondominated"
    ]].median()
    report = f"""# Benchmark MaF somente com CNBI

Foram executadas 13 configurações, com 10 sementes cada. As 130 execuções terminaram sem teto de avaliações e sem frentes vazias. Este benchmark é separado do DOE sintético e não participa da ANOVA nem da comparação entre métodos.

No MaF8, o IGD mediano variou de {summary[summary.scenario_id.str.startswith('maf8_')].IGD_median.min():.4f} a {summary[summary.scenario_id.str.startswith('maf8_')].IGD_median.max():.4f}. No MaF9, variou de {summary[summary.scenario_id.str.startswith('maf9_')].IGD_median.min():.4f} a {summary[summary.scenario_id.str.startswith('maf9_')].IGD_median.max():.4f}. O desenho no espaço x mostra cobertura progressivamente mais densa quando M aumenta.

O MaF13 é mais difícil para o CNBI: o IGD mediano foi {summary.loc[summary.scenario_id.eq('maf13_m8'),'IGD_median'].iloc[0]:.4f}, {summary.loc[summary.scenario_id.eq('maf13_m10'),'IGD_median'].iloc[0]:.4f} e {summary.loc[summary.scenario_id.eq('maf13_m15'),'IGD_median'].iloc[0]:.4f}. A comparação visual também revela pontos do CNBI muito afastados da fronteira real, principalmente nas soluções extremas. Por isso, o GD é muito alto e deve ser apresentado junto com o IGD; o IGD sozinho não evidencia esses pontos afastados.

A quantidade final pequena não veio de falta de tentativas. Em M=15, a mediana foi de {audit_medians.loc['maf13_m15','accepted_by_subproblems']:.0f} soluções aceitas pelos subproblemas, {audit_medians.loc['maf13_m15','distinct_decisions']:.0f} decisões distintas após remover repetições e {audit_medians.loc['maf13_m15','final_nondominated']:.0f} pontos finais após remover dominadas.

Os valores de HV entre números diferentes de objetivos não devem ser comparados diretamente, porque a dimensão do volume muda. Eles são adequados para comparar resultados dentro da mesma configuração.
"""
    (output / "MAF_CNBI_RESUMO.md").write_text(report, encoding="utf-8")
    print(f"Resumo e sete gráficos gravados em {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    run(parser.parse_args().output)
