"""Calibrate NSGA-III and MOEA/D for every (nx, M) in the synthetic DOE."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import product
import json
from pathlib import Path
import shutil
import time

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from scipy.stats import qmc

from .comparators import EA_CALIBRATION_FILE, ea_budget, run_ea
from .doe import RSM, master_design
from .pilot import frontier, write_json
from .solver import Config


PARAMETER_KEYS = ('n_partitions', 'sbx_probability', 'sbx_eta', 'pm_eta',
                  'neighbor_fraction', 'prob_neighbor_mating')


def _parameters(row):
    return {key: (int(row[key]) if key == 'n_partitions' else float(row[key]))
            for key in PARAMETER_KEYS}


def _id(parameters):
    return '_'.join(f'{key}-{str(parameters[key]).replace(".", "p")}'
                    for key in PARAMETER_KEYS)


def _hv(F, m, seed, samples=4096):
    reference = 1.1
    U = qmc.Sobol(d=m, scramble=True, seed=seed).random_base2(
        int(np.log2(samples)))*reference
    dominated = np.zeros(len(U), bool)
    for start in range(0, len(U), 256):
        block = U[start:start+256]
        dominated[start:start+256] = np.any(
            np.all(F[:, None, :] <= block[None, :, :], axis=2), axis=0)
    return float(reference**m*dominated.mean())


def _worker(task):
    method, sid, seed, parameters, budget, source_text = task
    source = Path(source_text)
    anchors = np.load(source/f'{sid}_anchors.npz')['anchors']
    problem = RSM(anchors, seed)
    started = time.perf_counter()
    result = run_ea(problem, Config(seed=seed, budget=budget), method, parameters)
    _, F = frontier(problem, result)
    reference = np.load(source/f'{sid}_reference.npz')
    Fn = (F-reference['ideal'])/reference['amplitude']
    Rn = (reference['F']-reference['ideal'])/reference['amplitude']
    igd = float(cKDTree(Fn).query(Rn, k=1)[0].mean())
    return dict(method=method, scenario_id=sid, nx=problem.nx, m=problem.m,
                seed=seed, config_id=_id(parameters), **parameters,
                status=result['status'], evaluations=result['evaluations'],
                population=result['diagnostics']['population'],
                generations=result['diagnostics']['generations'],
                IGD=igd, HV=_hv(Fn, problem.m, 9000+problem.m*100+seed),
                infeasibility=0., seconds=time.perf_counter()-started)


def _execute(tasks, output, workers, stage):
    checkpoint = output/'checkpoints'
    checkpoint.mkdir(parents=True, exist_ok=True)
    rows, pending = [], []
    for task in tasks:
        method, sid, seed, parameters, budget, _ = task
        path = checkpoint/f'{stage}_{sid}_{method.replace("/", "_")}_{_id(parameters)}_seed{seed}.json'
        if path.exists():
            rows.append(json.loads(path.read_text(encoding='utf-8')))
        else:
            pending.append((task, path))
    if workers == 1:
        iterable = ((_worker(task), path) for task, path in pending)
        for row, path in iterable:
            write_json(path, row); rows.append(row)
            print('TUNING', stage, row['scenario_id'], row['method'], row['seed'],
                  row['IGD'], flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_worker, task): path for task, path in pending}
            for future in as_completed(futures):
                row = future.result(); write_json(futures[future], row); rows.append(row)
                print('TUNING', stage, row['scenario_id'], row['method'], row['seed'],
                      row['IGD'], flush=True)
    return rows


def _rank(rows):
    data = pd.DataFrame(rows)
    ranked = data.groupby('config_id', as_index=False).agg(
        IGD_median=('IGD', 'median'), HV_median=('HV', 'median'),
        infeasibility_median=('infeasibility', 'median'),
        IGD_iqr=('IGD', lambda x: x.quantile(.75)-x.quantile(.25)),
        seconds_median=('seconds', 'median'))
    return ranked.sort_values(
        ['IGD_median', 'HV_median', 'infeasibility_median', 'IGD_iqr', 'seconds_median'],
        ascending=[True, False, True, True, True]).reset_index(drop=True)


def _prior(old, method, m):
    label = 'NSGAIII' if method == 'NSGA-III' else 'MOEAD'
    available = [4, 6, 12]
    nearest = min(available, key=lambda value: (abs(value-m), value))
    return {key: old[f'{label}_m{nearest}'][key] for key in PARAMETER_KEYS}


def _balanced(operator_partitions, prior):
    p0, p1 = operator_partitions
    tuples = [(operator_partitions[i % 2], (.9, 1.)[(i//2) % 2],
               (10., 20., 30.)[i % 3], (15., 20., 30.)[(i//3+i) % 3])
              for i in range(12)]
    configs = [dict(n_partitions=p, sbx_probability=sp, sbx_eta=se, pm_eta=pe,
                    neighbor_fraction=.2, prob_neighbor_mating=.9)
               for p, sp, se, pe in tuples]
    candidate = dict(prior)
    if _id(candidate) not in {_id(x) for x in configs}:
        configs[-1] = candidate
    assert len({_id(x) for x in configs}) == 12
    return configs


def run(source, output, workers=3):
    output.mkdir(parents=True, exist_ok=True)
    old_path = (Path(__file__).resolve().parents[1]/'CNBI-Synthetic-Benchmarks'/'results'/
                'synthetic'/'tuning'/'chosen_parameters.json')
    old = json.loads(old_path.read_text(encoding='utf-8'))
    design = pd.DataFrame(master_design()).drop_duplicates('scenario_id')
    medium = design[design.dependence_level.eq('medium')].sort_values(['nx', 'm'])
    screening_rows, finalist_rows, ranking_rows, chosen = [], [], [], {}

    for condition in medium.itertuples():
        sid, nx, m = condition.scenario_id, int(condition.nx), int(condition.m)
        for method in ('NSGA-III', 'MOEA/D'):
            prior = _prior(old, method, m)
            base = dict(sbx_probability=1., sbx_eta=20., pm_eta=20.,
                        neighbor_fraction=.2, prob_neighbor_mating=.9)
            stage_a = [dict(n_partitions=p, **base) for p in (2, 3, 4)]
            tasks = [(method, sid, 1, p, 50_000, str(source)) for p in stage_a]
            rows_a = _execute(tasks, output, workers, 'A')
            screening_rows.extend({**row, 'stage': 'A'} for row in rows_a)
            best_partitions = []
            for config_id in _rank(rows_a).head(2).config_id:
                best_partitions.append(int(next(r for r in rows_a
                                                if r['config_id'] == config_id)['n_partitions']))

            stage_b = _balanced(best_partitions, prior)
            tasks = [(method, sid, 1, p, 50_000, str(source)) for p in stage_b]
            rows_b = _execute(tasks, output, workers, 'B')
            screening_rows.extend({**row, 'stage': 'B'} for row in rows_b)
            terminal = rows_b
            if method == 'MOEA/D':
                best_b_id = _rank(rows_b).iloc[0].config_id
                best_b = _parameters(next(r for r in rows_b if r['config_id'] == best_b_id))
                stage_c = [{**best_b, 'neighbor_fraction': fraction,
                            'prob_neighbor_mating': mating}
                           for fraction, mating in product((.1, .2, .3), (.7, .9, 1.))]
                tasks = [(method, sid, 1, p, 50_000, str(source)) for p in stage_c]
                rows_c = _execute(tasks, output, workers, 'C')
                screening_rows.extend({**row, 'stage': 'C'} for row in rows_c)
                terminal = rows_c

            top = _rank(terminal).head(3).config_id.tolist()
            configs = [_parameters(next(r for r in terminal if r['config_id'] == cid))
                       for cid in top]
            tasks = [(method, sid, seed, p, ea_budget(m), str(source))
                     for p in configs for seed in (1, 2, 3)]
            final = _execute(tasks, output, workers, 'FINAL')
            finalist_rows.extend(final)
            ranking = _rank(final)
            ranking.insert(0, 'm', m); ranking.insert(0, 'nx', nx)
            ranking.insert(0, 'method', method); ranking_rows.extend(ranking.to_dict('records'))
            winner = ranking.iloc[0].config_id
            proto = next(row for row in final if row['config_id'] == winner)
            key = f'{method}_nx{nx}_m{m}'
            chosen[key] = dict(status='COMPLETED', scenario_id=sid,
                               calibration_seeds=[1, 2, 3],
                               screening_budget=50_000, final_budget=ea_budget(m),
                               source_prior=('legacy_full_m4_m6_m12_nearest'),
                               selection_order=['IGD_median', 'HV_median_desc',
                                                'infeasibility_median', 'IGD_iqr',
                                                'seconds_median'],
                               **_parameters(proto))
            write_json(output/'chosen_parameters.partial.json', chosen)

    pd.DataFrame(screening_rows).to_csv(output/'tuning_screening.csv', index=False)
    pd.DataFrame(finalist_rows).to_csv(output/'tuning_finalists.csv', index=False)
    pd.DataFrame(ranking_rows).to_csv(output/'tuning_rankings.csv', index=False)
    write_json(output/'chosen_parameters.json', chosen)
    shutil.copy2(output/'chosen_parameters.json', EA_CALIBRATION_FILE)
    write_json(output/'calibration_status.json', dict(
        status='COMPLETED', combinations=len(chosen), screening_runs=len(screening_rows),
        finalist_runs=len(finalist_rows), old_calibration=str(old_path),
        final_parameter_file=str(EA_CALIBRATION_FILE)))
    return chosen


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=3)
    args = parser.parse_args()
    run(args.source, args.output, args.workers)
