"""Evolutionary comparators and the paper-faithful VRF-NBI workflow."""
from dataclasses import replace
from math import comb
import json
from pathlib import Path
from types import SimpleNamespace
from time import perf_counter
import numpy as np
from .doe import RSM
from .solver import Meter, Config, BudgetExhausted, run_cnbi, cnbi_deltas
from cnbi.config import ALPHA


EA_MIN_EVALUATIONS = 50_000
EA_MIN_GENERATIONS = 400
EA_CALIBRATION_FILE = Path(__file__).with_name('ea_calibration.json')


def ea_budget(objectives):
    """Same allowance per M, sized for 400 generations at partitions=4."""
    largest_candidate_population = comb(int(objectives)+3, 4)
    return max(EA_MIN_EVALUATIONS,
               EA_MIN_GENERATIONS*largest_candidate_population)


def calibrated_ea_parameters(method, nx, objectives):
    if not EA_CALIBRATION_FILE.exists():
        return None
    selected = json.loads(EA_CALIBRATION_FILE.read_text(encoding='utf-8'))
    return selected.get(f'{method}_nx{int(nx)}_m{int(objectives)}')


def vrf_factor_count(cumulative):
    """User-authorized rule: at least two factors AND at least 90% variance.

    Dimensional admissibility is checked separately; never cap a required
    factor count to nx+1 and thereby silently lose the retention requirement.
    """
    cumulative = np.asarray(cumulative, float)
    if cumulative.ndim != 1 or len(cumulative) < 2 or not np.isfinite(cumulative).all():
        raise ValueError('VRF requires at least two finite PCA components')
    if np.any(np.diff(cumulative) < -1e-12) or cumulative[-1] < .90:
        raise ValueError('Invalid cumulative PCA retention')
    return max(2, int(np.searchsorted(cumulative, .90)+1))


def rotated_factor_scores(Y, k):
    """Equations 11 and 20: correlation loadings, Varimax and factor scores."""
    from factor_analyzer.rotator import Rotator
    Y = np.asarray(Y, float)
    mean = Y.mean(0)
    scale = Y.std(0, ddof=0)
    if np.any(scale <= 1e-14):
        raise ValueError('VRF cannot standardize a constant response')
    Z = (Y-mean)/scale
    correlation = np.corrcoef(Z, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(correlation)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = np.maximum(eigenvalues[order], 0.)
    eigenvectors = eigenvectors[:, order]
    loadings = eigenvectors[:, :k]*np.sqrt(eigenvalues[:k])
    loadings = Rotator(method='varimax').fit_transform(loadings)
    signs = np.where(loadings[np.argmax(np.abs(loadings), axis=0), np.arange(k)] >= 0, 1., -1.)
    loadings *= signs
    weights = loadings@np.linalg.pinv(loadings.T@loadings)
    return Z@weights, loadings, weights, mean, scale, eigenvalues


def factor_score_transform(loadings, standardized_objectives):
    """Equation 11, with the pseudoinverse as the loadings-based fallback."""
    loadings = np.asarray(loadings, float)
    weights = loadings@np.linalg.pinv(loadings.T@loadings)
    return np.atleast_2d(standardized_objectives)@weights, weights, 'L@pinv(L.T@L)'


def run_ea(problem, cfg, method, parameters=None):
    from pymoo.core.problem import Problem
    from pymoo.core.repair import Repair
    from pymoo.algorithms.moo.nsga3 import NSGA3
    from pymoo.algorithms.moo.moead import MOEAD
    from pymoo.operators.crossover.sbx import SBX
    from pymoo.operators.mutation.pm import PM
    from pymoo.util.ref_dirs import get_reference_directions
    t0 = perf_counter()
    rng = np.random.default_rng(cfg.seed)
    rows = []

    class DomainRepair(Repair):
        def _do(self, _, X, **kwargs):
            X = np.clip(X, problem.lower, problem.upper)
            if isinstance(problem, RSM):
                return X*np.minimum(1, ALPHA/np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-15))
            return problem.repair(X, int(rng.integers(2**31)))

    class Adapter(Problem):
        def __init__(self):
            super().__init__(n_var=problem.nx, n_obj=problem.m, xl=problem.lower, xu=problem.upper)

        def _evaluate(self, X, out, *args, **kwargs):
            values = []
            for x in X:
                F = meter(x)
                values.append(F)
                rows.append(dict(x=x.copy(), F=F, accepted=bool(problem.feasible(x)[0])))
            out['F'] = np.asarray(values)

    supplied_parameters = parameters
    if parameters is None:
        parameters = calibrated_ea_parameters(method, problem.nx, problem.m)
    parameters = dict(parameters or {})
    partitions = int(parameters.get('n_partitions', 2))
    sbx_probability = float(parameters.get('sbx_probability', 1.))
    sbx_eta = float(parameters.get('sbx_eta', 20.))
    pm_eta = float(parameters.get('pm_eta', 20.))
    neighbor_fraction = float(parameters.get('neighbor_fraction', .2))
    prob_neighbor_mating = float(parameters.get('prob_neighbor_mating', .9))
    directions = get_reference_directions('das-dennis', problem.m, n_partitions=partitions)
    budget = int(cfg.budget) if cfg.budget is not None else ea_budget(problem.m)
    meter = Meter(problem, budget); meter.phase = 'optimization'
    repair = DomainRepair()
    params = dict(ref_dirs=directions,
                  crossover=SBX(prob=sbx_probability, eta=sbx_eta, repair=repair),
                  mutation=PM(prob=1/problem.nx, eta=pm_eta, repair=repair), repair=repair)
    if method == 'NSGA-III':
        algorithm = NSGA3(pop_size=len(directions), **params)
    else:
        algorithm = MOEAD(n_neighbors=max(2, min(len(directions)-1,
                                                round(neighbor_fraction*len(directions)))),
                          prob_neighbor_mating=prob_neighbor_mating, **params)
    generations = max(2, budget//len(directions))
    algorithm.setup(Adapter(), termination=('n_gen', generations), seed=cfg.seed, verbose=False)
    status = 'COMPLETED'
    # Same hard ceiling; last partial generation is metered and archived.
    try:
        while meter.used < budget and algorithm.has_next():
            algorithm.next()
    except BudgetExhausted:
        status = 'BUDGET_EXHAUSTED'
    evaluated_count = len(rows)
    if algorithm.pop is not None:
        rows = [dict(x=x, F=f, accepted=bool(problem.feasible(x)[0]))
                for x, f in zip(algorithm.pop.get('X'), algorithm.pop.get('F'))]
    return dict(rows=rows, status=status, evaluations=meter.used, budget_limit=budget,
                evaluation_phases=meter.phases,
                seconds=perf_counter()-t0, diagnostic_seconds=0., diagnostics=dict(population=len(directions),
                tuning=('calibration_file' if supplied_parameters is None and parameters else
                        'explicit_calibration_run' if supplied_parameters is not None else
                        'legacy_base_not_retuned'),
                parameters=dict(n_partitions=partitions, sbx_probability=sbx_probability,
                                sbx_eta=sbx_eta, pm_eta=pm_eta,
                                neighbor_fraction=neighbor_fraction,
                                prob_neighbor_mating=prob_neighbor_mating),
                generations=generations, archive='last_complete_population',
                evaluated_count=evaluated_count,
                budget_rule='max(50000, 400*C(M+3,4))'), combinations=[])


def run_vrf(problem, cfg):
    """Pereira et al. VRF-NBI: Eqs. 11, 17--28 and Algorithm 3."""
    from itertools import product
    from math import comb
    from scipy.optimize import minimize
    from .doe import design, design_jac

    t0 = perf_counter()
    nx = problem.nx
    rho = float(ALPHA if isinstance(problem, RSM) else 2**(nx/4))

    if isinstance(problem, RSM):
        Xcoded = np.asarray(problem.Xobs)
        Y = np.asarray(problem.Yobs)
        to_physical = lambda X: np.asarray(X)
        from_physical = lambda X: np.asarray(X)
        training_cost = 0  # The experimental observations are already supplied.
        region = 'supplied_CCD_hypersphere'
    else:
        factorial = np.array(list(product((-1., 1.), repeat=nx)))
        axial = np.vstack((rho*np.eye(nx), -rho*np.eye(nx)))
        Xcoded = np.vstack((factorial, axial, np.zeros((5, nx))))
        if problem.number in (8, 9):
            to_physical = lambda X: np.asarray(X)
            from_physical = lambda X: np.asarray(X)
            region = 'coded_CCD_centered_at_origin_containing_known_Pareto_region'
        else:
            center = (problem.lower+problem.upper)/2
            scale = (problem.upper-problem.lower)/(2*rho)
            to_physical = lambda X, c=center, s=scale: c+np.asarray(X)*s
            from_physical = lambda X, c=center, s=scale: (np.asarray(X)-c)/s
            region = 'coded_CCD_mapped_to_MaF_bounds'
        Y = np.asarray(problem.evaluate(to_physical(Xcoded)))
        training_cost = len(Xcoded)

    # PCA retention is calculated from the same correlation eigensystem used
    # to construct the loadings in Eq. 20.
    Z0 = (Y-Y.mean(0))/Y.std(0, ddof=0)
    eigenvalues = np.maximum(np.linalg.eigvalsh(np.corrcoef(Z0, rowvar=False))[::-1], 0.)
    cumulative = np.cumsum(eigenvalues)/np.maximum(eigenvalues.sum(), 1e-15)
    k90 = int(np.searchsorted(cumulative, .90)+1)
    k = vrf_factor_count(cumulative)
    metadata = dict(
        implementation='Pereira_et_al_2025_equations_11_17_to_28',
        n_factors=k, n_factors_90=k90, minimum_factors=2,
        factor_rule='max(2, k90)', retained_variance=float(cumulative[k-1]),
        pca_cumulative=cumulative.tolist(), training_evaluations=training_cost,
        experimental_region=region, ccd_runs=len(Xcoded), radius=rho)
    if not 2 <= k <= nx+1:
        return dict(rows=[], status='VRF_STRUCTURALLY_INVALID', evaluations=training_cost,
                    seconds=perf_counter()-t0, diagnostics=metadata, combinations=[],
                    evaluation_phases={'training': training_cost})

    scores, loadings, score_weights, response_mean, response_scale, eigenvalues = rotated_factor_scores(Y, k)
    Zdesign = design(Xcoded)
    Bf = np.linalg.lstsq(Zdesign, scores, rcond=None)[0]
    fitted = Zdesign@Bf
    residual = scores-fitted
    n, q = Zdesign.shape
    sse = np.sum(residual**2, axis=0)
    sst = np.sum((scores-scores.mean(0))**2, axis=0)
    r2 = 1-sse/np.maximum(sst, 1e-15)
    adj_r2 = 1-(1-r2)*(n-1)/max(n-q, 1)
    Hdiag = np.einsum('ij,jk,ik->i', Zdesign, np.linalg.pinv(Zdesign.T@Zdesign), Zdesign)
    press = np.sum((residual/np.maximum(1-Hdiag[:, None], 1e-10))**2, axis=0)
    predicted_r2 = 1-press/np.maximum(sst, 1e-15)
    residual_mse = sse/max(n-q, 1)

    bounds = [(-rho, rho)]*nx
    cons = dict(type='ineq', fun=lambda x: rho**2-x@x, jac=lambda x: -2*x)
    extreme_constraints = [cons]
    if not isinstance(problem, RSM) and hasattr(problem, 'feasibility_margin'):
        extreme_constraints.append(dict(type='ineq', fun=lambda x: float(
            problem.feasibility_margin(to_physical(x))[0])))
    rng = np.random.default_rng(910003+cfg.seed)
    opt_starts = [np.zeros(nx), *list(.99*rho*np.eye(nx)), *list(-.99*rho*np.eye(nx))]
    for _ in range(2):
        u = rng.normal(size=nx); u /= np.linalg.norm(u)
        opt_starts.append(rho*rng.random()**(1/nx)*u)
    if not isinstance(problem, RSM) and hasattr(problem, 'optimization_starts'):
        for physical in problem.optimization_starts(cfg.seed):
            coded = from_physical(physical)
            if np.linalg.norm(coded) <= rho+1e-9 and problem.feasible(to_physical(coded))[0]:
                opt_starts.append(coded)

    extreme_pool = None
    if not isinstance(problem, RSM) and problem.number == 9:
        angles = np.linspace(0, 2*np.pi, 721)[:-1]
        radii = np.linspace(0, rho, 151)
        extreme_pool = np.vstack((np.zeros((1, 2)), np.column_stack([
            np.repeat(radii[1:], len(angles))*np.tile(np.cos(angles), len(radii)-1),
            np.repeat(radii[1:], len(angles))*np.tile(np.sin(angles), len(radii)-1)])))
        extreme_pool = extreme_pool[problem.feasible(to_physical(extreme_pool))]

    def extreme(fun, jac, maximize=False, pool_values=None):
        results = []
        sign = -1. if maximize else 1.
        search_starts = opt_starts
        if pool_values is not None:
            best_id = int(np.argmax(pool_values) if maximize else np.argmin(pool_values))
            x0 = extreme_pool[best_id]
            results.append(SimpleNamespace(x=x0.copy(), fun=float(fun(x0)), success=True))
            search_starts = []
        for x0 in search_starts:
            r = minimize(lambda x: sign*fun(x), x0, jac=lambda x: sign*jac(x),
                         method='SLSQP', bounds=bounds, constraints=extreme_constraints,
                         options=dict(ftol=1e-12, maxiter=max(100, cfg.maxiter)))
            # Some quartic VRFs reach a feasible stationary point while SLSQP
            # reports a line-search exit. Feasibility and the achieved value,
            # which are the criteria in Eqs. 21--22, remain directly checkable.
            if np.isfinite(r.fun) and all(c['fun'](r.x) >= -1e-7 for c in extreme_constraints):
                results.append(r)
        if not results:
            raise ValueError('VRF individual optimization failed')
        return min(results, key=lambda r: sign*fun(r.x))

    def factor_value(x):
        return (design(x)@Bf)[0]

    def factor_jac(x):
        return (design_jac(x).T@Bf).T

    targets = np.empty(k)
    pool_factors = design(extreme_pool)@Bf if extreme_pool is not None else None
    for j in range(k):
        r = extreme(lambda x, j=j: factor_value(x)[j],
                    lambda x, j=j: factor_jac(x)[j],
                    pool_values=None if pool_factors is None else pool_factors[:, j])
        targets[j] = factor_value(r.x)[j]

    # Eq. 21. This variance is constant inside each factor under the paper's
    # definition; retaining it makes the implementation explicit even though
    # it cancels algebraically in Eq. 25.
    factor_variance = np.sum(loadings**2, axis=0)*rho

    def raw_vrf(x):
        d = factor_value(x)-targets
        return d*d+factor_variance

    def raw_vrf_jac(x):
        d = factor_value(x)-targets
        return 2*d[:, None]*factor_jac(x)

    utopia = np.empty(k); nadir = np.empty(k)
    utopia_x = []; nadir_x = []
    for j in range(k):
        pool_raw = None if pool_factors is None else (pool_factors[:, j]-targets[j])**2+factor_variance[j]
        ru = extreme(lambda x, j=j: raw_vrf(x)[j], lambda x, j=j: raw_vrf_jac(x)[j],
                     pool_values=pool_raw)
        rn = extreme(lambda x, j=j: raw_vrf(x)[j], lambda x, j=j: raw_vrf_jac(x)[j], True,
                     pool_values=pool_raw)
        utopia[j], nadir[j] = raw_vrf(ru.x)[j], raw_vrf(rn.x)[j]
        utopia_x.append(ru.x.copy()); nadir_x.append(rn.x.copy())
    amplitude = nadir-utopia
    if np.any(amplitude <= 1e-12):
        raise ValueError('VRF normalization has zero amplitude')

    class VRFProblem:
        m = k
        lower = np.full(nx, -rho)
        upper = np.full(nx, rho)
        is_rsm = True
        radius = rho
        nbi_ideal = np.zeros(k)
        nbi_amplitude = np.ones(k)
        # SLSQP sometimes reports a line-search exit after already satisfying
        # the NBI equations. Algorithm 3 judges feasibility and dominance, so
        # those numerically feasible points remain admissible for VRF only.
        accept_feasible_optimizer_exit = True

        def __init__(self):
            self.nx = nx

        def feasible(self, X):
            X = np.atleast_2d(X)
            inside = np.linalg.norm(X, axis=1) <= rho+1e-8
            if not isinstance(problem, RSM):
                inside &= problem.feasible(to_physical(X))
            return inside

        def evaluate(self, X):
            X = np.asarray(X)
            out = np.vstack([(raw_vrf(x)-utopia)/amplitude for x in np.atleast_2d(X)])
            return out[0] if X.ndim == 1 else out

        def jacobian(self, x):
            return raw_vrf_jac(x)/amplitude[:, None]

        def payoff_starts(self, objective, seed):
            # Eq. 21 can have several equally good points on the target
            # contour. Multiple starts expose those points to the payoff step.
            candidates = [*utopia_x, *nadir_x, np.zeros(nx), *opt_starts[1:1+2*nx]]
            return [x for x in candidates if self.feasible(x)[0]]

        def payoff_key(self, objective, result):
            # Preserve the individual minimum first; among numerical ties pick
            # the point that displays the largest conflict with other VRFs.
            values = self.evaluate(result.x)
            return (round(float(values[objective]), 9),
                    -float(np.delete(values, objective).sum()))

    factors = VRFProblem()
    if not isinstance(problem, RSM) and hasattr(problem, 'feasibility_margin'):
        factors.additional_feasibility_margin = lambda X: problem.feasibility_margin(to_physical(X))
    resolution = cnbi_deltas(cfg)[k]
    reserve = comb(round(1/resolution)+k-1, k-1)
    if cfg.budget is not None and cfg.budget <= training_cost+reserve:
        raise ValueError('VRF budget insufficient for training and recomposition reserve')
    internal_budget = (None if cfg.budget is None
                       else cfg.budget-training_cost-reserve)
    result = run_cnbi(factors, replace(cfg, budget=internal_budget), 'direct')
    result['evaluations'] += training_cost
    result['evaluation_phases']['training'] = training_cost

    composed = []
    for row in result['rows']:
        if 'x' not in row:
            continue
        if cfg.budget is not None and result['evaluations'] >= cfg.budget:
            result['status'] = 'BUDGET_EXHAUSTED_BEFORE_RECOMPOSITION'
            break
        physical_x = to_physical(row['x'])
        composed.append({**row, 'x_coded': row['x'], 'x': physical_x,
                         'F_vrf': row['F'], 'F': problem.evaluate(physical_x)})
        result['evaluations'] += 1
    result['rows'] = composed
    result['budget_limit'] = cfg.budget
    result['evaluation_phases']['recomposition'] = len(composed)
    result['diagnostics'].update(metadata, loadings=loadings, score_weights=score_weights,
        score_weight_rule='L@pinv(L.T@L)', response_mean=response_mean,
        response_scale=response_scale, factor_targets=targets, factor_variance=factor_variance,
        vrf_utopia=utopia, vrf_nadir=nadir, factor_r2=r2, factor_adjusted_r2=adj_r2,
        factor_predicted_r2=predicted_r2, factor_residual_mse=residual_mse,
        surrogate_warning=bool(np.any(predicted_r2 < .75)),
        extreme_search=('dense_feasible_grid' if extreme_pool is not None
                        else 'multistart_SLSQP'),
        normalization='independent_VRF_utopia_nadir_Eq25',
        nbi_payoff_scaling='fixed_normalized_VRF_scale')
    result['seconds'] = perf_counter()-t0
    return result
