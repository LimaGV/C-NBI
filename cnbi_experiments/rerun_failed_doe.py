"""Targeted validation of the multidimensional legacy-style DOE generator."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist

from .doe import RSM, calibrate, master_design
from .pilot import frontier, write_json
from .solver import Config, run_cnbi


CASES = [
    ("doe_nx3_m5_high", 102),
    ("doe_nx3_m5_high", 103),
    ("doe_nx3_m7_high", 105),
    ("doe_nx5_m7_high", 105),
    ("doe_nx5_m7_high", 106),
]


def run(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    design = pd.DataFrame(master_design()).drop_duplicates("scenario_id").set_index("scenario_id")
    audits = {}
    for sid in dict(CASES):
        row = design.loc[sid]
        anchors, audit = calibrate(int(row.nx), int(row.m), row.dependence_level, int(row.geometry_seed))
        np.savez_compressed(output/f"{sid}_anchors.npz", anchors=anchors)
        distances = pdist(anchors)
        audit["anchor_distance_min"] = float(distances.min())
        audit["anchor_distance_median"] = float(np.median(distances))
        audit["anchor_distance_max"] = float(distances.max())
        audits[sid] = audit
        print("CALIBRATED", sid, audit["achieved"], audit["anchor_distance_median"], flush=True)
    write_json(output/"calibration.json", audits)

    rows = []
    for sid, seed in CASES:
        anchors = np.load(output/f"{sid}_anchors.npz")["anchors"]
        result = run_cnbi(RSM(anchors, seed), Config(seed=seed, budget=None), "spectral")
        X, F = frontier(RSM(anchors, seed), result)
        prefix = f"{sid}_seed{seed}_CNBI_spectral"
        write_json(output/f"{prefix}.json", result)
        np.savez_compressed(output/f"{prefix}_front.npz", X=X, F=F)
        rows.append({"scenario_id": sid, "seed": seed, "status": result["status"],
                     "evaluations": result["evaluations"], "selected_combinations": result["selected_combinations"],
                     "processed_subproblems": result["processed_subproblems"],
                     "feasible_subproblems": result["feasible_subproblems"], "front_size": len(F),
                     "d": result["diagnostics"].get("d"), "floor": result["diagnostics"].get("floor"),
                     "ceiling": result["diagnostics"].get("ceiling")})
        print("RESULT", sid, seed, result["status"], len(F), flush=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(output/"targeted_results.csv", index=False)
    passed = bool((frame.front_size > 0).all())
    write_json(output/"status.json", {"passed": passed, "cases": len(frame),
                                       "generator": "multidimensional extension of notebook 01"})
    return passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.output) else 1)
