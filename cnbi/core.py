"""Extração conservadora do notebook 03. Ver TRACEABILITY.md e aviso MIT."""


import numpy as np
from itertools import combinations
from .config import DELTA_BY_K
from .spectral import parallel_analysis
from .nbi import _solve_nbi_base


def cnbi(B, P, Xstar, mse, XtX_inv, maxiter=500, max_rescues=8):
    """Executa o núcleo combinatório e sempre retorna candidatos brutos.

    Entradas: B (10,m), P (m,m), Xstar (m,3), mse (m,) e XtX_inv (10,10),
    todos no sentido de minimização. ``maxiter=500`` e ``max_rescues=8`` são
    os padrões configuráveis do NBI. Não aplica deduplicação nem Pareto.
    """
    pa = parallel_analysis(P, Xstar, mse, XtX_inv, nmc=2000, seed=777)
    m = B.shape[1]
    results = []
    full = 0
    grad = 0
    combo_id = 0
    for k in range(2, min(m, 4) + 1):
        for combo in combinations(range(m), k):
            combo = np.asarray(combo, int)
            A = pa['scaled'][np.ix_(combo, combo)].T
            singular = np.linalg.svd(A[1:] - A[:1], compute_uv=False)
            quality = np.inf if singular[-1] <= 1e-12 else singular[0] / singular[-1]
            if not (singular[-1] > pa['floor'] and quality <= pa['ceiling']):
                continue
            (rows, nfull, ngrad) = _solve_nbi_base(B[:, combo], B, combo, Xstar[combo], P[np.ix_(combo, combo)], DELTA_BY_K[k], combo_id, maxiter=maxiter, max_rescues=max_rescues)
            results.extend(rows)
            full += nfull
            grad += ngrad
            combo_id += 1
    pa['rsm_evaluations'] = full
    pa['gradient_evaluations'] = grad
    return (results, pa)
