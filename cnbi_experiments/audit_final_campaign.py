"""Independent integrity checks for a completed DOE campaign."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .comparators import ea_budget


def run(output: Path):
    complete = pd.read_csv(output / "campaign_complete.csv")
    regular = complete.method.isin(["CNBI_spectral", "VRF-NBI"])
    evolutionary = complete.method.isin(["NSGA-III", "MOEA/D"])
    expected_budgets = complete.loc[evolutionary, "m"].map(ea_budget)

    bad_fronts = []
    for row in complete.itertuples(index=False):
        method_file = row.method.replace("/", "_")
        path = output / f"{row.scenario_id}_seed{row.seed}_{method_file}_front.npz"
        try:
            with np.load(path) as front:
                x = front["X"]
                f = front["F"]
                valid = (
                    x.shape == (int(row.n), int(row.nx))
                    and f.shape == (int(row.n), int(row.m))
                    and np.isfinite(x).all()
                    and np.isfinite(f).all()
                )
        except Exception:
            valid = False
        if not valid:
            bad_fronts.append(f"{row.scenario_id}/seed{row.seed}/{row.method}")

    tuning_errors = []
    for row in complete.loc[evolutionary].itertuples(index=False):
        method_file = row.method.replace("/", "_")
        path = output / f"{row.scenario_id}_seed{row.seed}_{method_file}.json"
        with path.open("rb") as handle:
            handle.seek(max(0, path.stat().st_size - 131072))
            tail = handle.read().decode("utf-8", errors="ignore")
        if '"tuning": "calibration_file"' not in tail:
            tuning_errors.append(f"{row.scenario_id}/seed{row.seed}/{row.method}")

    checks = {
        "1080_completed_runs": len(complete) == 1080 and complete.status.eq("COMPLETED").all(),
        "no_cnbi_all": not complete.method.eq("CNBI_all").any(),
        "cnbi_and_vrf_unlimited": complete.loc[regular, "budget"].isna().all(),
        "ea_budget_matches_rule": np.array_equal(
            complete.loc[evolutionary, "budget"].to_numpy(dtype=int),
            expected_budgets.to_numpy(dtype=int),
        ),
        "ea_never_exceeds_budget": (
            complete.loc[evolutionary, "evaluations"]
            <= complete.loc[evolutionary, "budget"]
        ).all(),
        "ea_uses_calibration_file": not tuning_errors,
        "all_front_files_finite_and_dimensionally_valid": not bad_fronts,
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": {key: bool(value) for key, value in checks.items()},
        "errors": {"fronts": bad_fronts, "ea_tuning": tuning_errors},
    }
    (output / "CAMPAIGN_AUDIT.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    run(parser.parse_args().output)
