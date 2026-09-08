"""Extração conservadora do notebook 03. Ver TRACEABILITY.md e aviso MIT."""


import numpy as np
from scipy.linalg import null_space
from scipy.optimize import minimize
from .config import ALPHA
from .rsm import z, dz
from .combinations import simplex_weights, _nearest_weight_order


def _solve_nbi_base(Bmodel, output_B, indices, Xstar, P, delta, combo_id=0, maxiter=500, max_rescues=8):
    """Resolve NBI local com a formulação do notebook 03.

    Os padrões são SLSQP ``maxiter=500`` e até oito resgates; ambos podem ser
    configurados. Permanecem ``ftol=1e-10``, igualdade <=1e-5, esfera <=1e-8,
    t em [-10,10], vértices exatos, warm starts, baricêntrico e centro. Usa a
    normalização local do notebook 03. Retorna linhas recompostas e contadores.
    """
    indices = np.asarray(indices, int)
    k = len(indices)
    ideal = P.min(1)
    amp = np.maximum(P.max(1) - ideal, 1e-12)
    A = ((P - ideal[:, None]) / amp[:, None]).T
    E = A[1:] - A[:1]
    normal = null_space(E).ravel()
    normal /= np.linalg.norm(normal)
    if normal @ -A.mean(0) < 0:
        normal = -normal
    rows = []
    full = 0
    grad = 0
    warm = None
    for (execution_order, (beta_id, beta)) in enumerate(_nearest_weight_order(simplex_weights(k, delta))):
        phi = beta @ A
        vertex = np.flatnonzero(np.isclose(beta, 1.0, atol=1e-12) & np.isclose(beta.sum(), 1.0, atol=1e-12))
        if len(vertex) == 1:
            x = Xstar[int(vertex[0])].copy()
            Fm = z(x) @ Bmodel
            full += 1
            residual = (Fm - ideal) / amp - phi
            rows.append({'k': k, 'combo': tuple(indices), 'beta_id': beta_id, 'beta': beta.copy(), 'execution_order': execution_order, 'success': bool(np.max(np.abs(residual)) <= 1e-05), 'accepted': bool(np.max(np.abs(residual)) <= 1e-05), 'solver_success': True, 'subproblem_status': 'COMPLETED', 'x': x, 'F_rsm': z(x) @ output_B, 'eq_inf': float(np.max(np.abs(residual))), 'sphere_violation': max(0.0, float(x @ x - ALPHA ** 2)), 'start': 'payoff_anchor_exact', 'attempts': 0, 'attempt_log': []})
            warm = np.r_[x, 0.0]
            continue

        def predict(x):
            nonlocal full
            full += 1
            return (z(x) @ Bmodel - ideal) / amp

        def jacobian(x):
            nonlocal grad
            grad += 1
            return (dz(x).T @ Bmodel).T / amp[:, None]

        def eq(v):
            return predict(v[:3]) - (phi + v[-1] * normal)

        def jeq(v):
            return np.column_stack([jacobian(v[:3]), -normal])

        def sphere(v):
            return ALPHA ** 2 - v[:3] @ v[:3]

        def jsphere(v):
            return np.r_[-2 * v[:3], 0.0]

        def project_t(x):
            nonlocal full
            full += 1
            return float(((z(x) @ Bmodel - ideal) / amp - phi) @ normal)
        starts = []
        seen = set()

        def add(name, x, t=None):
            x = np.asarray(x, float)
            norm = np.linalg.norm(x)
            if norm > ALPHA * (1 + 1e-10):
                return
            if norm > ALPHA:
                x = x * (ALPHA * (1 - 1e-12) / norm)
            v = np.r_[x, np.clip(project_t(x) if t is None else t, -10, 10)]
            key = tuple(np.round(v, 12))
            if key not in seen:
                seen.add(key)
                starts.append((name, v))
        if warm is not None:
            add('warm', warm[:3], warm[-1])
        add('barycentric_anchor', beta @ Xstar)
        for j in np.argsort(-beta):
            add(f'anchor_{int(indices[j])}', Xstar[j])
        add('center', np.zeros(3))
        candidates = []
        attempt_log = []

        def solve(name, v0, attempt):
            r = minimize(lambda v: -v[-1], v0, jac=lambda v: np.r_[np.zeros(3), -1.0], method='SLSQP', bounds=[(-ALPHA, ALPHA)] * 3 + [(-10, 10)], constraints=[{'type': 'eq', 'fun': eq, 'jac': jeq}, {'type': 'ineq', 'fun': sphere, 'jac': jsphere}], options={'ftol': 1e-10, 'maxiter': maxiter, 'disp': False})
            residual = eq(r.x)
            eq_inf = float(np.max(np.abs(residual)))
            violation = max(0.0, float(r.x[:3] @ r.x[:3] - ALPHA ** 2))
            feasible = eq_inf <= 1e-05 and violation <= 1e-08
            candidates.append((bool(r.success), feasible, r, name, attempt, eq_inf, violation))
            attempt_log.append({'attempt': attempt, 'start': name, 'solver_success': bool(r.success), 'eq_inf': eq_inf, 'sphere_violation': violation, 't': float(r.x[-1])})
            return candidates[-1]
        attempt = 0
        for (name, v0) in starts:
            attempt += 1
            candidate = solve(name, v0, attempt)
            if candidate[0] and candidate[1]:
                break
        if not any((c[0] and c[1] for c in candidates)):
            rng = np.random.default_rng(1000003 + 1009 * combo_id + beta_id)
            for rescue in range(max_rescues):
                direction = rng.normal(size=3)
                direction /= np.linalg.norm(direction)
                x = ALPHA * rng.random() ** (1 / 3) * direction
                attempt += 1
                candidate = solve(f'rescue_{rescue + 1}', np.r_[x, np.clip(project_t(x), -10, 10)], attempt)
                if candidate[0] and candidate[1]:
                    break
        chosen = min(candidates, key=lambda c: (0 if c[0] and c[1] else 1, -float(c[2].x[-1]) if c[0] and c[1] else c[5] / 1e-05 + c[6] / 1e-08, c[5], c[6]))
        (solver_success, feasible, r, name, attempt, eq_inf, violation) = chosen
        x = r.x[:3]
        valid_candidate = bool(solver_success and feasible)
        subproblem_status = 'COMPLETED' if valid_candidate else 'NO_FEASIBLE_INTERSECTION'
        rows.append({'k': k, 'combo': tuple(indices), 'beta_id': beta_id, 'beta': beta.copy(), 'execution_order': execution_order, 'success': valid_candidate, 'accepted': valid_candidate, 'solver_success': bool(solver_success), 'subproblem_status': subproblem_status, 'x': x, 'F_rsm': z(x) @ output_B, 'eq_inf': eq_inf, 'sphere_violation': violation, 't': float(r.x[-1]), 'start': name, 'attempts': attempt, 'attempt_log': attempt_log})
        warm = r.x.copy() if valid_candidate else None
    return (rows, full, grad)
