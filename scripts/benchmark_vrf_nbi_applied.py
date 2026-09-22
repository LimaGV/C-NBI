from __future__ import annotations

from itertools import product
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from factor_analyzer import FactorAnalyzer
from scipy.linalg import null_space
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler


ALPHA = 2**0.75
DATA = Path(
    r"C:\Users\gabri\Documents\Dissertação\04_CODIGOS\notebooks\files\VRF_artigo.xlsx"
)
REFERENCE = Path(
    r"C:\Users\gabri\Documents\Dissertação\04_CODIGOS\notebooks\files\VRF_Pareto.xlsx"
)
XCOLS = ["cs", "f", "md"]
YCOLS = ["T", "MTTF", "WR", "Ra", "Rt", "Kp", "ROI", "OEE"]


def z(x):
    x1, x2, x3 = np.asarray(x, float)
    return np.array(
        [1, x1, x2, x3, x1 * x1, x2 * x2, x3 * x3, x1 * x2, x1 * x3, x2 * x3]
    )


def dz(x):
    x1, x2, x3 = np.asarray(x, float)
    return np.array(
        [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [2 * x1, 0, 0],
            [0, 2 * x2, 0],
            [0, 0, 2 * x3],
            [x2, x1, 0],
            [x3, 0, x1],
            [0, x3, x2],
        ]
    )


def orient_factors(loadings, scores):
    loadings = np.asarray(loadings, float).copy()
    scores = np.asarray(scores, float).copy()
    for q in range(loadings.shape[1]):
        j = int(np.argmax(np.abs(loadings[:, q])))
        sign = 1.0 if loadings[j, q] >= 0 else -1.0
        loadings[:, q] *= sign
        scores[:, q] *= sign
    return loadings, scores


def individual_payoff(B):
    xstars = []
    columns = []
    starts = [np.zeros(3), *list(np.eye(3) * (0.99 * ALPHA)), *list(-np.eye(3) * (0.99 * ALPHA))]
    for j in range(B.shape[1]):
        candidates = []
        for x0 in starts:
            result = minimize(
                lambda x, j=j: float(z(x) @ B[:, j]),
                x0,
                jac=lambda x, j=j: dz(x).T @ B[:, j],
                method="SLSQP",
                bounds=[(-ALPHA, ALPHA)] * 3,
                constraints={"type": "ineq", "fun": lambda x: ALPHA**2 - x @ x},
                options={"ftol": 1e-11, "maxiter": 500},
            )
            candidates.append(result)
        valid = [
            result
            for result in candidates
            if result.success and result.x @ result.x <= ALPHA**2 + 1e-7
        ]
        if not valid:
            raise RuntimeError(f"Payoff sem ótimo válido para o fator {j + 1}")
        best = min(valid, key=lambda result: float(result.fun))
        xstars.append(best.x)
        columns.append(z(best.x) @ B)
    return np.asarray(xstars), np.column_stack(columns)


def simplex_weights(k=3, delta=0.10):
    p = round(1 / delta)
    return np.array([q for q in product(range(p + 1), repeat=k) if sum(q) == p], float) / p


def nearest_weight_order(weights):
    weights = np.asarray(weights, float)
    remaining = list(range(len(weights)))
    order = [remaining.pop(0)]
    while remaining:
        last = weights[order[-1]]
        pick = min(remaining, key=lambda i: (float(np.linalg.norm(weights[i] - last)), i))
        remaining.remove(pick)
        order.append(pick)
    return [(i, weights[i]) for i in order]


def solve_vrf_subproblems(B, xstars, payoff):
    ideal = payoff.min(1)
    amplitude = np.maximum(payoff.max(1) - ideal, 1e-12)
    anchors = ((payoff - ideal[:, None]) / amplitude[:, None]).T
    edges = anchors[1:] - anchors[:1]
    normal = null_space(edges).ravel()
    normal /= np.linalg.norm(normal)
    if normal @ (-anchors.mean(0)) < 0:
        normal = -normal

    rows = []
    warm = None
    for beta_id, beta in nearest_weight_order(simplex_weights()):
        phi = beta @ anchors
        vertex = np.flatnonzero(
            np.isclose(beta, 1.0, atol=1e-12) & np.isclose(beta.sum(), 1.0, atol=1e-12)
        )
        if len(vertex) == 1:
            x = xstars[int(vertex[0])].copy()
            residual = (z(x) @ B - ideal) / amplitude - phi
            rows.append((x, np.max(np.abs(residual)), 0.0, True))
            warm = np.r_[x, 0.0]
            continue

        def prediction(x):
            return (z(x) @ B - ideal) / amplitude

        def jacobian(x):
            return (dz(x).T @ B).T / amplitude[:, None]

        def equality(v):
            return prediction(v[:3]) - (phi + v[-1] * normal)

        def equality_jac(v):
            return np.column_stack([jacobian(v[:3]), -normal])

        def sphere(v):
            return ALPHA**2 - v[:3] @ v[:3]

        def sphere_jac(v):
            return np.r_[-2 * v[:3], 0.0]

        def projected_t(x):
            return float((prediction(x) - phi) @ normal)

        starts = []
        if warm is not None:
            starts.append(("warm", warm.copy()))
        barycenter = beta @ xstars
        starts.append(("barycentric", np.r_[barycenter, np.clip(projected_t(barycenter), -10, 10)]))
        for j in np.argsort(-beta):
            x = xstars[j]
            starts.append((f"anchor_{j}", np.r_[x, np.clip(projected_t(x), -10, 10)]))
        starts.append(("center", np.r_[np.zeros(3), np.clip(projected_t(np.zeros(3)), -10, 10)]))

        candidates = []
        for name, start in starts:
            result = minimize(
                lambda v: -v[-1],
                start,
                jac=lambda v: np.r_[np.zeros(3), -1.0],
                method="SLSQP",
                bounds=[(-ALPHA, ALPHA)] * 3 + [(-10, 10)],
                constraints=[
                    {"type": "eq", "fun": equality, "jac": equality_jac},
                    {"type": "ineq", "fun": sphere, "jac": sphere_jac},
                ],
                options={"ftol": 1e-10, "maxiter": 500, "disp": False},
            )
            eq_inf = float(np.max(np.abs(equality(result.x))))
            violation = max(0.0, float(result.x[:3] @ result.x[:3] - ALPHA**2))
            feasible = eq_inf <= 1e-5 and violation <= 1e-8
            candidates.append((result.success and feasible, result, eq_inf, violation, name))
            if result.success and feasible:
                break

        if not any(candidate[0] for candidate in candidates):
            rng = np.random.default_rng(1_000_003 + beta_id)
            for rescue in range(8):
                direction = rng.normal(size=3)
                direction /= np.linalg.norm(direction)
                x = ALPHA * (rng.random() ** (1 / 3)) * direction
                start = np.r_[x, np.clip(projected_t(x), -10, 10)]
                result = minimize(
                    lambda v: -v[-1],
                    start,
                    jac=lambda v: np.r_[np.zeros(3), -1.0],
                    method="SLSQP",
                    bounds=[(-ALPHA, ALPHA)] * 3 + [(-10, 10)],
                    constraints=[
                        {"type": "eq", "fun": equality, "jac": equality_jac},
                        {"type": "ineq", "fun": sphere, "jac": sphere_jac},
                    ],
                    options={"ftol": 1e-10, "maxiter": 500, "disp": False},
                )
                eq_inf = float(np.max(np.abs(equality(result.x))))
                violation = max(0.0, float(result.x[:3] @ result.x[:3] - ALPHA**2))
                feasible = eq_inf <= 1e-5 and violation <= 1e-8
                candidates.append((result.success and feasible, result, eq_inf, violation, f"rescue_{rescue}"))
                if result.success and feasible:
                    break

        chosen = min(candidates, key=lambda item: (not item[0], item[2], item[3]))
        valid, result, eq_inf, violation, _ = chosen
        rows.append((result.x[:3], eq_inf, violation, bool(valid)))
        warm = result.x.copy() if valid else None
    return rows


def prepare_problem():
    data = pd.read_excel(DATA)
    reference = pd.read_excel(REFERENCE)
    if len(reference) != 66 or not {"w1", "w2", "w3"}.issubset(reference.columns):
        raise ValueError("A referência VRF aplicada não contém os 66 pesos de três fatores.")

    design = np.vstack([z(x) for x in data[XCOLS].to_numpy(float)])
    scaler = StandardScaler()
    standardized = scaler.fit_transform(data[YCOLS])
    fa = FactorAnalyzer(n_factors=3, rotation="varimax", method="principal")
    scores_raw = fa.fit_transform(standardized)
    _, scores = orient_factors(fa.loadings_, scores_raw)
    factor_coefficients = np.linalg.lstsq(design, scores, rcond=None)[0]
    xstars, payoff = individual_payoff(factor_coefficients)
    return factor_coefficients, xstars, payoff


if __name__ == "__main__":
    B, xstars, payoff = prepare_problem()
    for repetition in range(1, 11):
        start = perf_counter()
        rows = solve_vrf_subproblems(B, xstars, payoff)
        elapsed = perf_counter() - start
        success = sum(row[3] for row in rows)
        max_eq = max(row[1] for row in rows)
        max_sphere = max(row[2] for row in rows)
        print(
            f"{repetition},{elapsed:.9f},{len(rows)},{success},{max_eq:.3e},{max_sphere:.3e}",
            flush=True,
        )
