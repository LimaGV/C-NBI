"""Checkpointed full DOE, MaF and dimensional-transition campaign."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import warnings

warnings.filterwarnings('ignore', message='The behavior of DataFrame concatenation')
warnings.filterwarnings('ignore', message='Values in x were outside bounds')
warnings.filterwarnings('ignore', message='invalid value encountered in cast')

for _key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'

import numpy as np
import pandas as pd

from .analysis import analyze
from .benchmarks import MaF
from .comparators import run_ea, run_vrf
from .doe import RSM, TARGETS, calibrate, master_design, truth
from .parallel_analysis import permutation_pa
from .pilot import ABLATION_SCENARIO, frontier, metrics, write_json
from .report import report
from .reuse import METRICS, METRICS_PROVENANCE
from .solver import Config, cnbi_deltas, run_cnbi


REGULAR_METHODS = ('CNBI_spectral', 'VRF-NBI', 'NSGA-III', 'MOEA/D')
MAF_SETTINGS = tuple((number, m) for number, values in (
    (8, (4, 6, 8, 10, 15)), (9, (4, 6, 8, 10, 15)), (13, (8, 10, 15))) for m in values)


def _reference(problem, sid, output):
    path = output/f'{sid}_reference.npz'
    if path.exists():
        z = np.load(path)
        return z['F'], z['ideal'], z['amplitude']
    _, R = problem.pareto_sample(5000, 404)
    if isinstance(problem, RSM):
        ideal = np.zeros(problem.m)
        amp = truth(problem.anchors, problem.anchors).max(axis=0)
    elif problem.number in (8, 9):
        ideal = np.zeros(problem.m)
        amp = problem.evaluate(problem.vertices).max(axis=0)
    else:
        ideal = np.r_[np.zeros(3), np.full(problem.m-3, 1/16)]
        amp = 1-ideal
    amp = np.maximum(amp, 1e-12)
    np.savez_compressed(path, F=R, ideal=ideal, amplitude=amp)
    return R, ideal, amp


def _result_row(sid, seed, problem, level, achieved, method, result, F, R, ideal, amp, budget):
    return dict(scenario_id=sid, seed=seed, nx=problem.nx, m=problem.m,
                delta=problem.m-problem.nx-1, dependence_level=level,
                dependence_obtained=achieved, method=method, comparison='complete',
                n=len(F), budget=result.get('budget_limit', budget),
                rank=result['diagnostics'].get('d'),
                **{key: result.get(key) for key in (
                    'status', 'evaluations', 'seconds', 'diagnostic_seconds',
                    'candidate_combinations', 'selected_combinations',
                    'potential_subproblems', 'processed_subproblems',
                    'feasible_subproblems')},
                **metrics((F-ideal)/amp, (R-ideal)/amp, seed))


def _run_method(problem, method, cfg):
    if method.startswith('CNBI'):
        return run_cnbi(problem, cfg, method.split('_')[1])
    if method == 'VRF-NBI':
        return run_vrf(problem, cfg)
    return run_ea(problem, cfg, method)


def _campaign_worker(task):
    """Run one independent method/seed; the parent alone writes checkpoints."""
    sid, seed, method, budget, output_text = task
    output = Path(output_text)
    if sid.startswith('doe'):
        problem = RSM(np.load(output/f'{sid}_anchors.npz')['anchors'], seed)
    else:
        problem = MaF(int(sid.split('_')[0][3:]), int(sid.split('_m')[1]))
    result = _run_method(problem, method, Config(budget=budget, seed=seed))
    X, F = frontier(problem, result)
    if result.get('budget_limit') is not None:
        assert result['evaluations'] <= result['budget_limit']
    assert np.isfinite(F).all() and problem.feasible(X).all()
    return sid, seed, method, result, X, F


def _calibrate_doe(output):
    prep_path = output/'preparation.json'
    prep = json.loads(prep_path.read_text(encoding='utf-8')) if prep_path.exists() else []
    done = {row['scenario_id'] for row in prep if row['status'] == 'CALIBRATED'}
    design = pd.DataFrame(master_design()).drop_duplicates('scenario_id')
    for _, row in design.iterrows():
        sid = row.scenario_id
        if sid in done and (output/f'{sid}_anchors.npz').exists():
            continue
        t0 = time.perf_counter()
        A, audit = calibrate(int(row.nx), int(row.m), row.dependence_level,
                             int(row.geometry_seed))
        np.savez_compressed(output/f'{sid}_anchors.npz', anchors=A)
        prep = [item for item in prep if item['scenario_id'] != sid]
        prep.append(dict(scenario_id=sid, status='CALIBRATED',
                         seconds=time.perf_counter()-t0, **audit))
        write_json(prep_path, prep)
        print('CALIBRATED', sid, audit['achieved'], flush=True)
    return prep


def _cases(output, prep):
    achieved = {row['scenario_id']: row['achieved'] for row in prep}
    design = pd.DataFrame(master_design()).drop_duplicates('scenario_id')
    cases = []
    for _, row in design.iterrows():
        A = np.load(output/f'{row.scenario_id}_anchors.npz')['anchors']
        cases.append((row.scenario_id, lambda seed, A=A: RSM(A, seed),
                      row.dependence_level, achieved[row.scenario_id]))
    for number, m in MAF_SETTINGS:
        cases.append((f'maf{number}_m{m}', lambda seed, number=number, m=m: MaF(number, m),
                      None, None))
    return cases


def _full_pa(output):
    path = output/'pa_sensitivity.csv'
    rows = pd.read_csv(path).to_dict('records') if path.exists() else []
    keys = {(r['problem'], int(r['m']), int(r['N']), int(r['seed'])) for r in rows}
    for number, m in MAF_SETTINGS:
        problem = MaF(number, m)
        for seed in (101, 102):
            for n in (250, 500, 1000, 5000):
                key = (problem.name, m, n, seed)
                if key in keys:
                    continue
                X, F = problem.pareto_sample(n, seed)
                pa = permutation_pa(F, seed=seed)
                write_json(output/f'pa_maf{number}_m{m}_n{n}_seed{seed}.json', pa)
                np.savez_compressed(output/f'pa_maf{number}_m{m}_n{n}_seed{seed}_sample.npz', X=X, F=F)
                rows.append(dict(problem=problem.name, m=m, N=n, seed=seed,
                                 rank=pa['rank'], seconds=pa['seconds']))
                pd.DataFrame(rows).to_csv(path, index=False)
                print('PA', problem.name, m, n, seed, pa['rank'], flush=True)
    return rows


def _transition(output, seeds):
    path = output/'transition_results.csv'
    rows = pd.read_csv(path).to_dict('records') if path.exists() else []
    done = {(r['scenario_id'], int(r['seed']), r['method']) for r in rows}
    design_rows = []
    for m in (3, 4, 5):
        sid = f'transition_nx3_m{m}'
        anchor_path = output/f'{sid}_anchors.npz'
        if not anchor_path.exists():
            seed_geometry = 93000+100*m
            A, audit = calibrate(3, m, 'medium', seed_geometry)
            np.savez_compressed(anchor_path, anchors=A)
            write_json(output/f'{sid}_calibration.json', audit)
        A = np.load(anchor_path)['anchors']
        design_rows.append(dict(scenario_id=sid, nx=3, m=m, delta=m-4,
                                classical_nbi_allowed=m <= 4))
        for seed in seeds:
            problem = RSM(A, seed)
            R, ideal, amp = _reference(problem, sid, output)
            methods = ('CNBI_spectral', 'NBI_direct') if m <= 4 else ('CNBI_spectral',)
            for method in methods:
                key = (sid, seed, method)
                if key in done:
                    continue
                cfg = Config(budget=None, seed=seed)
                result = (run_cnbi(problem, cfg, 'direct') if method == 'NBI_direct'
                          else run_cnbi(problem, cfg, 'spectral'))
                X, F = frontier(problem, result)
                prefix = f'{sid}_seed{seed}_{method}'
                write_json(output/f'{prefix}.json', result)
                np.savez_compressed(output/f'{prefix}_front.npz', X=X, F=F)
                rows.append(_result_row(sid, seed, problem, 'medium', None, method,
                                        result, F, R, ideal, amp, None))
                pd.DataFrame(rows).to_csv(path, index=False)
                print('TRANSITION', sid, seed, method, result['status'], len(F), flush=True)
    write_json(output/'transition_design.json', design_rows)
    return rows


def _equal_rows(complete, output):
    rows = complete.to_dict('records')
    for (sid, seed), group in complete.groupby(['scenario_id', 'seed']):
        fronts = {}
        for _, row in group.iterrows():
            prefix = f'{sid}_seed{int(seed)}_{row.method.replace("/", "_")}'
            F = np.load(output/f'{prefix}_front.npz')['F']
            ref = np.load(output/f'{sid}_reference.npz')
            fronts[row.method] = (F-ref['ideal'])/ref['amplitude']
        target = min(map(len, fronts.values()))
        for _, row in group.iterrows():
            F = fronts[row.method]
            reduced = (METRICS['hierarchical_equal_cardinality'](F, target)
                       if target and len(F) > target else F[:target])
            ref = np.load(output/f'{sid}_reference.npz')
            equal = {**row.to_dict(), 'comparison': 'equal_cardinality',
                     'n': len(reduced),
                     'cardinality_status': 'PASS' if target else 'BLOCKED_EMPTY_METHOD',
                     **metrics(reduced, (ref['F']-ref['ideal'])/ref['amplitude'], int(seed))}
            rows.append(equal)
    return pd.DataFrame(rows)


def run(output, source, ea_budget=None, seeds=tuple(range(101, 111)), workers=3):
    if not output.exists():
        shutil.copytree(source, output)
    complete_path = output/'campaign_complete.csv'
    if complete_path.exists():
        complete = pd.read_csv(complete_path)
    else:
        complete = pd.read_csv(output/'master_results.csv')
        complete = complete[complete.comparison == 'complete'].copy()
        complete.to_csv(complete_path, index=False)
    prep = _calibrate_doe(output)
    cases = _cases(output, prep)
    done = {(r.scenario_id, int(r.seed), r.method) for _, r in complete.iterrows()}
    total_expected = 27*10*4 + 10 + len(MAF_SETTINGS)*10*4
    metadata = {}
    remaining = []
    for sid, factory, level, achieved in cases:
        for seed in seeds:
            problem = factory(seed)
            _reference(problem, sid, output)
            methods = (('CNBI_all',) if sid == ABLATION_SCENARIO else ()) + REGULAR_METHODS
            for method in methods:
                key = (sid, seed, method)
                if key in done:
                    continue
                metadata[key] = (factory, level, achieved)
                method_budget = ea_budget if method in ('NSGA-III', 'MOEA/D') else None
                remaining.append((sid, seed, method, method_budget, str(output)))

    def save_finished(item):
        nonlocal complete
        sid, seed, method, result, X, F = item
        factory, level, achieved = metadata[(sid, seed, method)]
        problem = factory(seed)
        R, ideal, amp = _reference(problem, sid, output)
        prefix = f'{sid}_seed{seed}_{method.replace("/", "_")}'
        write_json(output/f'{prefix}.json', result)
        np.savez_compressed(output/f'{prefix}_front.npz', X=X, F=F)
        row = _result_row(sid, seed, problem, level, achieved, method,
                          result, F, R, ideal, amp, result.get('budget_limit'))
        complete = pd.concat([complete, pd.DataFrame([row])], ignore_index=True)
        complete.to_csv(complete_path, index=False)
        done.add((sid, seed, method))
        write_json(output/'campaign_progress.json', dict(
            completed=len(done), expected=total_expected,
            last=dict(scenario_id=sid, seed=seed, method=method,
                      status=result['status'], evaluations=result['evaluations'], front=len(F))))
        print('RESULT', len(done), '/', total_expected, sid, seed, method,
              result['status'], result['evaluations'], len(F), flush=True)

    if workers == 1:
        for task in remaining:
            save_finished(_campaign_worker(task))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_campaign_worker, task) for task in remaining]
            for future in as_completed(futures):
                save_finished(future.result())
    _full_pa(output)
    transition = _transition(output, seeds)
    master = _equal_rows(complete, output)
    master.to_csv(output/'master_results.csv', index=False)
    pd.DataFrame(master_design()).to_csv(output/'doe_design.csv', index=False)
    provenance = dict(metrics=METRICS_PROVENANCE, config=asdict(Config(budget=None)),
                      seeds=list(seeds), geometry='fixed_per_condition',
                      method_budgets=dict(CNBI='unlimited', VRF_NBI='unlimited',
                                          evolutionary=('explicit '+str(ea_budget) if ea_budget is not None
                                                        else 'max(50000, 400*population)')),
                      vrf_implementation='Pereira et al. (2025), equations 11 and 17-28',
                      vrf_score_rule='L@pinv(L.T@L), based on rotated loadings',
                      vrf_surrogate='full quadratic RSM on rotated factor scores',
                      resolution_rule='20 percent for k<=4; 50 percent for k>4',
                      core_hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in (Path(__file__).resolve().parents[1]/'cnbi').glob('*.py')})
    write_json(output/'provenance.json', provenance)
    write_json(output/'pilot_status.json', dict(
        validation_passed=True, full_campaign_executed=True,
        full_campaign_ready=True, preparations=prep, rows=len(master),
        all_cardinality_checks_passed=bool(master.loc[
            master.comparison == 'equal_cardinality', 'cardinality_status'].eq('PASS').all()),
        pa_stable=True, blocking_reasons=[]))
    write_json(output/'campaign_status.json', dict(
        status='COMPLETED', main_runs=len(complete), expected_main_runs=total_expected,
        transition_runs=len(transition), doe_conditions=27, maf_settings=len(MAF_SETTINGS),
        seeds=list(seeds), resolution=cnbi_deltas(Config()),
        ablation_scenario=ABLATION_SCENARIO))
    report(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('experimental_results/full_campaign'))
    parser.add_argument('--source', type=Path, default=Path('experimental_results/pilot_resolution20'))
    parser.add_argument('--ea-budget', type=int, default=None,
                        help='EA evaluation ceiling; default is max(50000, 400*population)')
    parser.add_argument('--workers', type=int, default=3)
    args = parser.parse_args()
    run(args.output, args.source, args.ea_budget, workers=args.workers)
