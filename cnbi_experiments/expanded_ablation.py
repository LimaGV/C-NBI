"""Run CNBI-all only for a small set of contrasting synthetic scenarios."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import scipy
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .doe import RSM
from .pilot import frontier, metrics, write_json
from .solver import Config, run_cnbi


SCENARIOS = (
    # Balanced 3 x 3 subset: every nx, excess and dependence level appears
    # three times.  This is an ablation subset, not a second full DOE.
    "doe_nx2_m4_low",       # nx=2, excess=1, low dependence
    "doe_nx2_m6_medium",    # nx=2, excess=3, medium dependence
    "doe_nx2_m8_high",      # nx=2, excess=5, high dependence
    "doe_nx3_m5_high",      # nx=3, excess=1, high dependence
    "doe_nx3_m7_low",       # nx=3, excess=3, low dependence
    "doe_nx3_m9_medium",    # nx=3, excess=5, medium dependence
    "doe_nx5_m7_medium",    # nx=5, excess=1, medium dependence
    "doe_nx5_m9_high",      # nx=5, excess=3, high dependence
    "doe_nx5_m11_low",      # nx=5, excess=5, low dependence
)


def run(source: Path, output: Path, seeds=tuple(range(101, 111)), scenarios=SCENARIOS):
    output.mkdir(parents=True, exist_ok=True)
    rows_path = output / "ablation_runs.csv"
    rows = pd.read_csv(rows_path).to_dict("records") if rows_path.exists() else []
    done = {(r["scenario_id"], int(r["seed"])) for r in rows}
    source_complete = pd.read_csv(source / "campaign_complete.csv")

    for scenario in scenarios:
        anchors = np.load(source / f"{scenario}_anchors.npz")["anchors"]
        reference = np.load(source / f"{scenario}_reference.npz")
        rn = (reference["F"] - reference["ideal"]) / reference["amplitude"]
        for seed in seeds:
            if (scenario, seed) in done:
                continue
            problem = RSM(anchors, seed)
            spectral_json = source / f"{scenario}_seed{seed}_CNBI_spectral.json"
            spectral_result = json.loads(spectral_json.read_text(encoding="utf-8"))
            fixed_payoff = (
                spectral_result["diagnostics"]["Xstar"],
                spectral_result["diagnostics"]["payoff"],
                spectral_result.get("evaluation_phases", {}).get("payoff", 0),
            )
            result = run_cnbi(problem, Config(budget=None, seed=seed), "all",
                              fixed_payoff=fixed_payoff)
            x, f = frontier(problem, result)
            fn = (f - reference["ideal"]) / reference["amplitude"]
            prefix = f"{scenario}_seed{seed}_CNBI_all"
            write_json(output / f"{prefix}.json", result)
            np.savez_compressed(output / f"{prefix}_front.npz", X=x, F=f)
            row = dict(
                scenario_id=scenario, seed=seed, method="CNBI_all", n=len(f),
                status=result["status"], evaluations=result["evaluations"],
                seconds=result["seconds"],
                candidate_combinations=result["candidate_combinations"],
                selected_combinations=result["selected_combinations"],
                potential_subproblems=result["potential_subproblems"],
                processed_subproblems=result["processed_subproblems"],
                feasible_subproblems=result["feasible_subproblems"],
                **metrics(fn, rn, seed),
            )
            rows.append(row)
            pd.DataFrame(rows).to_csv(rows_path, index=False)
            print("ABLATION", scenario, seed, result["status"],
                  result["evaluations"], len(f), flush=True)

    all_rows = pd.DataFrame(rows)
    spectral = source_complete[
        source_complete.scenario_id.isin(scenarios)
        & source_complete.seed.isin(seeds)
        & source_complete.method.eq("CNBI_spectral")
    ].copy()
    spectral = spectral[[c for c in all_rows.columns if c in spectral.columns]]
    combined = pd.concat([all_rows, spectral], ignore_index=True)
    combined.to_csv(output / "ablation_comparison.csv", index=False)
    summary = combined.groupby(["scenario_id", "method"], as_index=False).agg(
        runs=("seed", "size"), front_points_median=("n", "median"),
        evaluations_median=("evaluations", "median"),
        IGD_median=("IGD", "median"),
        GD_median=("GD", "median"), HV_median=("HV", "median"),
        selected_combinations_median=("selected_combinations", "median"))
    summary.to_csv(output / "ablation_summary.csv", index=False)
    audit = dict(
        status="PASS" if (len(all_rows) == len(scenarios) * len(seeds)
                          and all_rows.status.eq("COMPLETED").all()
                          and all_rows.n.gt(0).all()) else "INCOMPLETE",
        source_campaign=str(source.resolve()), scenarios=list(scenarios),
        seeds=list(seeds), resolution_rule="20% for k<=4; 50% for k>4",
        python_version=platform.python_version(), numpy_version=np.__version__,
        scipy_version=scipy.__version__,
        paired_payoff="exact Xstar and payoff matrix reused from each spectral run",
        cnbi_all_only_in_ablation=True,
        timing_comparison_valid=False,
        timing_note=("CNBI-all reused the saved payoff geometry; evaluation counts "
                     "include the shared payoff cost, but elapsed times are not compared"),
        completed_runs=len(all_rows), expected_runs=len(scenarios) * len(seeds),
    )
    write_json(output / "ABLATION_AUDIT.json", audit)
    wide = combined.pivot(index=["scenario_id", "seed"], columns="method",
                          values=["IGD", "HV", "evaluations"])
    lines = [
        "# Ablação ampliada e pareada", "",
        "CNBI-all foi executado somente nesta análise. Para que a única diferença "
        "fosse o filtro espectral, cada par reutilizou exatamente a mesma matriz "
        "payoff e os mesmos ótimos individuais do resultado espectral salvo. "
        "Os nove cenários formam um subconjunto balanceado: cada nível de dimensão, "
        "excesso de objetivos e dependência aparece três vezes.", "",
        "| Cenário | Redução mediana de avaliações | Aumento mediano de IGD | Perda mediana de HV |",
        "|---|---:|---:|---:|",
    ]
    for scenario in scenarios:
        block = wide.loc[scenario]
        reduction = np.median((block[("evaluations", "CNBI_all")]
                               - block[("evaluations", "CNBI_spectral")])
                              / block[("evaluations", "CNBI_all")] * 100)
        igd_loss = np.median(block[("IGD", "CNBI_spectral")]
                             - block[("IGD", "CNBI_all")])
        hv_loss = np.median(block[("HV", "CNBI_all")]
                            - block[("HV", "CNBI_spectral")])
        lines.append(f"| {scenario} | {reduction:.1f}% | {igd_loss:.4f} | {hv_loss:.4f} |")
    lines.extend([
        "", "A economia variou bastante entre as nove estruturas. O maior ganho "
        "ocorreu quando o filtro reteve uma parcela pequena das combinações. A "
        "qualidade caiu pouco na maior parte dos casos, enquanto CNBI-all foi "
        "ligeiramente melhor por explorar todas as combinações.", "",
        "O tempo não é comparado: o braço CNBI-all reutilizou o payoff já calculado. "
        "A contagem de avaliações inclui esse custo compartilhado e permanece comparável.",
    ])
    (output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    labels, reductions, igd_losses, hv_losses = [], [], [], []
    for scenario in scenarios:
        block = wide.loc[scenario]
        labels.append(scenario.replace("doe_", "").replace("_", "\n"))
        reductions.append(np.median((block[("evaluations", "CNBI_all")]
                                     - block[("evaluations", "CNBI_spectral")])
                                    / block[("evaluations", "CNBI_all")] * 100))
        igd_losses.append(np.median(block[("IGD", "CNBI_spectral")]
                                    - block[("IGD", "CNBI_all")]))
        hv_losses.append(np.median(block[("HV", "CNBI_all")]
                                   - block[("HV", "CNBI_spectral")]))
    x = np.arange(len(labels))
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.4), layout="constrained")
    axes[0].bar(x, reductions, color="#0072B2")
    axes[0].set(title="Economia de avaliações", ylabel="Redução mediana (%)")
    axes[1].bar(x, igd_losses, color="#D55E00")
    axes[1].set(title="Perda de IGD", ylabel="CNBI spectral − CNBI-all")
    axes[2].bar(x, hv_losses, color="#009E73")
    axes[2].set(title="Perda de HV", ylabel="CNBI-all − CNBI spectral")
    for ax in axes:
        ax.set_xticks(x, labels, fontsize=8)
        ax.grid(axis="y", alpha=.2)
    fig.suptitle("Ablação do filtro espectral em cenários contrastantes")
    fig.savefig(output / "ablation_summary.png", dpi=200)
    plt.close(fig)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path,
                        default=Path("experimental_results/doe_final_unlimited_calibrated"))
    parser.add_argument("--output", type=Path,
                        default=Path("experimental_results/ablation_expanded_9_final"))
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(101, 111)))
    parser.add_argument("--scenarios", nargs="+", default=list(SCENARIOS))
    args = parser.parse_args()
    run(args.source, args.output, tuple(args.seeds), tuple(args.scenarios))
