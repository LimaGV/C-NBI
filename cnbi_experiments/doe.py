"""Dimension extension of notebook 01's anchor generator, CCD and quadratic RSM.

Same distance objectives, logistic radii, penalties, target bands and noise law.
The calibration covariance is evaluated from sufficient statistics, avoiding
rebuilding a 8192 x M objective array at every optimizer finite difference.
"""
from itertools import combinations, product
from math import comb
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import Delaunay
from scipy.stats import norm, qmc
from cnbi.config import ALPHA
from cnbi.rsm import z, dz

TARGETS = dict(low=.25, medium=.60, high=.85)
CORRELATION_TOLERANCE = .04


def design(X):
    X = np.atleast_2d(X)
    if X.shape[1] == 3:
        return np.vstack([z(x) for x in X])
    return np.column_stack([np.ones(len(X)), X, X*X,
                            *[X[:, i]*X[:, j] for i, j in combinations(range(X.shape[1]), 2)]])


def design_jac(x):
    if len(x) == 3:
        return dz(x)
    n = len(x)
    cross = []
    for i, j in combinations(range(n), 2):
        row = np.zeros(n); row[i] = x[j]; row[j] = x[i]; cross.append(row)
    return np.vstack([np.zeros(n), np.eye(n), 2*np.diag(x), cross])


def ball(n, nx, seed):
    rng = np.random.default_rng(seed)
    V = rng.normal(size=(n, nx))
    return ALPHA*V/np.linalg.norm(V, axis=1, keepdims=True)*rng.random((n, 1))**(1/nx)


def sobol_ball(n, nx, seed):
    """Dimension-independent extension of notebook 01's Sobol rejection sampler."""
    engine = qmc.Sobol(nx, scramble=True, seed=seed)
    chunks = []
    total = 0
    block_power = max(10, int(np.ceil(np.log2(max(n, 2)))))
    first = True
    while total < n:
        U = engine.random_base2(block_power) if first else engine.random(2**block_power)
        first = False
        Y = 2*U-1
        Y = Y[np.einsum('ij,ij->i', Y, Y) <= 1]
        chunks.append(Y)
        total += len(Y)
    return np.vstack(chunks)[:n]*ALPHA


def regular_directions(m, nx, phase=0.):
    """Regular/quasi-regular n-D analogue of the original tetrahedron/Fibonacci starts."""
    if m == nx+1:
        centered = np.eye(m)-np.ones((m, m))/m
        U, _, _ = np.linalg.svd(centered)
        directions = U[:, :nx]
    elif nx == 2:
        angles = 2*np.pi*(np.arange(m)/m+phase/m)
        directions = np.column_stack([np.cos(angles), np.sin(angles)])
    elif nx == 3:
        i = np.arange(m); zc = 1-2*(i+.5)/m
        phi = np.pi*(1+np.sqrt(5))*(i+phase)
        radius = np.sqrt(1-zc*zc)
        directions = np.column_stack([radius*np.cos(phi), radius*np.sin(phi), zc])
    else:
        # A scrambled Sobol normal map is the direct n-D quasi-uniform sphere
        # counterpart of the original 3-D Fibonacci sphere.
        seed = 104729+int(round(1000003*phase))+1009*m+9176*nx
        engine = qmc.Sobol(nx, scramble=True, seed=seed)
        U = engine.random_base2(int(np.ceil(np.log2(m))))[:m]
        directions = norm.ppf(np.clip(U, 1e-12, 1-1e-12))
    return directions/np.maximum(np.linalg.norm(directions, axis=1, keepdims=True), 1e-12)


def truth(X, A):
    return np.sum((np.atleast_2d(X)[:, None, :]-A[None, :, :])**2, axis=2)


def dependence(F):
    C = np.corrcoef(F, rowvar=False)
    return float(np.abs(C[np.triu_indices(len(C), 1)]).mean())


def calibrate(nx, m, level, seed, starts=48, maxiter=350, prefer_spread=False):
    target = TARGETS[level]
    X = sobol_ball(50000, nx, 2026)
    Xsearch = X[:8192]
    search_cov = np.cov(np.column_stack([np.sum(Xsearch**2, axis=1), Xsearch]), rowvar=False)
    audit_cov = np.cov(np.column_stack([np.sum(X**2, axis=1), X]), rowvar=False)
    def rho(A, covariance):
        # Squared-distance objectives equal ||x||² - 2*a_j'x plus a
        # constant. Their correlation therefore follows exactly from these
        # sufficient statistics; this avoids rebuilding the full N x M array.
        Q = np.vstack([np.ones(m), -2*A.T])
        covariance_F = Q.T@covariance@Q
        scale = np.sqrt(np.outer(np.diag(covariance_F), np.diag(covariance_F)))
        correlation = covariance_F/scale
        return float(np.abs(correlation[np.triu_indices(m, 1)]).mean())
    def decode(v):
        R = v.reshape(m, nx+1)
        direction = R[:, :nx]/np.maximum(np.linalg.norm(R[:, :nx], axis=1, keepdims=True), 1e-12)
        radii = .18*ALPHA+.70*ALPHA/(1+np.exp(-np.clip(R[:, nx], -700, 700)))
        return direction*radii[:, None]
    def quality(A, separation_fraction=.10):
        distances = np.linalg.norm(A[:, None]-A[None], axis=2)+np.eye(m)*1e6
        sep = distances.min()
        s = np.linalg.svd(A-A.mean(0), compute_uv=False)
        penalty = 500*max(0., separation_fraction*ALPHA-sep)**2+500*max(0., .025*ALPHA-s[-1])**2
        return sep, s, penalty
    rng = np.random.default_rng(seed+100*m+round(100*target))
    best = None; attempts = []; accepted = []
    for attempt in range(starts):
        directions = regular_directions(m, nx, attempt/starts) if attempt < 3 else rng.normal(size=(m, nx))
        directions /= np.maximum(np.linalg.norm(directions, axis=1, keepdims=True), 1e-12)
        radii = rng.uniform(.28, .78, size=m)
        v0 = np.column_stack([directions, np.log(radii/(1-radii))]).ravel()
        def objective(v):
            A = decode(v)
            return (rho(A, search_cov)-target)**2+quality(A)[2]
        opt = minimize(objective, v0, method='L-BFGS-B', options=dict(maxiter=maxiter, ftol=1e-13, maxls=30))
        A = decode(opt.x); achieved = rho(A, audit_cov)
        sep, s, penalty = quality(A)
        pair_distances = np.linalg.norm(A[:, None]-A[None], axis=2)[np.triu_indices(m, 1)]
        record = dict(attempt=attempt, achieved=achieved, separation=float(sep),
                      median_distance=float(np.median(pair_distances)), singular=s.tolist(),
                      success=bool(opt.success), iterations=int(opt.nit), search_separation_fraction=.10)
        attempts.append(record)
        score = (achieved-target)**2+penalty
        if best is None or score < best[0]:
            best = score, A, record
        if abs(achieved-target) <= CORRELATION_TOLERANCE and sep > .05*ALPHA and s[-1] > .01*ALPHA:
            accepted.append((record['median_distance'], A, record))
            if not prefer_spread:
                break
    if prefer_spread and accepted:
        _, A, record = max(accepted, key=lambda item: item[0])
    else:
        _, A, record = best
    if abs(record['achieved']-target) > CORRELATION_TOLERANCE:
        raise ValueError(f'Unattained dependence nx={nx}, m={m}, {level}: {record}; no relabeling')
    return A, dict(target=target, achieved=record['achieved'], attempts=attempts,
                   tolerance=CORRELATION_TOLERANCE, calibration_seed=seed,
                   audit_seed=2026, audit_N=50000)


class RSM:
    def __init__(self, A, seed):
        self.anchors = np.asarray(A)
        self.m, self.nx = A.shape
        self.name = 'DOE'
        self.lower, self.upper = np.full(self.nx, -ALPHA), np.full(self.nx, ALPHA)
        X = np.vstack([np.array(list(product([-1., 1.], repeat=self.nx))),
                       ALPHA*np.eye(self.nx), -ALPHA*np.eye(self.nx), np.zeros((5, self.nx))])
        self.Xobs, self.Z = X, design(X)
        F = truth(X, A)
        sigma = np.sqrt(F.var(0, ddof=1)*(.05/.95))
        self.Yobs = F+np.random.default_rng(seed).normal(0, sigma, size=F.shape)
        self.B = np.linalg.lstsq(self.Z, self.Yobs, rcond=None)[0]
        residual = self.Yobs-self.Z@self.B
        self.mse = np.sum(residual**2, axis=0)/(len(X)-self.Z.shape[1])
        self.XtX_inv = np.linalg.inv(self.Z.T@self.Z)

    def evaluate(self, X):
        F = design(X)@self.B
        return F[0] if np.asarray(X).ndim == 1 else F

    def jacobian(self, x):
        return (design_jac(x).T@self.B).T

    def feasible(self, X):
        return np.sum(np.atleast_2d(X)**2, axis=1) <= ALPHA**2+1e-8

    def sample(self, n, seed):
        return ball(n, self.nx, seed)

    def pareto_sample(self, n, seed):
        A = self.anchors
        if len(A) <= self.nx+1:
            rng = np.random.default_rng(seed)
            w = rng.exponential(size=(n-len(A), len(A)))
            w /= w.sum(axis=1, keepdims=True)
            X = np.vstack([A, w@A])
            return X, truth(X, A)
        tri = Delaunay(A)
        T = A[tri.simplices]
        volumes = np.abs(np.linalg.det(T[:, 1:]-T[:, :1]))
        rng = np.random.default_rng(seed)
        ids = rng.choice(len(T), n-len(A), p=volumes/volumes.sum())
        w = rng.exponential(size=(len(ids), self.nx+1)); w /= w.sum(1, keepdims=True)
        X = np.vstack([A, np.einsum('ni,nij->nj', w, T[ids])])
        return X, truth(X, A)


def master_design():
    rows = []
    for nx, delta, level in product((2, 3, 5), (1, 3, 5), TARGETS):
        m = nx+1+delta
        sid = f'doe_nx{nx}_m{m}_{level}'
        for seed in range(101, 111):
            rows.append(dict(scenario_id=sid, seed=seed, nx=nx, m=m, delta=delta,
                             dependence_level=level, target=TARGETS[level],
                             geometry_seed=7300+10000*nx+100*m+round(TARGETS[level]*100),
                             candidate_combinations=sum(comb(m, k) for k in range(2, min(m, nx+1)+1))))
    return rows
