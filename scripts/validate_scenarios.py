"""Strong validation of the authorized nine-scenario audit."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'data'/'generated'/'scenario_audit'; refs=ROOT/'data'/'reference_fronts'/'scenario_audit'
df=pd.read_csv(base/'scenario_diagnostics.csv')
assert len(df)==9 and set(df.m)=={4,6,12} and set(df.level)=={'low','medium','high'}
assert df.within_tolerance.all() and np.max(np.abs(df.achieved-df.target))<=.03 and df.affine_rank.eq(3).all()
for row in df.itertuples():
    scenario=np.load(base/f'{row.scenario}_scenario.npz'); A=scenario['anchors']; ref=np.load(refs/f'{row.scenario}_pareto_reference.npz')
    assert np.array_equal(ref['X'][:len(A)],A) and bool(ref['anchors_included'])
    assert np.allclose(ref['ideal_true'],0)
    assert np.allclose(ref['nadir_true'],np.max(np.sum((A[:,None,:]-A[None,:,:])**2,axis=2),axis=0))
    audit=json.loads((base/f'{row.scenario}_anchor_search.json').read_text(encoding='utf-8'))
    assert audit['attempt_count']>=1 and audit['seed'] and audit['best']['min_anchor_distance']>0
print('SCENARIO_AUDIT: nove cenários aprovados.')
