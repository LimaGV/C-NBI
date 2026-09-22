"""Re-run the 270 VRF arms on the corrected synthetic-generator campaign."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import json
import shutil

import numpy as np
import pandas as pd

from .analysis import analyze
from .campaign import _campaign_worker, _equal_rows, _reference, _result_row
from .doe import RSM
from .pilot import write_json


def revise(source, output, workers=3):
    if output.exists():
        raise ValueError('Use a new output directory')
    shutil.copytree(source, output)
    original = pd.read_csv(output/'campaign_complete.csv')
    complete = original[~original.method.eq('VRF-NBI')].copy()
    prep = json.loads((output/'preparation.json').read_text(encoding='utf-8'))
    achieved = {r['scenario_id']: r['achieved'] for r in prep}
    tasks = [(sid, seed, 'VRF-NBI', 50000, str(output))
             for sid in sorted(original.scenario_id.unique()) for seed in range(101, 111)]

    def save(item):
        nonlocal complete
        sid, seed, method, result, X, F = item
        A = np.load(output/f'{sid}_anchors.npz')['anchors']
        problem = RSM(A, seed)
        R, ideal, amp = _reference(problem, sid, output)
        prefix = f'{sid}_seed{seed}_VRF-NBI'
        write_json(output/f'{prefix}.json', result)
        np.savez_compressed(output/f'{prefix}_front.npz', X=X, F=F)
        level = sid.rsplit('_', 1)[1]
        row = _result_row(sid, seed, problem, level, achieved[sid], method,
                          result, F, R, ideal, amp, 50000)
        complete = pd.concat([complete, pd.DataFrame([row])], ignore_index=True)
        complete.to_csv(output/'campaign_complete.csv', index=False)
        print('DOE_VRF', len(complete)-810, '/ 270', sid, seed,
              result['status'], len(F), flush=True)

    with ProcessPoolExecutor(max_workers=workers) as pool:
        for item in as_completed([pool.submit(_campaign_worker, task) for task in tasks]):
            save(item.result())
    master = _equal_rows(complete, output)
    master.to_csv(output/'master_results.csv', index=False)
    analyze(output)
    diagnostics = []
    for row in complete[complete.method.eq('VRF-NBI')].itertuples():
        d = json.loads((output/f'{row.scenario_id}_seed{int(row.seed)}_VRF-NBI.json').read_text(
            encoding='utf-8'))['diagnostics']
        diagnostics.append(dict(scenario_id=row.scenario_id, seed=int(row.seed), status=row.status,
            front=int(row.n), n_factors=int(d['n_factors']), retained_variance=d['retained_variance'],
            minimum_predicted_r2=min(d['factor_predicted_r2']), surrogate_warning=d['surrogate_warning']))
    pd.DataFrame(diagnostics).to_csv(output/'vrf_diagnostics.csv', index=False)
    write_json(output/'VRF_FAITHFUL_REVISION.json', dict(
        source=str(source), rerun_vrf_arms=270, reused_non_vrf_arms=810,
        generator='corrected multidimensional legacy synthetic generator',
        implementation='Pereira et al. (2025), equations 11 and 17-28',
        factor_rule='max(2,k90)', resolution_rule='20 percent for k<=4; 50 percent for k>4'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('source', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--workers', type=int, default=3)
    a = p.parse_args(); revise(a.source, a.output, a.workers)
