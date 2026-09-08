"""Extração conservadora do notebook 03. Ver TRACEABILITY.md e aviso MIT."""


import numpy as np
from scipy.optimize import minimize
from .config import ALPHA
from .rsm import z, dz


def canonical_payoff_starts():
    """Retorna cópias dos sete pontos iniciais normativos do notebook 03."""
    return [np.zeros(3), *list(np.eye(3) * (.99 * ALPHA)), *list(-np.eye(3) * (.99 * ALPHA))]


def individual_payoff(B, starts=None, maxiter=500):
    """Calcula ótimos individuais e payoff pública de B, já em minimização.

    O padrão usa os sete starts normativos e ``maxiter=500``. Para alterar a
    quantidade, forneça explicitamente ``starts``; seu comprimento define o
    número de pontos sem introduzir uma nova regra de geração. A jacobiana
    analítica, ``ftol=1e-11`` e a factibilidade até ``1e-7`` são preservadas.
    Retorna Xstar (m,3) e P (m,m), com objetivos nas linhas. Os contadores
    históricos permanecem em atributos da função; o uso deve ser sequencial.
    """
    m = B.shape[1]
    Xs = []
    cols = []
    evaluation_count = 0
    gradient_count = 0
    if starts is None:
        starts = canonical_payoff_starts()
    else:
        starts = [np.asarray(start, float) for start in starts]
        if not starts:
            raise ValueError('starts precisa conter ao menos um ponto inicial')
        if any(start.shape != (3,) for start in starts):
            raise ValueError('cada ponto inicial da payoff precisa ter shape (3,)')
    for j in range(m):
        candidates = []
        for x0 in starts:

            def objective(x):
                nonlocal evaluation_count
                evaluation_count += 1
                return float(z(x) @ B[:, j])

            def gradient(x):
                nonlocal gradient_count
                gradient_count += 1
                return dz(x).T @ B[:, j]
            r = minimize(objective, x0, jac=gradient, method='SLSQP', bounds=[(-ALPHA, ALPHA)] * 3, constraints={'type': 'ineq', 'fun': lambda x: ALPHA ** 2 - x @ x}, options={'ftol': 1e-11, 'maxiter': maxiter})
            candidates.append(r)
        valid = [r for r in candidates if r.success and r.x @ r.x <= ALPHA ** 2 + 1e-07]
        assert valid, f'Nenhum ótimo individual válido para objetivo {j}'
        best = min(valid, key=lambda r: float(r.fun))
        Xs.append(best.x)
        cols.append(z(best.x) @ B)
    P = np.column_stack(cols)
    individual_payoff.last_evaluations = evaluation_count
    individual_payoff.last_gradient_evaluations = gradient_count
    return (np.asarray(Xs), P)
