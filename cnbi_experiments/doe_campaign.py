"""Checkpointed DOE-only campaign with the multidimensional legacy generator."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd

from .analysis import inference
from .campaign import REGULAR_METHODS, _campaign_worker, _equal_rows, _reference, _result_row
from .doe import CORRELATION_TOLERANCE, RSM, calibrate, master_design
from .pilot import write_json


def run(output, ea_budget=None, seeds=tuple(range(101, 111)), workers=3):
    output.mkdir(parents=True, exist_ok=True)
    complete_path = output/'campaign_complete.csv'
    complete = pd.read_csv(complete_path) if complete_path.exists() else pd.DataFrame()
    prep_path = output/'preparation.json'
    prep = json.loads(prep_path.read_text(encoding='utf-8')) if prep_path.exists() else []
    calibrated = {x['scenario_id'] for x in prep}
    design = pd.DataFrame(master_design()).drop_duplicates('scenario_id')

    for _, row in design.iterrows():
        sid = row.scenario_id
        if sid in calibrated and (output/f'{sid}_anchors.npz').exists():
            continue
        started = time.perf_counter()
        spread_tiebreak = (int(row.nx), int(row.m), row.dependence_level) == (3, 7, 'high')
        anchors, audit = calibrate(int(row.nx), int(row.m), row.dependence_level,
                                   int(row.geometry_seed), prefer_spread=spread_tiebreak)
        np.savez_compressed(output/f'{sid}_anchors.npz', anchors=anchors)
        prep.append(dict(scenario_id=sid, status='CALIBRATED',
                         seconds=time.perf_counter()-started, **audit))
        write_json(prep_path, prep)
        print('CALIBRATED', sid, audit['achieved'], flush=True)

    achieved = {x['scenario_id']: x['achieved'] for x in prep}
    done = set() if complete.empty else {(r.scenario_id, int(r.seed), r.method) for _, r in complete.iterrows()}
    metadata, tasks = {}, []
    for _, row in design.iterrows():
        sid = row.scenario_id
        anchors = np.load(output/f'{sid}_anchors.npz')['anchors']
        factory = lambda seed, A=anchors: RSM(A, seed)
        _reference(factory(seeds[0]), sid, output)
        for seed in seeds:
            for method in REGULAR_METHODS:
                key = (sid, seed, method)
                if key not in done:
                    metadata[key] = (factory, row.dependence_level, achieved[sid])
                    # CNBI and VRF finish without an evaluation ceiling.  For
                    # EAs, None activates the population-scaled rule in run_ea;
                    # an explicit value remains available for sensitivity runs.
                    method_budget = ea_budget if method in ('NSGA-III', 'MOEA/D') else None
                    tasks.append((sid, seed, method, method_budget, str(output)))

    def save(item):
        nonlocal complete
        sid, seed, method, result, X, F = item
        factory, level, obtained = metadata[(sid, seed, method)]
        problem = factory(seed)
        R, ideal, amp = _reference(problem, sid, output)
        prefix = f'{sid}_seed{seed}_{method.replace("/", "_")}'
        write_json(output/f'{prefix}.json', result)
        np.savez_compressed(output/f'{prefix}_front.npz', X=X, F=F)
        row = _result_row(sid, seed, problem, level, obtained, method,
                          result, F, R, ideal, amp, result.get('budget_limit'))
        complete = pd.concat([complete, pd.DataFrame([row])], ignore_index=True)
        complete.to_csv(complete_path, index=False)
        done.add((sid, seed, method))
        write_json(output/'campaign_progress.json', dict(
            completed=len(done), expected=1080,
            last=dict(scenario_id=sid, seed=seed, method=method,
                      status=result['status'], evaluations=result['evaluations'], front=len(F))))
        print('RESULT', len(done), '/', 1080, sid, seed, method,
              result['status'], result['evaluations'], len(F), flush=True)

    if workers == 1:
        for task in tasks:
            save(_campaign_worker(task))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_campaign_worker, task) for task in tasks]
            for future in as_completed(futures):
                save(future.result())

    master = _equal_rows(complete, output)
    master.to_csv(output/'master_results.csv', index=False)
    master.to_csv(output/'DOE_synthetic_results.csv', index=False)
    pd.DataFrame(master_design()).to_csv(output/'doe_design.csv', index=False)
    inference(master, output)
    empty = complete[complete.n.eq(0)]
    write_json(output/'campaign_status.json', dict(
        status='COMPLETED' if len(complete) == 1080 else 'INCOMPLETE',
        runs=len(complete), expected_runs=1080,
        conditions=int(complete.scenario_id.nunique()), empty_fronts=len(empty),
        method_budgets=dict(CNBI='unlimited', VRF_NBI='unlimited',
                            evolutionary=('explicit '+str(ea_budget) if ea_budget is not None
                                          else 'max(50000, 400*population)')),
        generator='multidimensional legacy Sobol and regular starts',
        correlation_tolerance=CORRELATION_TOLERANCE,
        all_cardinality_checks_passed=not len(empty)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('experimental_results/doe_legacy_generator'))
    parser.add_argument('--ea-budget', type=int, default=None,
                        help='EA evaluation ceiling; default is max(50000, 400*population)')
    parser.add_argument('--workers', type=int, default=3)
    args = parser.parse_args()
    run(args.output, args.ea_budget, workers=args.workers)
