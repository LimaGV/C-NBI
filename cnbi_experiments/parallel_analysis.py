"""Seeded nonparametric Horn PA and explicit bridge to the legacy CHIM window."""
import time
import numpy as np


def sequential_rank(observed, thresholds):
    passed = np.asarray(observed) > np.asarray(thresholds)
    failed = np.flatnonzero(~passed)
    return int(failed[0]) if len(failed) else len(passed)


def permutation_pa(F, B=1000, alpha=.95, seed=777):
    t0 = time.perf_counter()
    F = np.asarray(F, float)
    if F.ndim != 2 or min(F.shape) < 2 or not np.isfinite(F).all():
        raise ValueError('PA requires a finite N x M matrix, N,M >=2')
    if B < 1 or not 0 < alpha < 1:
        raise ValueError('Invalid B/alpha')
    sd = F.std(axis=0, ddof=1)
    if np.any(sd <= 0):
        raise ValueError('Constant objectives: correlation undefined; no silent removal')
    Z = (F-F.mean(axis=0))/sd
    def spectrum(A):
        return np.linalg.eigvalsh(A.T@A/(len(A)-1))[::-1]
    observed = spectrum(Z)
    rng = np.random.default_rng(seed)
    null = np.empty((B, F.shape[1]))
    for b in range(B):
        permuted = np.column_stack([rng.permutation(Z[:, j]) for j in range(F.shape[1])])
        null[b] = spectrum(permuted)
    thresholds = np.quantile(null, alpha, axis=0, method='linear')
    return dict(rank=sequential_rank(observed, thresholds), observed=observed,
                thresholds=thresholds, null_spectra=null, B=B, alpha=alpha, seed=seed,
                N=len(F), seconds=time.perf_counter()-t0, mode='permutation_sequential')


def payoff_window(P, rank):
    """Approved experimental bridge: rank from Horn, scale from payoff SVD.

    Invalid/unsupported ranks are errors, never clamped to 1. Numerical
    degeneracy uses the legacy 1e-12 guard, not an invented filtering threshold.
    """
    P = np.asarray(P, float)
    amp = P.max(1)-P.min(1)
    scaled = (P-P.min(1)[:, None])/np.where(amp > 1e-12, amp, 1)[:, None]
    A = scaled.T
    s = np.linalg.svd(A[1:]-A[:1], compute_uv=False)
    if not 1 <= rank <= len(s) or s[rank-1] <= 1e-12:
        raise ValueError(f'Horn rank {rank} incompatible with payoff spectrum {s.tolist()}')
    return dict(d=rank, s=s, floor=float(s[rank]) if rank < len(s) else 0.,
                ceiling=float(s[0]/s[rank-1]), scaled=scaled, mode='horn_rank_payoff_window')
