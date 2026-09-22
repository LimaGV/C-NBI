"""Re-run every VRF arm with the paper-faithful implementation; reuse others."""
import argparse
import json
from pathlib import Path
import shutil

import pandas as pd

from .campaign import run
from .pilot import write_json


def revise(source, output, workers=3):
    if output.exists():
        raise ValueError('Use a new output directory to preserve earlier evidence')
    shutil.copytree(source, output)
    complete_path = output/'campaign_complete.csv'
    complete = pd.read_csv(complete_path)
    old_vrf = complete[complete.method.eq('VRF-NBI')].copy()
    reused = complete[~complete.method.eq('VRF-NBI')].copy()
    if len(old_vrf) != 400:
        raise ValueError(f'Expected 400 VRF runs, found {len(old_vrf)}')
    reused.to_csv(complete_path, index=False)
    run(output, source, ea_budget=None, workers=workers)
    final = pd.read_csv(output/'campaign_complete.csv')
    new_vrf = final[final.method.eq('VRF-NBI')]
    diagnostics = []
    for row in new_vrf.itertuples():
        path = output/f'{row.scenario_id}_seed{int(row.seed)}_VRF-NBI.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        diag = data['diagnostics']
        diagnostics.append(dict(
            scenario_id=row.scenario_id, seed=int(row.seed), status=row.status,
            front=int(row.n), n_factors=int(diag['n_factors']),
            retained_variance=float(diag['retained_variance']),
            minimum_predicted_r2=min(diag['factor_predicted_r2']),
            surrogate_warning=bool(diag['surrogate_warning'])))
    pd.DataFrame(diagnostics).to_csv(output/'vrf_diagnostics.csv', index=False)
    write_json(output/'VRF_FAITHFUL_REVISION.json', dict(
        source=str(source), rerun_vrf_arms=len(new_vrf),
        reused_non_vrf_arms=len(reused),
        implementation='Pereira et al. (2025), equations 11 and 17-28',
        factor_rule='max(2,k90)',
        resolution_rule='20 percent for k<=4; 50 percent for k>4',
        tests='11 passed before campaign', diagnostics_file='vrf_diagnostics.csv'))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--workers', type=int, default=3)
    a = p.parse_args()
    revise(a.source, a.output, a.workers)
