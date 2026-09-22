"""Small audited pilot only. No FULL mode exists in this entry point.

Run: .venv/python -m cnbi_experiments.pilot --output experimental_results/pilot
"""
import os
for _key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
from cnbi.pareto import postprocess_frontier
from .benchmarks import MaF
from .doe import RSM, calibrate, master_design, truth
from .parallel_analysis import permutation_pa
from .solver import Config, run_cnbi
from .comparators import run_ea, run_vrf
from .reuse import METRICS, METRICS_PROVENANCE

ABLATION_SCENARIO = 'doe_nx2_m4_low'


def clean(value):
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def write_json(path, data):
    path.write_text(json.dumps(clean(data), indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')


def frontier(problem, result):
    rows = [r for r in result['rows'] if r.get('accepted') and 'x' in r]
    if not rows:
        return np.empty((0, problem.nx)), np.empty((0, problem.m))
    X = np.vstack([r['x'] for r in rows])
    # External evaluation of RSM solutions, not available to the optimizers.
    F = truth(X, problem.anchors) if isinstance(problem, RSM) else np.vstack([r['F'] for r in rows])
    processed = postprocess_frontier(X, F, duplicate_tolerance=1e-5, dominance_tolerance=1e-10)
    return processed['X'], processed['F']


def metrics(F, R, seed):
    if len(F) == 0:
        return dict(IGD=None, HV=None, GD=None, Spacing=None, Sparsity=None, HV_se=None)
    hv, se = METRICS['hv_qmc'](F, F.shape[1], seed=2026+seed, n=8192)
    return dict(IGD=METRICS['IGD'](F, R), GD=METRICS['GD'](F, R), HV=hv, HV_se=se,
                Spacing=METRICS['spacing'](F) if len(F) > 1 else None,
                Sparsity=METRICS['sparsity'](F) if len(F) > 1 else None)


def run(output, ea_budget=None, seeds=(101, 102)):
    output.mkdir(parents=True, exist_ok=True)
    from . import tests
    import unittest
    suite = unittest.defaultTestLoader.discover(str(Path(tests.__file__).parent))
    validation = unittest.TextTestRunner(verbosity=1).run(suite)
    if not validation.wasSuccessful():
        raise RuntimeError('Benchmark/unit validation failed: optimizer pilot blocked')
    pd.DataFrame(master_design()).to_csv(output/'doe_design.csv', index=False)
    write_json(output/'transition_design.json', [dict(nx=3, m=m, delta=m-4, level='medium',
               classical_nbi_allowed=m <= 4) for m in (3, 4, 5)])
    write_json(output/'maf_design.json', [dict(problem=f'MaF{number}', nx=5 if number == 13 else 2, m=m)
               for number in (8, 9, 13) for m in ((8, 10, 15) if number == 13 else (4, 6, 8, 10, 15))])
    write_json(output/'provenance.json', dict(metrics=METRICS_PROVENANCE,
               config=asdict(Config(budget=None)), seeds=seeds, geometry='fixed_per_condition',
               method_budgets=dict(CNBI='unlimited', VRF_NBI='unlimited',
                                   evolutionary=('explicit '+str(ea_budget) if ea_budget is not None
                                                 else 'max(50000, 400*population)')),
               oracle_cost='PA objective vectors charged to ceiling; common external reference reported separately',
               core_hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (Path(__file__).resolve().parents[1]/'cnbi').glob('*.py')}))
    cases = []; preparation = []
    for nx, m, level in ((2, 4, 'low'), (3, 7, 'medium'), (5, 11, 'high')):
        sid = f'doe_nx{nx}_m{m}_{level}'
        t0 = time.perf_counter()
        try:
            targets = dict(low=.25, medium=.60, high=.85)
            A, audit = calibrate(nx, m, level, 7300+10000*nx+100*m+round(100*targets[level]))
            np.savez_compressed(output/f'{sid}_anchors.npz', anchors=A)
            preparation.append(dict(scenario_id=sid, status='CALIBRATED', seconds=time.perf_counter()-t0, **audit))
            cases.append((sid, lambda seed, A=A: RSM(A, seed), level, audit['achieved']))
        except ValueError as error:
            preparation.append(dict(scenario_id=sid, status='CALIBRATION_FAILED', error=str(error), seconds=time.perf_counter()-t0))
        print('PREPARATION', sid, preparation[-1]['status'], flush=True)
        write_json(output/'preparation.json', preparation)
    for number, m in ((8, 4), (9, 6), (13, 8)):
        cases.append((f'maf{number}_m{m}', lambda seed, number=number, m=m: MaF(number, m), None, None))

    # N sensitivity is a pilot prerequisite, not an unrecorded plotting step.
    sensitivity = []
    for number, m in ((8, 4), (9, 6), (13, 8)):
        p = MaF(number, m)
        for seed in seeds:
            for n in (250, 500, 1000, 5000):
                X, F = p.pareto_sample(n, seed)
                pa = permutation_pa(F, seed=seed)
                write_json(output/f'pa_maf{number}_m{m}_n{n}_seed{seed}.json', pa)
                np.savez_compressed(output/f'pa_maf{number}_m{m}_n{n}_seed{seed}_sample.npz', X=X, F=F)
                sensitivity.append(dict(problem=p.name, m=m, N=n, seed=seed, rank=pa['rank'], seconds=pa['seconds']))
        print('PA', p.name, [r['rank'] for r in sensitivity if r['problem'] == p.name], flush=True)
    pd.DataFrame(sensitivity).to_csv(output/'pa_sensitivity.csv', index=False)

    table = []
    for sid, factory, level, achieved in cases:
        for seed in seeds:
            problem = factory(seed)
            _, R = problem.pareto_sample(5000, 404)
            if isinstance(problem, RSM):
                ideal = np.zeros(problem.m)
                amp = truth(problem.anchors, problem.anchors).max(axis=0)
            elif problem.number in (8, 9):
                Fv = problem.evaluate(problem.vertices)
                ideal = np.zeros(problem.m); amp = Fv.max(axis=0)
            else:
                # MaF13 repeated PF coordinate a+(1-a)^5/16 has minimum
                # 1/16 at a=f1^2=0, f2=f3=1/sqrt(2), and maximum 1.
                ideal = np.r_[np.zeros(3), np.full(problem.m-3, 1/16)]
                amp = 1-ideal
            amp = np.maximum(amp, 1e-12)
            Rn = (R-ideal)/amp
            np.savez_compressed(output/f'{sid}_reference.npz', F=R, ideal=ideal, amplitude=amp)
            fronts = {}; complete = []
            methods = (('CNBI_all',) if sid == ABLATION_SCENARIO else ()) + (
                'CNBI_spectral', 'VRF-NBI', 'NSGA-III', 'MOEA/D')
            for method in methods:
                method_budget = ea_budget if method in ('NSGA-III', 'MOEA/D') else None
                cfg = Config(budget=method_budget, seed=seed)
                print('RUN', sid, seed, method, flush=True)
                if method.startswith('CNBI'):
                    result = run_cnbi(problem, cfg, method.split('_')[1])
                elif method == 'VRF-NBI':
                    result = run_vrf(problem, cfg)
                else:
                    result = run_ea(problem, cfg, method)
                X, F = frontier(problem, result); Fn = (F-ideal)/amp
                fronts[method] = Fn
                if result.get('budget_limit') is not None:
                    assert result['evaluations'] <= result['budget_limit']
                assert np.isfinite(F).all() and problem.feasible(X).all()
                filename = f'{sid}_seed{seed}_{method.replace("/", "_")}'
                write_json(output/f'{filename}.json', result)
                np.savez_compressed(output/f'{filename}_front.npz', X=X, F=F)
                row = dict(scenario_id=sid, seed=seed, nx=problem.nx, m=problem.m,
                           delta=problem.m-problem.nx-1, dependence_level=level, dependence_obtained=achieved,
                           method=method, comparison='complete', n=len(F),
                           budget=result.get('budget_limit'),
                           rank=result['diagnostics'].get('d'),
                           **{k: result.get(k) for k in ('status', 'evaluations', 'seconds', 'diagnostic_seconds',
                             'candidate_combinations', 'selected_combinations', 'potential_subproblems',
                             'processed_subproblems', 'feasible_subproblems')}, **metrics(Fn, Rn, seed))
                table.append(row); complete.append(row)
                print('RESULT', result['status'], result['evaluations'], 'front', len(F), flush=True)
            target = min(len(F) for F in fronts.values())
            # No silent exclusion of an empty method to claim equal cardinality.
            for row in complete:
                F = fronts[row['method']]
                if target == 0:
                    reduced = np.empty((0, problem.m))
                else:
                    reduced = METRICS['hierarchical_equal_cardinality'](F, target) if len(F) > target else F
                equal_row = {**row, 'comparison': 'equal_cardinality', 'n': len(reduced),
                             'cardinality_status': 'PASS' if target > 0 else 'BLOCKED_EMPTY_METHOD',
                             **metrics(reduced, Rn, seed)}
                table.append(equal_row)
            pd.DataFrame(table).to_csv(output/'master_results.csv', index=False)
    write_json(output/'pilot_status.json', dict(validation_passed=True, full_campaign_executed=False,
               preparations=preparation, rows=len(table), all_cardinality_checks_passed=all(
               r.get('cardinality_status') == 'PASS' for r in table if r['comparison'] == 'equal_cardinality'),
               pa_stable=all(len(set(r['rank'] for r in sensitivity if r['problem'] == p)) == 1
                             for p in ('MaF8', 'MaF9', 'MaF13'))))
    return pd.DataFrame(table)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('experimental_results/pilot'))
    parser.add_argument('--ea-budget', type=int, default=None,
                        help='EA evaluation ceiling; default is max(50000, 400*population)')
    parser.add_argument('--seeds', type=int, nargs='+', default=[101, 102])
    args = parser.parse_args()
    run(args.output, args.ea_budget, tuple(args.seeds))
