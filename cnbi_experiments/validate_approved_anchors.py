"""Preflight every seed before replacing DOE checkpoint geometries."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .doe import RSM
from .pilot import frontier
from .solver import Config, run_cnbi


def run(source: Path):
    rows = []
    for anchor_path in sorted(source.glob("doe_*_anchors.npz")):
        scenario_id = anchor_path.name.removesuffix("_anchors.npz")
        anchors = np.load(anchor_path)["anchors"]
        for seed in range(101, 111):
            problem = RSM(anchors, seed)
            result = run_cnbi(problem, Config(seed=seed, budget=None), "spectral")
            _, front = frontier(problem, result)
            rows.append({"scenario_id": scenario_id, "seed": seed,
                         "status": result["status"], "front_size": len(front)})
            print(scenario_id, seed, result["status"], len(front), flush=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(source / "all_seed_preflight.csv", index=False)
    return bool(len(frame) and frame.front_size.gt(0).all())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.source) else 1)
