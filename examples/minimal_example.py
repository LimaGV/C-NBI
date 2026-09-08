"""Exemplo mínimo: entrada RSM -> CNBI -> fronteira RSM não dominada -> CSV.

Execute na raiz da candidata:
    python examples/minimal_example.py
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cnbi import cnbi, individual_payoff, postprocess_frontier  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payoff-maxiter", type=int, default=500)
    parser.add_argument("--nbi-maxiter", type=int, default=500)
    parser.add_argument("--max-rescues", type=int, default=8)
    parser.add_argument("--duplicate-tolerance", type=float, default=1e-5)
    parser.add_argument("--dominance-tolerance", type=float, default=1e-10)
    parser.add_argument("--no-postprocess", action="store_true")
    args = parser.parse_args()
    payload = json.loads((ROOT / "examples" / "data" / "rsm_input.json").read_text(encoding="utf-8"))
    B = np.asarray(payload["B"], dtype=float)
    mse = np.asarray(payload["mse"], dtype=float)
    xtx_inv = np.asarray(payload["XtX_inv"], dtype=float)

    xstar, payoff = individual_payoff(B, maxiter=args.payoff_maxiter)
    candidates, diagnostic = cnbi(
        B, payoff, xstar, mse, xtx_inv,
        maxiter=args.nbi_maxiter, max_rescues=args.max_rescues,
    )
    accepted = [row for row in candidates if row["accepted"]]

    output = ROOT / "examples" / "output"
    output.mkdir(exist_ok=True)
    raw_path = output / "cnbi_candidates_raw.csv"
    objective_names = [f"f{i+1}" for i in range(B.shape[1])]
    with raw_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow([
            "accepted", "status", "k", "combination", "beta",
            "x1", "x2", "x3", *objective_names,
        ])
        for row in candidates:
            writer.writerow([
                row["accepted"], row["subproblem_status"], row["k"],
                json.dumps([int(value) for value in row["combo"]]),
                json.dumps(row["beta"].tolist()),
                *row["x"], *row["F_rsm"],
            ])

    filtered = None
    frontier_path = None
    if not args.no_postprocess and accepted:
        X = np.vstack([row["x"] for row in accepted])
        F_rsm = np.vstack([row["F_rsm"] for row in accepted])
        filtered = postprocess_frontier(
            X, F_rsm,
            duplicate_tolerance=args.duplicate_tolerance,
            dominance_tolerance=args.dominance_tolerance,
        )
        frontier_path = output / "cnbi_frontier_estimated_rsm.csv"
        with frontier_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["x1", "x2", "x3", *objective_names])
            writer.writerows(np.column_stack([filtered["X"], filtered["F"]]))

    summary = {
        "input": payload["source_label"],
        "raw_candidates": len(candidates),
        "accepted_candidates": len(accepted),
        "estimated_frontier_rows": None if filtered is None else filtered["output_count"],
        "parallel_dimension": diagnostic["d"],
        "rsm_evaluations_cnbi": diagnostic["rsm_evaluations"],
        "gradient_evaluations_cnbi": diagnostic["gradient_evaluations"],
        "raw_output": raw_path.relative_to(ROOT).as_posix(),
        "estimated_frontier_output": None if frontier_path is None else frontier_path.relative_to(ROOT).as_posix(),
        "raw_candidates_always_preserved": True,
        "postprocess_enabled": not args.no_postprocess,
        "duplicate_tolerance": args.duplicate_tolerance,
        "dominance_tolerance": args.dominance_tolerance,
        "payoff_maxiter": args.payoff_maxiter,
        "nbi_maxiter": args.nbi_maxiter,
        "max_rescues": args.max_rescues,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
