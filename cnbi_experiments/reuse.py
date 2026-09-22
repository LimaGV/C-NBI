"""Load ONLY named function definitions; never execute notebook campaign cells."""
import ast
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.stats import qmc

ROOT = Path(__file__).resolve().parents[1]


def notebook_functions(filename, names, namespace=None):
    path = ROOT/'CNBI-Synthetic-Benchmarks'/'notebooks'/filename
    nb = json.loads(path.read_text(encoding='utf-8'))
    found = {}
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            for node in ast.parse(''.join(cell['source'])).body:
                if isinstance(node, ast.FunctionDef) and node.name in names:
                    found[node.name] = node
    if set(found) != set(names):
        raise ValueError(f'Missing definitions: {set(names)-set(found)}')
    env = dict(np=np, cKDTree=cKDTree, qmc=qmc, **(namespace or {}))
    for node in found.values():
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), env)
    return {name: env[name] for name in names}, dict(path=str(path.relative_to(ROOT)),
             sha256=hashlib.sha256(path.read_bytes()).hexdigest(), functions=sorted(names))


METRICS, METRICS_PROVENANCE = notebook_functions('04_analise_resultados.ipynb',
    ['nearest', 'GD', 'IGD', 'spacing', 'sparsity', 'hv_qmc', 'hierarchical_equal_cardinality'])
