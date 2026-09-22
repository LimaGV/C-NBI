"""Experimental problem adapter and shared all/spectral NBI orchestration.

Equations, normalization and acceptance follow cnbi/nbi.py. The original module
is never patched. Changes: arbitrary dimension/domain, metered finite-difference
Jacobians for non-RSM functions, explicit degenerate geometry and hard budget.
"""
from dataclasses import dataclass
from typing import Optional
from itertools import combinations
from math import comb
from time import perf_counter
import numpy as np
from scipy.linalg import null_space
from scipy.optimize import minimize
from cnbi.config import ALPHA
from cnbi.combinations import simplex_weights, _nearest_weight_order
from cnbi.spectral import parallel_analysis as legacy_pa
from .doe import RSM, design
from .parallel_analysis import permutation_pa, payoff_window


class BudgetExhausted(RuntimeError):
    pass


@dataclass
class Config:
    # None means that the method is allowed to finish its complete procedure.
    budget: Optional[int] = 8000
    maxiter: int = 100
    max_rescues: int = 2
    seed: int = 101
    # Explicit experimental resolutions; cnbi.config.DELTA_BY_K remains intact.
    delta2: float = .2
    delta3: float = .2
    delta4: float = .2
    delta5: float = .5
    # p=2 includes vertices and pairwise midpoints for six objectives.
    delta6: float = .5
    pa_B: int = 1000
    pa_N: int = 500


class Meter:
    def __init__(self, problem, limit):
        self.problem, self.limit = problem, limit
        self.used = 0; self.gradient_calls = 0; self.phase = 'setup'; self.phases = {}

    def __call__(self, x):
        if self.limit is not None and self.used >= self.limit:
            raise BudgetExhausted()
        self.used += 1
        self.phases[self.phase] = self.phases.get(self.phase, 0)+1
        F = np.asarray(self.problem.evaluate(x))
        if not np.isfinite(F).all():
            raise FloatingPointError('Nonfinite objective value')
        return F

    def charge_batch(self, n, phase):
        """Reserve objective-vector evaluations before a diagnostic batch."""
        if self.limit is not None and self.used+n > self.limit:
            raise BudgetExhausted()
        self.used += n
        self.phases[phase] = self.phases.get(phase, 0)+n

    def jac(self, x):
        self.gradient_calls += 1
        if hasattr(self.problem, 'jacobian'):
            return self.problem.jacobian(x)
        # Every numerical perturbation is metered; no free objective calls.
        x = np.asarray(x, float)
        out = np.empty((self.problem.m, self.problem.nx))
        for j in range(len(x)):
            h = 1e-6*max(1., abs(x[j]))
            lo, hi = x.copy(), x.copy()
            lo[j] = max(self.problem.lower[j], x[j]-h)
            hi[j] = min(self.problem.upper[j], x[j]+h)
            out[:, j] = (self(hi)-self(lo))/(hi[j]-lo[j])
        return out


def cnbi_deltas(cfg):
    """Resolution table for this experiment without mutating core CNBI."""
    return {2: cfg.delta2, 3: cfg.delta3, 4: cfg.delta4,
            5: cfg.delta5, 6: cfg.delta6}


def constraints(problem, augmented=False):
    if isinstance(problem, RSM) or getattr(problem, 'is_rsm', False):
        nx = problem.nx
        radius = getattr(problem, 'radius', ALPHA)
        result = [dict(type='ineq', fun=lambda v: radius**2-v[:nx]@v[:nx],
                       jac=lambda v: np.r_[-2*v[:nx], 0.] if augmented else -2*v)]
        if hasattr(problem, 'additional_feasibility_margin'):
            result.append(dict(type='ineq', fun=lambda v: float(problem.additional_feasibility_margin(
                v[:nx] if augmented else v)[0])))
        return result
    if hasattr(problem, 'feasibility_margin'):
        nx = problem.nx
        return [dict(type='ineq', fun=lambda v: float(
            problem.feasibility_margin(v[:nx] if augmented else v)[0]))]
    return []


def starts(problem, seed):
    nx = problem.nx
    if isinstance(problem, RSM) or getattr(problem, 'is_rsm', False):
        radius = getattr(problem, 'radius', ALPHA)
        return [np.zeros(nx), *list(.99*radius*np.eye(nx)), *list(-.99*radius*np.eye(nx))]
    if hasattr(problem, 'optimization_starts'):
        return problem.optimization_starts(seed)
    rng = np.random.default_rng(seed)
    center = (problem.lower+problem.upper)/2
    return [center, *list(rng.uniform(problem.lower, problem.upper, (2*nx, nx)))]


def payoff(problem, meter, cfg):
    meter.phase = 'payoff'
    Xs, columns = [], []
    for j in range(problem.m):
        valid = []
        payoff_starts = (problem.payoff_starts(j, cfg.seed)
                         if hasattr(problem, 'payoff_starts') else starts(problem, cfg.seed))
        for x0 in payoff_starts:
            if not problem.feasible(x0)[0]:
                continue
            result = minimize(lambda x: meter(x)[j], x0, jac=lambda x: meter.jac(x)[j],
                              method='SLSQP', bounds=list(zip(problem.lower, problem.upper)),
                              constraints=constraints(problem), options=dict(ftol=1e-11, maxiter=cfg.maxiter))
            optimizer_ok = result.success or getattr(problem, 'accept_feasible_optimizer_exit', False)
            if optimizer_ok and problem.feasible(result.x)[0] and np.isfinite(result.fun):
                valid.append(result)
        if not valid:
            raise ValueError(f'No valid payoff optimum for objective {j}')
        best = min(valid, key=(lambda r: problem.payoff_key(j, r))
                   if hasattr(problem, 'payoff_key') else (lambda r: r.fun))
        Xs.append(best.x); columns.append(meter(best.x))
    return np.array(Xs), np.column_stack(columns)


def uncertainty_pa(problem, P, Xstar):
    if problem.nx == 3:
        return legacy_pa(P, Xstar, problem.mse, problem.XtX_inv)
    amp = P.max(1)-P.min(1); amp = np.where(amp > 1e-12, amp, 1.)
    scaled = (P-P.min(1)[:, None])/amp[:, None]
    A = scaled.T; s = np.linalg.svd(A[1:]-A[:1], compute_uv=False)
    Z = design(Xstar)
    h = np.einsum('ij,jk,ik->i', Z, problem.XtX_inv, Z)
    sd = np.sqrt(np.outer(h, problem.mse))/amp[None, :]
    rng = np.random.default_rng(777); noise = []
    for _ in range(2000):
        R = rng.normal(0, sd)
        noise.append(np.linalg.svd(R[1:]-R[:1], compute_uv=False))
    p95 = np.percentile(noise, 95, axis=0)
    d = max(1, int(np.sum(s > p95)))
    return dict(d=d, s=s, p95=p95, floor=float(s[d]) if d < len(s) else 0.,
                ceiling=float(s[0]/s[d-1]), scaled=scaled)


def solve_subset(problem, meter, combo, Xstar, P, delta, combo_id, cfg):
    """Yield records immediately so a hard stop preserves completed subproblems."""
    nx = problem.nx
    k = len(combo)
    if hasattr(problem, 'nbi_ideal'):
        ideal = np.asarray(problem.nbi_ideal)[combo]
        amp = np.asarray(problem.nbi_amplitude)[combo]
    else:
        ideal = P.min(1); amp = np.maximum(P.max(1)-ideal, 1e-12)
    A = ((P-ideal[:, None])/amp[:, None]).T
    ns = null_space(A[1:]-A[:1])
    if ns.shape[1] != 1:
        return
    normal = ns[:, 0]
    if normal@(-A.mean(0)) < 0:
        normal = -normal
    warm = None
    for beta_id, beta in _nearest_weight_order(simplex_weights(k, delta)):
        phi = beta@A
        vertex = np.flatnonzero(np.isclose(beta, 1., atol=1e-12) & np.isclose(beta.sum(), 1., atol=1e-12))
        if len(vertex) == 1:
            x = Xstar[vertex[0]].copy(); F = meter(x)
            residual = np.max(np.abs((F[combo]-ideal)/amp-phi))
            accepted = bool(residual <= 1e-5 and problem.feasible(x)[0])
            yield dict(combo=combo.tolist(), beta_id=int(beta_id), accepted=accepted, x=x, F=F,
                       eq_inf=float(residual), attempts=0, status='COMPLETED' if accepted else 'INFEASIBLE')
            warm = np.r_[x, 0.]
            continue
        def eq(v):
            return (meter(v[:nx])[combo]-ideal)/amp-phi-v[-1]*normal
        def jeq(v):
            return np.column_stack([meter.jac(v[:nx])[combo]/amp[:, None], -normal])
        initial = []
        if warm is not None:
            initial.append(warm[:nx])
        initial.extend([beta@Xstar, *Xstar[np.argsort(-beta)], (problem.lower+problem.upper)/2])
        rng = np.random.default_rng(1000003+1009*combo_id+beta_id)
        for _ in range(cfg.max_rescues):
            if isinstance(problem, RSM) or getattr(problem, 'is_rsm', False):
                direction = rng.normal(size=nx); direction /= np.linalg.norm(direction)
                radius = getattr(problem, 'radius', ALPHA)
                initial.append(radius*rng.random()**(1/nx)*direction)
            else:
                initial.append(rng.uniform(problem.lower, problem.upper))
        candidates = []; seen = set()
        for x0 in initial:
            if not problem.feasible(x0)[0]:
                continue
            key = tuple(np.round(x0, 12))
            if key in seen:
                continue
            seen.add(key)
            t = np.clip(((meter(x0)[combo]-ideal)/amp-phi)@normal, -10, 10)
            r = minimize(lambda v: -v[-1], np.r_[x0, t], jac=lambda v: np.r_[np.zeros(nx), -1.],
                         method='SLSQP', bounds=[*zip(problem.lower, problem.upper), (-10, 10)],
                         constraints=[dict(type='eq', fun=eq, jac=jeq), *constraints(problem, True)],
                         options=dict(ftol=1e-10, maxiter=cfg.maxiter))
            residual = float(np.max(np.abs(eq(r.x))))
            feasible = bool(problem.feasible(r.x[:nx])[0])
            optimizer_ok = r.success or getattr(problem, 'accept_feasible_optimizer_exit', False)
            ok = bool(optimizer_ok and residual <= 1e-5 and feasible)
            candidates.append((ok, residual, r))
            if ok:
                break
        if not candidates:
            yield dict(combo=combo.tolist(), beta_id=int(beta_id), accepted=False,
                       status='NO_FEASIBLE_START', attempts=0)
            continue
        ok, residual, r = min(candidates, key=lambda v: (not v[0], -v[2].x[-1] if v[0] else v[1]))
        F = meter(r.x[:nx])
        yield dict(combo=combo.tolist(), beta_id=int(beta_id), accepted=ok, x=r.x[:nx], F=F,
                   eq_inf=residual, attempts=len(candidates), status='COMPLETED' if ok else 'INFEASIBLE')
        warm = r.x if ok else None


def run_cnbi(problem, cfg, variant='spectral', fixed_payoff=None):
    if variant not in ('all', 'spectral', 'direct'):
        raise ValueError('Unknown variant')
    if variant == 'direct' and problem.m > problem.nx+1:
        raise ValueError('Classical NBI dimensionally inadmissible')
    t0 = perf_counter(); meter = Meter(problem, cfg.budget)
    rows = []; combinations_log = []; diag = {}; status = 'COMPLETED'; diagnostic_seconds = 0.
    deltas = cnbi_deltas(cfg)
    combos = [tuple(range(problem.m))] if variant == 'direct' else [
        c for k in range(2, min(problem.m, problem.nx+1)+1) for c in combinations(range(problem.m), k)]
    selected = None
    potential = sum(comb(round(1/deltas[len(c)])+len(c)-1, len(c)-1) for c in combos)
    try:
        if fixed_payoff is None:
            Xstar, P = payoff(problem, meter, cfg)
        else:
            # A paired ablation must change only the combination filter.
            # Reuse the exact saved payoff geometry from its spectral arm.
            Xstar, P, payoff_evaluations = fixed_payoff
            meter.charge_batch(int(payoff_evaluations), 'payoff')
            Xstar, P = np.asarray(Xstar, float), np.asarray(P, float)
        # Store the payoff used, including numerical individual-optimum limitations.
        diag.update(payoff=P, Xstar=Xstar)
        tdiag = perf_counter()
        if variant == 'spectral':
            if isinstance(problem, RSM):
                window = uncertainty_pa(problem, P, Xstar)
                diag.update(window)
            else:
                meter.charge_batch(cfg.pa_N, 'pareto_diagnostic')
                _, F = problem.pareto_sample(cfg.pa_N, cfg.seed)
                pa = permutation_pa(F, B=cfg.pa_B, seed=cfg.seed)
                window = payoff_window(P, pa['rank'])
                diag.update(window); diag['horn'] = pa
        else:
            window = None
        selected = []
        for combo in combos:
            c = np.array(combo)
            local = P[np.ix_(c, c)]
            if hasattr(problem, 'nbi_ideal'):
                local_ideal = np.asarray(problem.nbi_ideal)[c]
                amp = np.asarray(problem.nbi_amplitude)[c]
            else:
                local_ideal = local.min(1)
                amp = np.maximum(local.max(1)-local_ideal, 1e-12)
            A = ((local-local_ideal[:, None])/amp[:, None]).T
            degeneracy = null_space(A[1:]-A[:1]).shape[1] != 1
            keep = True
            if window is not None:
                S = window['scaled'][np.ix_(c, c)].T
                s = np.linalg.svd(S[1:]-S[:1], compute_uv=False)
                q = np.inf if s[-1] <= 1e-12 else s[0]/s[-1]
                keep = bool(s[-1] > window['floor'] and q <= window['ceiling'])
            count = comb(round(1/deltas[len(c)])+len(c)-1, len(c)-1)
            combinations_log.append(dict(combo=list(combo), selected=keep, degenerate=degeneracy,
                                         potential_subproblems=count, processed=0,
                                         status='FILTERED' if not keep else 'DEGENERATE' if degeneracy else 'NOT_REACHED'))
            if keep and not degeneracy:
                selected.append((c, len(combinations_log)-1))
        diagnostic_seconds = perf_counter()-tdiag
        if not selected and combos:
            status = 'NO_NONDEGENERATE_COMBINATIONS'
        meter.phase = 'subproblems'
        for c, log_id in selected:
            # Canonical candidate index pairs rescue seeds across ablation arms.
            for row in solve_subset(problem, meter, c, Xstar[c], P[np.ix_(c, c)], deltas[len(c)], log_id, cfg):
                rows.append(row); combinations_log[log_id]['processed'] += 1
                combinations_log[log_id]['status'] = 'PARTIAL'
            combinations_log[log_id]['status'] = 'COMPLETED'
    except BudgetExhausted:
        status = 'BUDGET_EXHAUSTED'
    except ValueError as error:
        status = 'METHODOLOGICAL_OR_PAYOFF_GATE'
        diag['error'] = str(error)
    return dict(rows=rows, diagnostics=diag, combinations=combinations_log, status=status,
                evaluations=meter.used, evaluation_phases=meter.phases, gradient_calls=meter.gradient_calls,
                budget_limit=cfg.budget,
                seconds=perf_counter()-t0, diagnostic_seconds=diagnostic_seconds,
                candidate_combinations=len(combos), selected_combinations=(len(combos) if variant != 'spectral' else
                    sum(r['selected'] for r in combinations_log) if selected is not None else None),
                potential_subproblems=potential, processed_subproblems=len(rows),
                feasible_subproblems=sum(r['accepted'] for r in rows))
