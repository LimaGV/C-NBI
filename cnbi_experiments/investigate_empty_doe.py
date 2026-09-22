"""Read-only sensitivity diagnostic for DOE cases filtered before NBI."""
import argparse
import json
from itertools import combinations, product
from pathlib import Path

import numpy as np
import pandas as pd

from .doe import RSM, design, truth
from .solver import Config, Meter, payoff, uncertainty_pa


CASES = [
    ("doe_nx3_m5_high", 102),
    ("doe_nx3_m5_high", 103),
    ("doe_nx3_m7_high", 105),
    ("doe_nx5_m7_high", 105),
    ("doe_nx5_m7_high", 106),
]


def design_points(nx):
    alpha = 2 ** 0.75
    return np.vstack([
        np.array(list(product([-1.0, 1.0], repeat=nx))),
        alpha * np.eye(nx),
        -alpha * np.eye(nx),
        np.zeros((5, nx)),
    ])


def selection_summary(window, m, nx):
    selected = []
    best_smin = 0.0
    for combo in combinations(range(m), 2):
        c = np.array(combo)
        S = window["scaled"][np.ix_(c, c)].T
        singular = np.linalg.svd(S[1:] - S[:1], compute_uv=False)
        best_smin = max(best_smin, float(singular[-1]))
    for k in range(2, min(m, nx + 1) + 1):
        for combo in combinations(range(m), k):
            c = np.array(combo)
            S = window["scaled"][np.ix_(c, c)].T
            singular = np.linalg.svd(S[1:] - S[:1], compute_uv=False)
            quality = np.inf if singular[-1] <= 1e-12 else singular[0] / singular[-1]
            if singular[-1] > window["floor"] and quality <= window["ceiling"]:
                selected.append(combo)
    return selected, best_smin


def run(output):
    rows = []
    for scenario, seed in CASES:
        anchors = np.load(output / f"{scenario}_anchors.npz")["anchors"]
        nx, m = anchors.shape[1], anchors.shape[0]
        X = design_points(nx)
        F = truth(X, anchors)
        signal_var = F.var(axis=0, ddof=1)
        for target_r2 in (0.95, 0.975, 0.99, 1.0):
            sigma = np.zeros(m) if target_r2 == 1 else np.sqrt(signal_var * (1 - target_r2) / target_r2)
            Y = F + np.random.default_rng(seed).normal(0, sigma, F.shape)
            problem = RSM(anchors, seed)
            problem.Yobs = Y
            problem.B = np.linalg.lstsq(design(X), Y, rcond=None)[0]
            residual = Y - design(X) @ problem.B
            problem.mse = np.sum(residual ** 2, axis=0) / (len(X) - design(X).shape[1])
            meter = Meter(problem, 1000000)
            Xstar, P = payoff(problem, meter, Config(seed=seed, maxiter=100, budget=1000000))
            window = uncertainty_pa(problem, P, Xstar)
            selected, best_pair_smin = selection_summary(window, m, nx)
            fitted = design(X) @ problem.B
            observed_r2 = 1 - np.sum((Y - fitted) ** 2, axis=0) / np.sum((Y - Y.mean(axis=0)) ** 2, axis=0)
            rows.append({
                "scenario_id": scenario,
                "seed": seed,
                "target_r2": target_r2,
                "noise_sd_over_signal_sd": float(np.sqrt((1-target_r2)/target_r2)) if target_r2 < 1 else 0.0,
                "mean_observed_r2": float(np.mean(observed_r2)),
                "min_observed_r2": float(np.min(observed_r2)),
                "d": int(window["d"]),
                "floor": float(window["floor"]),
                "ceiling": float(window["ceiling"]),
                "best_pair_smin": best_pair_smin,
                "selected_combinations": len(selected),
                "selected_by_k": json.dumps({str(k): sum(len(c) == k for c in selected)
                                               for k in range(2, min(m, nx+1)+1)}),
            })
    frame = pd.DataFrame(rows)
    frame.to_csv(output / "empty_doe_noise_sensitivity.csv", index=False)
    return frame


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    print(run(parser.parse_args().output).to_string(index=False))
