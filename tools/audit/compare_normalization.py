"""Quantify local versus global payoff normalization without changing CNBI."""
from pathlib import Path
import inspect
import json
import sys

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'CNBI_v1.0'
sys.path.insert(0, str(PACKAGE))

from cnbi import core, payoff, pareto
from cnbi import nbi as nbi_module
from cnbi.config import DELTA_BY_K


def global_solver():
    """Create an audit-only solver by substituting only the normalization source."""
    source = inspect.getsource(nbi_module._solve_nbi_base)
    source = source.replace(
        'def _solve_nbi_base(Bmodel, output_B, indices, Xstar, P, delta, combo_id=0, maxiter=500, max_rescues=8):',
        'def _solve_nbi_global(Bmodel, output_B, indices, Xstar, P, delta, supplied_ideal, supplied_amp, combo_id=0, maxiter=500, max_rescues=8):',
    )
    source = source.replace(
        '    ideal = P.min(1)\n    amp = np.maximum(P.max(1) - ideal, 1e-12)\n',
        '    ideal = np.asarray(supplied_ideal, float)\n    amp = np.asarray(supplied_amp, float)\n',
    )
    namespace = dict(nbi_module.__dict__)
    exec(compile(source, '<audit_global_normalization>', 'exec'), namespace)
    return namespace['_solve_nbi_global']


def front(F):
    return F[pareto.nondominated(F)] if len(F) else F


def symmetric_nearest(A, B):
    if not len(A) or not len(B):
        return {'median': None, 'max': None}
    distances = np.r_[cKDTree(B).query(A)[0], cKDTree(A).query(B)[0]]
    return {'median': float(np.median(distances)), 'max': float(np.max(distances))}


solve_global = global_solver()
records = []
fixture_dir = PACKAGE / 'tests' / 'fixtures'
for fixture in ('m4_low_seed103', 'm6_medium_seed101', 'm12_high_seed101'):
    payload = json.loads((fixture_dir / f'{fixture}.json').read_text(encoding='utf-8'))
    B = np.asarray(payload['B'], float)
    mse = np.asarray(payload['mse'], float)
    inverse = np.asarray(payload['XtX_inv'], float)
    Xstar, P = payoff.individual_payoff(B)
    local_rows, pa = core.cnbi(B, P, Xstar, mse, inverse)
    ideal = P.min(1)
    amp = np.where(P.max(1)-ideal > 1e-12, P.max(1)-ideal, 1)

    global_rows = []
    combo_id = 0
    # Reuse the exact accepted-combination order already produced by the core.
    combos = list(dict.fromkeys(row['combo'] for row in local_rows))
    for combo_tuple in combos:
        combo = np.asarray(combo_tuple, int)
        rows, _, _ = solve_global(
            B[:, combo], B, combo, Xstar[combo], P[np.ix_(combo, combo)],
            DELTA_BY_K[len(combo)], ideal[combo], amp[combo], combo_id=combo_id,
        )
        global_rows.extend(rows)
        combo_id += 1

    if len(local_rows) != len(global_rows):
        raise RuntimeError(f'{fixture}: cardinalidades brutas incompatíveis')
    keys_local = [(row['combo'], row['beta_id']) for row in local_rows]
    keys_global = [(row['combo'], row['beta_id']) for row in global_rows]
    if keys_local != keys_global:
        raise RuntimeError(f'{fixture}: ordem incompatível')

    XL = np.vstack([row['x'] for row in local_rows])
    XG = np.vstack([row['x'] for row in global_rows])
    FL = np.vstack([row['F_rsm'] for row in local_rows])
    FG = np.vstack([row['F_rsm'] for row in global_rows])
    valid_l = np.array([row['accepted'] for row in local_rows])
    valid_g = np.array([row['accepted'] for row in global_rows])
    union_ideal = np.minimum(FL.min(0), FG.min(0))
    union_amp = np.maximum(np.maximum(FL.max(0), FG.max(0))-union_ideal, 1e-12)
    front_l = front((FL[valid_l]-union_ideal)/union_amp)
    front_g = front((FG[valid_g]-union_ideal)/union_amp)
    post_l = pareto.postprocess_frontier(XL[valid_l], FL[valid_l])
    post_g = pareto.postprocess_frontier(XG[valid_g], FG[valid_g])
    decision_distance = np.linalg.norm(XL-XG, axis=1)
    records.append({
        'fixture': fixture,
        'objectives': B.shape[1],
        'combinations': len(combos),
        'raw_candidates_each': len(local_rows),
        'accepted_local': int(valid_l.sum()),
        'accepted_global': int(valid_g.sum()),
        'same_acceptance_status': int(np.sum(valid_l == valid_g)),
        'decision_distance_median': float(np.median(decision_distance)),
        'decision_distance_p95': float(np.percentile(decision_distance, 95)),
        'decision_distance_max': float(decision_distance.max()),
        'same_decision_within_1e-8': int(np.sum(decision_distance <= 1e-8)),
        'estimated_pareto_rows_local_exact': len(front_l),
        'estimated_pareto_rows_global_exact': len(front_g),
        'estimated_postprocessed_rows_local_default': post_l['output_count'],
        'estimated_postprocessed_rows_global_default': post_g['output_count'],
        'normalized_front_symmetric_nearest': symmetric_nearest(front_l, front_g),
    })

result = {
    'purpose': 'audit only; global normalization is not included in the package API',
    'local_definition': 'notebook 03: each subproblem recomputes ideal/range from its reduced payoff',
    'global_definition': 'v0-style audit: each subproblem uses ideal/range of the full payoff restricted to its objectives',
    'selection': 'identical global spectral selection; only NBI local normalization changes',
    'records': records,
}
(PACKAGE / 'provenance' / 'NORMALIZATION_IMPACT.json').write_text(
    json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
)
print(json.dumps(result, indent=2, ensure_ascii=False))
