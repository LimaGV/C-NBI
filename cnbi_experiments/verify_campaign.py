"""Audit persisted full-campaign artifacts without rerunning optimizers."""
import argparse
import hashlib
import json
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd


EXPECTED_RESOLUTION = {2: 0.2, 3: 0.2, 4: 0.2, 5: 0.5, 6: 0.5}
ABLATION_SCENARIO = "doe_nx2_m4_low"


def verify(output: Path, repository: Path) -> dict:
    data = pd.read_csv(output / "master_results.csv")
    complete = data[data.comparison.eq("complete")].copy()
    equal = data[data.comparison.eq("equal_cardinality")].copy()
    failures = []

    def check(name, condition, detail=None):
        passed = bool(condition)
        if not passed:
            failures.append(name)
        return {"passed": passed, "detail": detail} if detail is not None else passed

    checks = {}
    checks["master_shape"] = check("master_shape", len(data) == 3220 and len(complete) == 1610 and len(equal) == 1610,
                                    {"rows": len(data), "complete": len(complete), "equal_cardinality": len(equal)})
    expected_exports = {
        "DOE_synthetic_results.csv": 2160,
        "MaF_benchmarks_results.csv": 1040,
        "ablation_results.csv": 40,
        "transition_results.csv": 50,
        "pa_sensitivity.csv": 104,
    }
    observed_exports = {name: len(pd.read_csv(output / name)) for name in expected_exports}
    checks["export_rows"] = check("export_rows", observed_exports == expected_exports, observed_exports)

    regular = complete[complete.method.ne("CNBI_all")]
    doe = regular[regular.scenario_id.str.startswith("doe_")]
    maf = regular[regular.scenario_id.str.startswith("maf")]
    coverage_ok = (doe.scenario_id.nunique() == 27 and maf.scenario_id.nunique() == 13 and
                   doe.groupby(["scenario_id", "method"]).seed.nunique().eq(10).all() and
                   maf.groupby(["scenario_id", "method"]).seed.nunique().eq(10).all())
    checks["full_grid"] = check("full_grid", coverage_ok,
                                 {"doe_conditions": doe.scenario_id.nunique(), "maf_settings": maf.scenario_id.nunique()})

    all_rows = complete[complete.method.eq("CNBI_all")]
    ablation_ok = (len(all_rows) == 10 and all_rows.scenario_id.eq(ABLATION_SCENARIO).all() and
                   all_rows.seed.nunique() == 10)
    checks["single_synthetic_ablation"] = check("single_synthetic_ablation", ablation_ok,
                                                 {"runs": len(all_rows), "scenarios": sorted(all_rows.scenario_id.unique())})

    preparation = json.loads((output / "preparation.json").read_text(encoding="utf-8"))
    prep_rows = preparation.get("preparations", preparation) if isinstance(preparation, dict) else preparation
    calibration_errors = [abs(float(x["achieved"]) - float(x["target"])) for x in prep_rows]
    calibration_ok = len(prep_rows) == 27 and all(x.get("status") == "CALIBRATED" for x in prep_rows) and max(calibration_errors) <= 0.04
    checks["doe_calibration"] = check("doe_calibration", calibration_ok,
                                       {"conditions": len(prep_rows), "max_absolute_error": max(calibration_errors)})

    phase_errors = []
    budget_errors = []
    front_errors = []
    resolution_errors = []
    fallback_runs = []
    vrf_factor_errors = []
    empty_runs = []
    for _, row in complete.iterrows():
        method_file = row.method.replace("/", "_")
        prefix = f"{row.scenario_id}_seed{int(row.seed)}_{method_file}"
        raw = json.loads((output / f"{prefix}.json").read_text(encoding="utf-8"))
        if sum(raw.get("evaluation_phases", {}).values()) != int(raw["evaluations"]):
            phase_errors.append(prefix)
        if int(raw["evaluations"]) > int(row.budget):
            budget_errors.append(prefix)
        F = np.load(output / f"{prefix}_front.npz")["F"]
        if F.ndim != 2 or F.shape[0] != int(row.n) or F.shape[1] != int(row.m) or not np.isfinite(F).all():
            front_errors.append(prefix)
        if len(F) == 0:
            empty_runs.append({"scenario_id": row.scenario_id, "seed": int(row.seed),
                               "method": row.method, "status": row.status})
        if row.method.startswith("CNBI"):
            for item in raw.get("combinations", []):
                k = len(item["combo"])
                expected = comb(round(1 / EXPECTED_RESOLUTION[k]) + k - 1, k - 1)
                if int(item["potential_subproblems"]) != expected:
                    resolution_errors.append({"run": prefix, "k": k, "observed": item["potential_subproblems"], "expected": expected})
        if row.method == "VRF-NBI":
            diagnostics = raw.get("diagnostics", {})
            if int(diagnostics.get("n_factors", 0)) < 2:
                vrf_factor_errors.append(prefix)
            if diagnostics.get("score_weight_rule") == "loadings_fallback_singular_correlation":
                fallback_runs.append(prefix)

    checks["phase_accounting"] = check("phase_accounting", not phase_errors, {"errors": phase_errors})
    checks["hard_budget"] = check("hard_budget", not budget_errors, {"errors": budget_errors})
    checks["finite_front_files"] = check("finite_front_files", not front_errors, {"errors": front_errors})
    checks["cnbi_resolution"] = check("cnbi_resolution", not resolution_errors,
                                      {"rule": {str(k): v for k, v in EXPECTED_RESOLUTION.items()}, "errors": resolution_errors})
    checks["vrf_minimum_two_factors"] = check("vrf_minimum_two_factors", not vrf_factor_errors,
                                               {"errors": vrf_factor_errors})
    checks["vrf_library_fallback"] = {"passed": True, "count": len(fallback_runs), "runs": fallback_runs}

    provenance = json.loads((output / "provenance.json").read_text(encoding="utf-8"))
    core_dir = repository / "cnbi"
    current_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in core_dir.glob("*.py")}
    expected_hashes = provenance["core_hashes"]
    checks["core_hashes_intact"] = check("core_hashes_intact", current_hashes == expected_hashes,
                                          {"expected": expected_hashes, "observed": current_hashes})

    status_counts = {str(k): int(v) for k, v in complete.status.value_counts().items()}
    blocked_cardinality = int(equal.cardinality_status.ne("PASS").sum())
    result = {
        "status": "PASS_WITH_RECORDED_EMPTY_FRONTS" if not failures else "FAIL",
        "checks": checks,
        "status_counts": status_counts,
        "empty_front_count": len(empty_runs),
        "empty_front_runs": empty_runs,
        "blocked_equal_cardinality_rows": blocked_cardinality,
        "methodology": {
            "cnbi_resolution": {str(k): v for k, v in EXPECTED_RESOLUTION.items()},
            "vrf_factor_rule": "max(2, k90)",
            "vrf_singular_score_rule": "library loadings fallback on LinAlgError",
            "cnbi_all_scenario": ABLATION_SCENARIO,
            "core_cnbi_modified": False,
        },
        "failures": failures,
    }
    (output / "VERIFICATION.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(verify(args.output, args.repository), indent=2, ensure_ascii=False))
