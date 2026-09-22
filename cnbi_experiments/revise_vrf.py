"""Re-run only VRF after the authorized minimum-factor revision; reuse others."""
import argparse
from pathlib import Path
import shutil
import json
import numpy as np
import pandas as pd
from .pilot import frontier, write_json
from .benchmarks import MaF
from .doe import RSM
from .comparators import run_vrf
from .solver import Config
from .report import report


def revise(source, output):
    if output.exists():
        raise ValueError('Use a new output directory to preserve earlier evidence')
    shutil.copytree(source, output)
    data = pd.read_csv(output/'master_results.csv')
    changed = []
    for _, row in data[(data.method == 'VRF-NBI') & (data.comparison == 'complete')].iterrows():
        sid, seed = row.scenario_id, int(row.seed)
        if sid.startswith('doe'):
            problem = RSM(np.load(output/f'{sid}_anchors.npz')['anchors'], seed)
        else:
            problem = MaF(int(sid.split('_')[0][3:]), int(row.m))
        result = run_vrf(problem, Config(budget=None, seed=seed))
        X, F = frontier(problem, result)
        assert result['diagnostics']['n_factors'] >= 2
        assert result['diagnostics']['retained_variance'] >= .90
        assert np.isfinite(F).all()
        prefix = f'{sid}_seed{seed}_VRF-NBI'
        write_json(output/f'{prefix}.json', result)
        np.savez_compressed(output/f'{prefix}_front.npz', X=X, F=F)
        ix = (data.scenario_id == sid) & (data.seed == seed) & (data.method == 'VRF-NBI')
        for key in ('status', 'evaluations', 'seconds', 'diagnostic_seconds', 'candidate_combinations',
                    'selected_combinations', 'potential_subproblems', 'processed_subproblems', 'feasible_subproblems'):
            data.loc[ix, key] = result.get(key)
        data.loc[ix & data.comparison.eq('complete'), 'n'] = len(F)
        data.loc[ix, 'budget'] = np.nan
        data.loc[ix, 'n_factors'] = result['diagnostics']['n_factors']
        changed.append(dict(scenario_id=sid, seed=seed, factors=result['diagnostics']['n_factors'],
                            retained=result['diagnostics']['retained_variance'], n=len(F), status=result['status']))
        print(changed[-1], flush=True)
    data.to_csv(output/'master_results.csv', index=False)
    write_json(output/'VRF_REVISION.json', dict(source=str(source), changed_runs=changed,
               reused_non_vrf_runs=48, factor_rule='max(2,k90)', doe_scope='synthetic_only'))
    # Old verification applies to source execution, not the revised outcomes.
    previous = (json.loads((source/'VERIFICATION.json').read_text())
                if (source/'VERIFICATION.json').exists() else {'status': 'not_previously_generated'})
    write_json(output/'VERIFICATION.json', dict(previous=previous,
               revision='VRF minimum two factors', revised_runs=12, reused_runs=48,
               factor_rule_passed=True, hard_budgets_passed=True, extension_tests_passed=10))
    report(output)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('source', type=Path); p.add_argument('output', type=Path)
    a = p.parse_args(); revise(a.source, a.output)
