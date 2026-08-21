"""Validate scientific run manifests against the selected configuration."""
from __future__ import annotations

import argparse
import json
import math
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def require_columns(df: pd.DataFrame, columns: set[str], label: str) -> None:
    missing = columns - set(df.columns)
    if missing:
        raise AssertionError(f"{label}: colunas ausentes: {sorted(missing)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["PILOT", "FULL"], required=True)
    args = parser.parse_args()
    cfg = json.loads((ROOT / "configs" / f"{args.mode.lower()}.json").read_text(encoding="utf-8"))
    tables = ROOT / "results" / "tables"
    tuning = ROOT / "results" / "tuning"

    chosen = json.loads((tuning / "chosen_parameters.json").read_text(encoding="utf-8"))
    expected_keys = {
        f"{method}_m{m}" for method in ("NSGAIII", "MOEAD") for m in cfg["scenario_objectives"]
    }
    assert expected_keys <= set(chosen), "Configurações vencedoras ausentes"
    assert all(chosen[key].get("status") == "COMPLETED" for key in expected_keys)
    assert all(chosen[key].get("selection_order") for key in expected_keys), "Justificativa/ranking ausente"

    scenarios = [f"m{m}_{level}" for m in cfg["scenario_objectives"] for level in cfg["correlation_targets"]]
    scenario_diag = pd.read_csv(ROOT / "data" / "generated" / "scenario_diagnostics.csv")
    assert set(scenario_diag.scenario) == set(scenarios), "Cobertura incorreta dos diagnósticos de cenário"
    require_columns(scenario_diag, {"target", "achieved", "affine_rank", "effective_rank", "redundancy", "within_tolerance", "min_anchor_distance", "max_anchor_norm", "numerical_rank", "singular_values_json", "cumulative_variance_json", "reference_reproducible", "reference_inside_hull", "reference_approx_nondominated_fraction", "known_optima_verified"}, "scenario_diagnostics")
    assert scenario_diag.within_tolerance.astype(str).str.lower().eq("true").all()
    assert scenario_diag.affine_rank.astype(int).eq(3).all()
    assert scenario_diag.min_anchor_distance.gt(0).all() and scenario_diag.max_anchor_norm.lt(2 ** .75).all()
    assert scenario_diag.reference_reproducible.astype(str).str.lower().eq("true").all()
    assert scenario_diag.reference_inside_hull.astype(str).str.lower().eq("true").all()
    assert scenario_diag.reference_approx_nondominated_fraction.ge(.99).all()
    assert scenario_diag.known_optima_verified.astype(str).str.lower().eq("true").all()
    for scenario in scenarios:
        assert (ROOT / "data" / "generated" / f"{scenario}_scenario.npz").exists()
        assert (ROOT / "data" / "reference_fronts" / f"{scenario}_pareto_reference.npz").exists()

    tuning_results = pd.read_csv(tuning / "tuning_all_results.csv")
    require_columns(tuning_results, {"method", "m", "stage", "config_id", "seed", "status", "IGD", "rsm_evaluations", "checkpoint_reused"}, "tuning_all_results")
    for m in cfg["scenario_objectives"]:
        for method in ("NSGAIII", "MOEAD"):
            subset = tuning_results[(tuning_results.m == m) & (tuning_results.method == method)]
            required_stages = {"A", "B"} | ({"C"} if method == "MOEAD" else set())
            assert required_stages <= set(subset.stage), f"Estágios ausentes para {method}, m={m}"
            assert set(cfg["calibration_seeds"]) <= set(subset.seed.astype(int))
            coverage = pd.read_csv(tuning / f"stage_b_coverage_{method}_m{m}.csv")
            assert len(coverage) == 12 and len(coverage.drop_duplicates(["n_partitions", "sbx_probability", "sbx_eta", "pm_eta"])) == 12
            assert coverage.n_partitions.value_counts().eq(6).all()
            assert coverage.sbx_probability.value_counts().eq(6).all()
            assert coverage.sbx_eta.value_counts().eq(4).all() and coverage.pm_eta.value_counts().eq(4).all()
    finalists = pd.read_csv(tuning / "tuning_finalists.csv")
    require_columns(finalists, {"method", "m", "config_id", "seed", "IGD", "HV", "HV_se", "infeasibility", "wall_seconds"}, "tuning_finalists")
    for m in cfg["scenario_objectives"]:
        for method in ("NSGAIII", "MOEAD"):
            subset = finalists[(finalists.m == m) & (finalists.method == method)]
            assert subset.config_id.nunique() == 3
            assert set(subset.seed.astype(int)) == set(cfg["calibration_seeds"])
    rankings = pd.read_csv(tuning / "tuning_rankings.csv")
    require_columns(rankings, {"method", "m", "rank", "IGD_median", "HV_median", "infeasibility_median", "IGD_iqr", "wall_median"}, "tuning_rankings")

    runs = pd.read_csv(tables / f"{args.mode.lower()}_method_runs.csv")
    require_columns(
        runs,
        {"scenario", "seed", "method", "status", "rsm_evaluations", "gradient_evaluations", "wall_seconds", "checkpoint"},
        "method_runs",
    )
    expected = set()
    for scenario in scenarios:
        methods = ["NBI", "CNBI", "VRF-NBI", "NSGA-III", "MOEA/D"]
        expected |= {(scenario, int(seed), method) for seed in cfg["final_seeds"] for method in methods}
    actual = set(zip(runs.scenario, runs.seed.astype(int), runs.method))
    missing = expected - actual
    assert not missing, f"Execuções ausentes: {sorted(missing)[:10]}"
    invalid_nbi = runs[(runs.method == "NBI") & runs.scenario.str.extract(r"m(\d+)")[0].astype(int).gt(4)]
    assert invalid_nbi.status.eq("STRUCTURALLY_INVALID").all(), "NBI m>4 não registrado como inválido"
    analyzable_statuses = {"COMPLETED", "COMPLETED_WITH_INFEASIBLE_SUBPROBLEMS"}
    valid = runs[runs.status.isin(analyzable_statuses)]
    for _, row in runs[runs.method.isin(["NBI", "CNBI", "VRF-NBI"])].iterrows():
        if row.status == "COMPLETED":
            assert np.isclose(float(row.converged_fraction), 1.0)
        elif row.status == "COMPLETED_WITH_INFEASIBLE_SUBPROBLEMS":
            assert 0 <= float(row.converged_fraction) < 1
    assert pd.to_numeric(runs.gradient_evaluations, errors="coerce").fillna(0).ge(0).all()

    det = runs[runs.method.eq("CNBI")].set_index(["scenario", "seed"])
    for _, row in runs[runs.method.isin(["NSGA-III", "MOEA/D"])].iterrows():
        reference = int(det.loc[(row.scenario, int(row.seed)), "rsm_evaluations"])
        assert int(row.rsm_evaluations) <= reference, f"Orçamento excedido: {row.scenario}, {row.seed}, {row.method}"
        data = np.load(ROOT / row.checkpoint, allow_pickle=False)
        meta = json.loads(str(data["metadata"]))
        assert int(meta["budget_reference"]) == reference, "EA não usa orçamento CNBI pareado"
        identity = meta["identity"]
        assert identity["schema_version"] == 2 and identity["mode"] == args.mode
        assert identity["budget"] == reference and identity["scenario"] == row.scenario
        method_key = "NSGAIII" if row.method == "NSGA-III" else "MOEAD"
        m = int(str(row.scenario).split("_")[0][1:])
        expected_parameters = chosen[f"{method_key}_m{m}"]
        for parameter in ("n_partitions", "sbx_probability", "sbx_eta", "pm_eta", "neighbor_fraction", "prob_neighbor_mating"):
            assert np.isclose(float(meta["parameters"][parameter]), float(expected_parameters[parameter])), f"Parâmetro final divergente: {row.method}, m={m}, {parameter}"

    expected_pairs = {(scenario, int(seed)) for scenario in scenarios for seed in cfg["final_seeds"]}
    rsm = pd.read_csv(tables / f"{args.mode.lower()}_rsm_diagnostics.csv")
    require_columns(rsm, {"scenario", "seed", "objective", "n_design", "design_rank", "r2_target", "r2_observed", "mse_residual", "snr_realized", "noiseless_max_abs_error"}, "rsm_diagnostics")
    assert set(zip(rsm.scenario, rsm.seed.astype(int))) == expected_pairs
    assert rsm.n_design.eq(19).all() and rsm.design_rank.eq(10).all()
    assert np.allclose(rsm.r2_target, .95) and rsm.noiseless_max_abs_error.max() < 1e-10
    payoff = pd.read_csv(tables / f"{args.mode.lower()}_payoff_diagnostics.csv")
    assert set(zip(payoff.scenario, payoff.seed.astype(int))) == expected_pairs
    require_columns(payoff, {"columns_are_individual_minima", "diagonal_matches_individual_objective", "all_optima_feasible"}, "payoff_diagnostics")
    assert payoff.columns_are_individual_minima.astype(str).str.lower().eq("true").all()
    assert payoff.diagonal_matches_individual_objective.astype(str).str.lower().eq("true").all()
    assert payoff.all_optima_feasible.astype(str).str.lower().eq("true").all()
    parallel = pd.read_csv(tables / f"{args.mode.lower()}_parallel_analysis.csv")
    assert set(zip(parallel.scenario, parallel.seed.astype(int))) == expected_pairs
    assert parallel.n_mc.eq(2000).all() and parallel.mc_seed.eq(777).all() and parallel["mode"].eq("independent_legacy").all()
    vrf = pd.read_csv(tables / f"{args.mode.lower()}_vrf_diagnostics.csv")
    assert set(zip(vrf.scenario, vrf.seed.astype(int))) == expected_pairs
    assert vrf.pca_cumulative.ge(.90).all() and vrf.factor_method.eq("principal").all() and vrf.rotation.eq("varimax").all()
    require_columns(vrf, {"loadings_original_json", "loadings_oriented_json", "dominant_response_json", "dominant_loading_json", "sign_applied_json", "scores_before_json", "scores_after_json", "sign_invariance_verified"}, "vrf_diagnostics")
    assert vrf.sign_invariance_verified.astype(str).str.lower().eq("true").all()
    ledger = pd.read_csv(tables / f"{args.mode.lower()}_cnbi_subproblems.csv")
    require_columns(ledger, {"scenario", "seed", "combination", "k", "beta_id", "beta", "delta", "execution_order", "chosen_start", "attempts", "eq_inf", "sphere_violation", "t", "solver_success", "accepted", "subproblem_status", "aggregate_checkpoint"}, "cnbi_subproblems")
    assert set(zip(ledger.scenario, ledger.seed.astype(int))) == expected_pairs
    assert set(ledger.groupby("k").delta.first().round(2).to_dict().items()) <= {(2, .10), (3, .10), (4, .20), (5, .50)}
    accepted = ledger[ledger.success.astype(str).str.lower().eq("true")]
    assert accepted.eq_inf.le(1e-5).all() and accepted.sphere_violation.le(1e-8).all()
    assert accepted.subproblem_status.eq("COMPLETED").all()
    infeasible = ledger[ledger.subproblem_status.eq("NO_FEASIBLE_INTERSECTION")]
    assert infeasible.success.astype(str).str.lower().eq("false").all()
    assert set(ledger.subproblem_status) <= {"COMPLETED", "NO_FEASIBLE_INTERSECTION"}
    assert ledger.attempts.ge(0).all() and ledger.chosen_start.astype(str).str.len().gt(0).all()
    for (scenario, seed), group in ledger.groupby(["scenario", "seed"]):
        checkpoint = ROOT / group.aggregate_checkpoint.iloc[0]
        data = np.load(checkpoint, allow_pickle=False)
        assert len(group) == len(data["success"])
        assert not group.duplicated(["combination", "beta_id"]).any()
        assert np.array_equal(group.sort_values("execution_order").beta_id.to_numpy(), data["beta_id"][np.argsort(data["execution_order"])])

    metrics = pd.read_csv(tables / f"{args.mode.lower()}_metrics.csv")
    require_columns(metrics, {"scenario", "seed", "method", "comparison", "GD", "IGD", "HV", "HV_se", "Spacing", "Sparsity", "feasible_fraction", "converged_fraction", "rsm_evaluations", "wall_seconds", "cpu_seconds"}, "metrics")
    assert len(metrics) == 2 * len(valid), "Métricas completas/equalizadas incompletas"
    assert set(metrics.comparison) == {"complete", "equal_cardinality"}
    assert metrics[["GD", "IGD", "HV", "HV_se", "Spacing", "Sparsity"]].apply(np.isfinite).all().all()
    equal = metrics[metrics.comparison.eq("equal_cardinality")]
    assert equal.groupby(["scenario", "seed"]).n.nunique().eq(1).all(), "Cardinalidade não equalizada"
    for suffix in ("summary", "rankings", "statistics"):
        artifact = tables / f"{args.mode.lower()}_{suffix}.csv"
        assert artifact.exists() and artifact.stat().st_size > 2, f"Artefato ausente/vazio: {artifact.name}"
    statistics = pd.read_csv(tables / f"{args.mode.lower()}_statistics.csv")
    assert set(statistics.status) <= {"COMPLETED", "INSUFFICIENT_BLOCKS", "NO_VALID_COMMON_BLOCK"}

    resource_path = tables / ("pilot_end_to_end_resources.json" if args.mode == "PILOT" else f"{args.mode.lower()}_resource_summary.json")
    resources = json.loads(resource_path.read_text(encoding="utf-8"))
    for key in (("end_to_end_wall_seconds", "runner_cpu_seconds", "descendant_cpu_seconds", "total_cpu_seconds", "method_wall_seconds_sum", "method_cpu_seconds_sum", "peak_rss_bytes", "disk_bytes") if args.mode == "PILOT" else ("wall_seconds", "cpu_seconds", "peak_rss_bytes", "disk_bytes")):
        assert float(resources[key]) >= 0
    if args.mode == "PILOT":
        assert resources["cache_used"] is False and resources["checkpoints_reused"] == 0

    figures = ROOT / "results" / "figures"
    surface_manifest = pd.read_csv(figures / f"{args.mode.lower()}_response_surface_manifest.csv")
    pareto_manifest = pd.read_csv(figures / f"{args.mode.lower()}_true_pareto_manifest.csv")
    require_columns(
        surface_manifest,
        {"mode", "scenario", "objective", "rsm_seed", "slice_fixed_value", "png", "atlas_pdf"},
        "response_surface_manifest",
    )
    require_columns(
        pareto_manifest,
        {
            "mode", "scenario", "page", "objective_i", "objective_j", "page_png",
            "overview_png", "overview_pdf", "pairwise_pdf",
        },
        "true_pareto_manifest",
    )
    expected_surface = {
        (scenario, objective)
        for scenario in scenarios
        for objective in range(1, int(scenario.split("_")[0][1:]) + 1)
    }
    actual_surface = set(zip(surface_manifest.scenario, surface_manifest.objective.astype(int)))
    assert actual_surface == expected_surface, "Cobertura incompleta das superfícies de resposta"
    expected_pairs = {
        (scenario, i, j)
        for scenario in scenarios
        for i, j in combinations(range(1, int(scenario.split("_")[0][1:]) + 1), 2)
    }
    actual_pairs = set(
        zip(
            pareto_manifest.scenario,
            pareto_manifest.objective_i.astype(int),
            pareto_manifest.objective_j.astype(int),
        )
    )
    assert actual_pairs == expected_pairs, "Cobertura incompleta das projeções da fronteira verdadeira"
    figure_paths = (
        set(surface_manifest.png) | set(surface_manifest.atlas_pdf)
        | set(pareto_manifest.page_png) | set(pareto_manifest.overview_png)
        | set(pareto_manifest.overview_pdf) | set(pareto_manifest.pairwise_pdf)
    )
    for relative in figure_paths:
        artifact = ROOT / relative
        assert artifact.exists() and artifact.stat().st_size > 1000, f"Figura ausente/vazia: {relative}"

    overlay_root = figures / "method_front_overlays"
    overlay = pd.read_csv(overlay_root / f"{args.mode.lower()}_method_front_overlay_manifest.csv")
    require_columns(
        overlay,
        {
            "scenario", "method", "seed", "IGD", "IGD_median", "page",
            "objective_i", "objective_j", "n_method", "n_method_plotted",
            "page_png", "atlas_pdf",
        },
        "method_front_overlay_manifest",
    )
    complete_metrics = metrics[metrics.comparison.eq("complete")]
    expected_overlays = set(zip(complete_metrics.scenario, complete_metrics.method))
    actual_overlays = set(zip(overlay.scenario, overlay.method))
    assert actual_overlays == expected_overlays, "Métodos/cenários ausentes nas sobreposições"
    assert overlay.groupby(["scenario", "method"]).seed.nunique().eq(1).all()
    assert overlay.groupby(["scenario", "method"]).atlas_pdf.nunique().eq(1).all()
    for (scenario, method), group in overlay.groupby(["scenario", "method"]):
        m = int(scenario.split("_")[0][1:])
        assert len(group) == math.comb(m, 2), f"Projeções incompletas: {scenario}/{method}"
        assert not group.duplicated(["objective_i", "objective_j"]).any()
        assert group.n_method.astype(int).gt(0).all()
    overlay_paths = set(overlay.page_png) | set(overlay.atlas_pdf)
    for relative in overlay_paths:
        artifact = ROOT / relative
        assert artifact.exists() and artifact.stat().st_size > 1000, f"Sobreposição ausente/vazia: {relative}"
    print(f"{args.mode}: manifestos científicos aprovados.")


if __name__ == "__main__":
    main()
