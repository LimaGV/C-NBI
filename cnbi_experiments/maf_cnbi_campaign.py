"""Checkpointed MaF benchmark containing only unlimited CNBI runs."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import os
from pathlib import Path
import shutil

for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "1"

import numpy as np
import pandas as pd

from .benchmarks import MaF
from .campaign import MAF_SETTINGS, _reference
from .pilot import frontier, metrics, write_json
from .solver import Config, run_cnbi


def worker(task):
    number, m, seed = task
    problem = MaF(number, m)
    result = run_cnbi(problem, Config(budget=None, seed=seed), "spectral")
    x, f = frontier(problem, result)
    assert result.get("budget_limit") is None
    assert np.isfinite(x).all() and np.isfinite(f).all()
    assert problem.feasible(x).all()
    return number, m, seed, result, x, f


def run(output: Path, reference_source: Path | None, workers: int):
    output.mkdir(parents=True, exist_ok=True)
    complete_path = output / "campaign_complete.csv"
    complete = pd.read_csv(complete_path) if complete_path.exists() else pd.DataFrame()
    done = set()
    if len(complete):
        done = set(zip(complete.scenario_id, complete.seed.astype(int)))

    for number, m in MAF_SETTINGS:
        sid = f"maf{number}_m{m}"
        target = output / f"{sid}_reference.npz"
        source = reference_source / f"{sid}_reference.npz" if reference_source else None
        if not target.exists() and source is not None and source.exists():
            shutil.copy2(source, target)
        _reference(MaF(number, m), sid, output)

    tasks = [
        (number, m, seed)
        for number, m in MAF_SETTINGS
        for seed in range(101, 111)
        if (f"maf{number}_m{m}", seed) not in done
    ]

    def save(item):
        nonlocal complete
        number, m, seed, result, x, f = item
        sid = f"maf{number}_m{m}"
        problem = MaF(number, m)
        reference, ideal, amplitude = _reference(problem, sid, output)
        prefix = f"{sid}_seed{seed}_CNBI_spectral"
        write_json(output / f"{prefix}.json", result)
        np.savez_compressed(output / f"{prefix}_front.npz", X=x, F=f)
        row = {
            "scenario_id": sid,
            "seed": seed,
            "nx": problem.nx,
            "m": problem.m,
            "method": "CNBI_spectral",
            "comparison": "complete",
            "n": len(f),
            "budget": None,
            "rank": result["diagnostics"].get("d"),
            "status": result["status"],
            "evaluations": result["evaluations"],
            "seconds": result["seconds"],
            "diagnostic_seconds": result["diagnostic_seconds"],
            "candidate_combinations": result.get("candidate_combinations"),
            "selected_combinations": result.get("selected_combinations"),
            "potential_subproblems": result.get("potential_subproblems"),
            "processed_subproblems": result.get("processed_subproblems"),
            "feasible_subproblems": result.get("feasible_subproblems"),
            **metrics((f - ideal) / amplitude, (reference - ideal) / amplitude, seed),
        }
        complete = pd.concat([complete, pd.DataFrame([row])], ignore_index=True)
        complete.to_csv(complete_path, index=False)
        done.add((sid, seed))
        write_json(output / "campaign_progress.json", {
            "completed": len(done), "expected": 130,
            "last": {"scenario_id": sid, "seed": seed,
                     "status": result["status"],
                     "evaluations": result["evaluations"], "front": len(f)},
        })
        print("RESULT", len(done), "/ 130", sid, seed,
              result["status"], result["evaluations"], len(f), flush=True)

    if workers == 1:
        for task in tasks:
            save(worker(task))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(worker, task) for task in tasks]
            for future in as_completed(futures):
                save(future.result())

    complete = complete.sort_values(["scenario_id", "seed"]).reset_index(drop=True)
    complete.to_csv(complete_path, index=False)
    complete.to_csv(output / "master_results.csv", index=False)
    status = {
        "status": "COMPLETED",
        "runs": len(complete),
        "expected_runs": 130,
        "settings": len(MAF_SETTINGS),
        "seeds": 10,
        "methods": ["CNBI_spectral"],
        "budget": "unlimited",
        "separate_from_synthetic_doe": True,
        "empty_fronts": int(complete.n.eq(0).sum()),
    }
    (output / "campaign_status.json").write_text(
        json.dumps(status, indent=2), encoding="utf-8"
    )
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=Path("experimental_results/maf_cnbi_unlimited"))
    parser.add_argument("--reference-source", type=Path,
                        default=Path("experimental_results/full_campaign_vrf_faithful_final"))
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    run(args.output, args.reference_source, args.workers)
