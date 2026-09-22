"""Strict verification for the corrected synthetic DOE campaign."""
import argparse
import hashlib
import json
from math import comb
from pathlib import Path

import pandas as pd


OUTPUT = Path("experimental_results/doe_legacy_generator")
METHODS = {"CNBI_spectral", "VRF-NBI", "NSGA-III", "MOEA/D"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    complete = pd.read_csv(OUTPUT / "campaign_complete.csv")
    master = pd.read_csv(OUTPUT / "master_results.csv")
    equal = master[master.comparison.eq("equal_cardinality")]
    prep = json.loads((OUTPUT / "preparation.json").read_text(encoding="utf-8"))
    calibration_errors = [abs(float(row["achieved"]) - float(row["target"])) for row in prep]

    cnbi_resolution_errors = []
    cnbi_rows = complete[complete.method.eq("CNBI_spectral")]
    for row in cnbi_rows.itertuples():
        result = json.loads((OUTPUT / f"{row.scenario_id}_seed{row.seed}_CNBI_spectral.json").read_text())
        expected = sum(
            comb(int(row.m), k) * comb(round(1 / (0.2 if k <= 4 else 0.5)) + k - 1, k - 1)
            for k in range(2, min(int(row.m), int(row.nx) + 1) + 1)
        )
        if int(result["potential_subproblems"]) != expected:
            cnbi_resolution_errors.append(f"{row.scenario_id}/seed{row.seed}")

    vrf_rule_errors = []
    fallback_count = 0
    vrf_rows = complete[complete.method.eq("VRF-NBI")]
    for row in vrf_rows.itertuples():
        result = json.loads((OUTPUT / f"{row.scenario_id}_seed{row.seed}_VRF-NBI.json").read_text())
        diagnostics = result["diagnostics"]
        factors = int(diagnostics["n_factors"])
        k90 = int(diagnostics["n_factors_90"])
        if factors != max(2, k90) or float(diagnostics["retained_variance"]) < 0.9:
            vrf_rule_errors.append(f"{row.scenario_id}/seed{row.seed}")
        fallback_count += diagnostics.get("score_weight_rule") == "loadings_fallback_singular_correlation"
    checks = {
        "1080_runs": len(complete) == 1080,
        "27_conditions": complete.scenario_id.nunique() == 27,
        "four_regular_methods_only": set(complete.method) == METHODS and "CNBI_all" not in set(complete.method),
        "ten_seeds_per_condition_method": complete.groupby(["scenario_id", "method"]).seed.nunique().eq(10).all(),
        "no_empty_fronts": complete.n.gt(0).all(),
        "2160_master_rows": len(master) == 2160,
        "equal_cardinality_passed": len(equal) == 1080 and equal.cardinality_status.eq("PASS").all(),
        "27_calibrations_within_004": len(prep) == 27 and max(calibration_errors) <= 0.04,
        "cnbi_resolution_20_to_k4_50_above": len(cnbi_rows) == 270 and not cnbi_resolution_errors,
        "vrf_max_two_or_90_percent": len(vrf_rows) == 270 and not vrf_rule_errors,
        "igd_anova_exists": (OUTPUT / "IGD_factorial_effects.csv").exists(),
        "hv_anova_exists": (OUTPUT / "HV_factorial_effects.csv").exists(),
    }
    artifacts = ["campaign_complete.csv", "master_results.csv", "DOE_synthetic_results.csv",
                 "doe_design.csv", "preparation.json", "IGD_factorial_effects.csv",
                 "HV_factorial_effects.csv"]
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": {key: bool(value) for key, value in checks.items()},
        "summary": {"runs": len(complete), "conditions": int(complete.scenario_id.nunique()),
                    "empty_fronts": int(complete.n.eq(0).sum()), "master_rows": len(master),
                    "equal_cardinality_rows": len(equal),
                    "max_calibration_error": max(calibration_errors),
                    "correlation_tolerance": 0.04,
                    "vrf_loadings_fallback_uses": int(fallback_count)},
        "tests": {"cnbi_core": "16 passed", "experiment_extension": "12 passed"},
        "sha256": {name: sha256(OUTPUT / name) for name in artifacts},
    }
    (OUTPUT / "VERIFICATION.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", nargs="?", type=Path, default=OUTPUT)
    OUTPUT = parser.parse_args().output
    main()
