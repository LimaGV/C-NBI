"""Prepare small RSM regression inputs using the exact notebook 03 setup."""
from pathlib import Path
import json
import os
import sys

for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import numpy as np
from itertools import product

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'CNBI-Synthetic-Benchmarks'
DST=ROOT/'CNBI_v1.0/tests/fixtures'
sys.stdout.reconfigure(encoding='utf-8')
ns={}
exec(compile((DST/'original_core.py.txt').read_text(encoding='utf-8'),'original_core','exec'),ns)
ALPHA=ns['ALPHA']; z=ns['z']
manifest=[]
for scenario,seed in [('m4_low',103),('m6_medium',101),('m12_high',101)]:
    A=np.load(SRC/'data/generated'/f'{scenario}_scenario.npz')['anchors']
    # Exact setup from notebook 03, cell 2 lines 159-160 / cell 4 lines 47-48.
    X=np.vstack([np.array(list(product([-1.,1.],repeat=3))),np.vstack([np.eye(3)*ALPHA,-np.eye(3)*ALPHA]),np.zeros((5,3))])
    D=np.vstack([z(x) for x in X]); F=np.sum((X[:,None,:]-A[None,:,:])**2,axis=2)
    rng=np.random.default_rng(seed); sig=np.sqrt(F.var(0,ddof=1)*(.05/.95)); Y=F+rng.normal(0,sig,F.shape)
    B=np.linalg.lstsq(D,Y,rcond=None)[0]; E=Y-D@B; mse=np.sum(E*E,axis=0)/(19-10)
    name=f'{scenario}_seed{seed}'
    payload={'scenario':scenario,'seed':seed,'B':B.tolist(),'mse':mse.tolist(),'XtX_inv':np.linalg.inv(D.T@D).tolist()}
    (DST/f'{name}.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    matches=list((SRC/'results/synthetic/checkpoints').glob(f'full_{scenario}_seed{seed}_CNBI_*.npz'))
    canonical=[]
    print(name,'historical checkpoints',len(matches))
    for path in matches:
        with np.load(path,allow_pickle=False) as data:
            meta=json.loads(str(data['metadata']))
            print(path.name,meta.get('identity',{}).get('implementation_fingerprint'),data['X'].shape)
            if meta.get('identity',{}).get('implementation_fingerprint') == 'common-nbi-valid-payoff-v4':
                canonical.append(path)
    if len(canonical) != 1:
        raise RuntimeError(f'{name}: esperado exatamente um checkpoint normativo v4; obtidos {canonical}')
    path=canonical[0]
    if scenario=='m4_low':
        with np.load(path,allow_pickle=False) as data:
                fields=['X','F_rsm','success','k','beta_id','combo_json','beta_json','eq_inf','sphere_violation','start','attempts','execution_order','accepted','solver_success','subproblem_status','t','attempt_log_json']
                np.savez_compressed(DST/'historical_m4_low_seed103.npz',**{k:data[k] for k in fields if k in data.files})
                (DST/'historical_m4_low_seed103.metadata.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
                manifest.append({'fixture':'historical_m4_low_seed103.npz','source':path.relative_to(SRC).as_posix(),'fields':fields})
    manifest.append({'fixture':name+'.json','source':'notebook 03 cell 4 lines 47-48; data/generated/'+scenario+'_scenario.npz','construction':'same CCD, Gaussian observations and OLS expressions; no truth callable enters package'})
(DST/'PROVENANCE.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
