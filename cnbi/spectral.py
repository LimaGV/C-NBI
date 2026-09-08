"""Extração conservadora do notebook 03. Ver TRACEABILITY.md e aviso MIT."""


import numpy as np
from .rsm import z


def parallel_analysis(P, Xstar, mse, XtX_inv, nmc=2000, seed=777):
    """Diagnóstico global legado independente. P (m,m), Xstar (m,3), mse (m,), XtX_inv (10,10); retorna d,s,p95,floor,ceiling,scaled. h=zᵀXtX_inv z; ruído sqrt(h*MSE)/amplitude; SVD das diferenças de linhas. Padrões nmc=2000, seed=777; p95, piso sigma[d], teto sigma[0]/sigma[d-1]. Amplitude <=1e-12 vira 1; d>=1. Ver TRACEABILITY.md para hipóteses."""
    ideal = P.min(1)
    nadir = P.max(1)
    amp = np.where(nadir - ideal > 1e-12, nadir - ideal, 1)
    Ps = (P - ideal[:, None]) / amp[:, None]
    A = Ps.T
    assert np.allclose(A.T, Ps)
    E = A[1:] - A[:1]
    s = np.linalg.svd(E, compute_uv=False)
    h = np.einsum('ij,jk,ik->i', np.vstack([z(x) for x in Xstar]), XtX_inv, np.vstack([z(x) for x in Xstar]))
    sd = np.sqrt(np.outer(h, mse)) / amp[None, :]
    rng = np.random.default_rng(seed)
    sn = np.empty((nmc, len(s)))
    for b in range(nmc):
        R = rng.normal(0, sd)
        sn[b] = np.linalg.svd(R[1:] - R[:1], compute_uv=False)
    p95 = np.percentile(sn, 95, axis=0)
    d = max(1, int(np.sum(s > p95)))
    floor = float(s[d]) if d < len(s) else 0.0
    ceiling = float(s[0] / s[d - 1])
    return {'d': d, 's': s, 'p95': p95, 'floor': floor, 'ceiling': ceiling, 'scaled': Ps}
