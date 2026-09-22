"""Re-run CNBI-family arms after changing k=2 and k=3 resolution to 20%."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

from .benchmarks import MaF
from .comparators import run_vrf
from .doe import RSM
from .pilot import frontier, write_json, ABLATION_SCENARIO
from .report import report
from .solver import Config, run_cnbi, cnbi_deltas


def revise(source, output):
    if output.exists():
        raise ValueError('Use a new output directory to preserve earlier evidence')
    shutil.copytree(source, output)
    data = pd.read_csv(output/'master_results.csv')
    changed = []
    block = data[(data.comparison == 'complete') &
                 data.method.isin(['CNBI_all', 'CNBI_spectral', 'VRF-NBI'])]
    for _, row in block.iterrows():
        sid, seed, method = row.scenario_id, int(row.seed), row.method
        if sid.startswith('doe'):
            problem = RSM(np.load(output/f'{sid}_anchors.npz')['anchors'], seed)
        else:
            problem = MaF(int(sid.split('_')[0][3:]), int(row.m))
        cfg = Config(budget=None, seed=seed)
        print('RUN', sid, seed, method, flush=True)
        result = (run_vrf(problem, cfg) if method == 'VRF-NBI'
                  else run_cnbi(problem, cfg, method.split('_')[1]))
        X, F = frontier(problem, result)
        assert np.isfinite(F).all() and problem.feasible(X).all()
        prefix = f'{sid}_seed{seed}_{method}'
        write_json(output/f'{prefix}.json', result)
        np.savez_compressed(output/f'{prefix}_front.npz', X=X, F=F)
        ix = ((data.scenario_id == sid) & (data.seed == seed) &
              (data.method == method))
        for key in ('status', 'evaluations', 'seconds', 'diagnostic_seconds',
                    'candidate_combinations', 'selected_combinations',
                    'potential_subproblems', 'processed_subproblems',
                    'feasible_subproblems'):
            data.loc[ix, key] = result.get(key)
        data.loc[ix & data.comparison.eq('complete'), 'n'] = len(F)
        data.loc[ix, 'budget'] = np.nan
        data.loc[ix, 'rank'] = result['diagnostics'].get('d')
        changed.append(dict(scenario_id=sid, seed=seed, method=method,
                            status=result['status'], evaluations=result['evaluations'],
                            front_size=len(F)))
        print('RESULT', changed[-1], flush=True)
    data.to_csv(output/'master_results.csv', index=False)
    provenance_path = output/'provenance.json'
    provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
    provenance['config'] = asdict(Config(budget=None))
    write_json(provenance_path, provenance)
    write_json(output/'RESOLUTION_REVISION.json', dict(
        source=str(source), ablation_scenario=ABLATION_SCENARIO,
        changed_runs=changed, reused_ea_runs=24,
        resolutions=cnbi_deltas(Config()), core_config_changed=False))
    previous = json.loads((source/'VERIFICATION.json').read_text(encoding='utf-8'))
    write_json(output/'VERIFICATION.json', dict(
        previous=previous, revision='CNBI k2/k3 resolution 20 percent',
        revised_runs=len(changed), reused_ea_runs=24,
        resolutions=cnbi_deltas(Config()), core_config_changed=False))
    report(output)
    maf9 = data[(data.scenario_id == 'maf9_m6') &
                (data.comparison == 'complete') &
                data.method.isin(['CNBI_spectral', 'VRF-NBI'])]
    lines = ['# Diagnóstico MaF9 — resolução de 20%', '',
             'A correção do adaptador do otimizador permanece válida. Nesta revisão, CNBI_spectral e VRF-NBI '
             'foram reexecutados com Δ₂=Δ₃=0,20; CNBI_all não integra o benchmark MaF.', '',
             '| Seed | Método | Estado | Avaliações | Frente |',
             '|---:|---|---|---:|---:|']
    for _, row in maf9.iterrows():
        lines.append(f'| {int(row.seed)} | {row.method} | {row.status} | '
                     f'{int(row.evaluations)} | {int(row.n)} |')
    (output/'MAF9_DIAGNOSTICO.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    revise(args.source, args.output)
