"""One-off conservative extraction from the user-selected working notebook.

Audit/build helper, outside the candidate distribution. No original is modified.
"""
from pathlib import Path
import ast
import collections
import csv
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'CNBI-Synthetic-Benchmarks'
DEST = ROOT / 'CNBI_v1.0'
sys.stdout.reconfigure(encoding='utf-8')


def write(path, text):
    path = DEST / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


nbpath = 'notebooks/03_pipeline_CNBI_comparacoes.ipynb'
nb = json.loads((SOURCE / nbpath).read_text(encoding='utf-8'))
source = ''.join(nb['cells'][1]['source'])
tree = ast.parse(source)
groups = {
    'rsm': ('import numpy as np', ['z', 'dz']),
    'payoff': ('import numpy as np\nfrom scipy.optimize import minimize\nfrom .config import ALPHA\nfrom .rsm import z, dz', ['individual_payoff']),
    'spectral': ('import numpy as np\nfrom .rsm import z', ['parallel_analysis']),
    'combinations': ('import numpy as np\nfrom itertools import product', ['simplex_weights', '_nearest_weight_order']),
    'nbi': ('import numpy as np\nfrom scipy.linalg import null_space\nfrom scipy.optimize import minimize\nfrom .config import ALPHA\nfrom .rsm import z, dz\nfrom .combinations import simplex_weights, _nearest_weight_order', ['_solve_nbi_base']),
    'core': ('import numpy as np\nfrom itertools import combinations\nfrom .config import DELTA_BY_K\nfrom .spectral import parallel_analysis\nfrom .nbi import _solve_nbi_base', ['cnbi']),
}
docs = {
    'z': 'Vetor RSM de três fatores, dez termos na ordem original. Entrada x (3,); saída (10,). Sem tolerância ou iteração. Ver TRACEABILITY.md.',
    'dz': 'Jacobiana analítica dos dez termos RSM. Entrada x (3,); saída (10,3). Mesma ordem de z; sem tolerância ou iteração.',
    'individual_payoff': 'Ótimos individuais e payoff pública de B (10,m), já em minimização. Retorna Xstar (m,3), P (m,m), objetivos nas linhas. SLSQP: sete starts, ftol=1e-11, maxiter=500; aceita sucesso e esfera até 1e-7. Contadores históricos em atributos da função; uso sequencial.',
    'parallel_analysis': 'Diagnóstico global legado independente. P (m,m), Xstar (m,3), mse (m,), XtX_inv (10,10); retorna d,s,p95,floor,ceiling,scaled. h=zᵀXtX_inv z; ruído sqrt(h*MSE)/amplitude; SVD das diferenças de linhas. Padrões nmc=2000, seed=777; p95, piso sigma[d], teto sigma[0]/sigma[d-1]. Amplitude <=1e-12 vira 1; d>=1. Ver TRACEABILITY.md para hipóteses.',
    'simplex_weights': 'Malha simplex original: product(range(p+1), repeat=k), soma p, dividida por p=round(1/delta). Retorna pesos na ordem lexicográfica original. Usar deltas normativos; a função original não valida divisibilidade.',
    '_nearest_weight_order': 'Ordena pesos por vizinho mais próximo a partir do índice zero; empate pelo índice. Retorna pares (índice original, beta). Entrada não vazia, sem aleatoriedade ou tolerância explícita.',
    '_solve_nbi_base': 'Solver NBI original do notebook 03, preservado. Bmodel (10,k), output_B (10,m), indices (k,), Xstar (k,3), P (k,k), delta e combo_id. Retorna linhas recompostas, contador full e grad. Minimiza -t com F_local(x)=beta@A+t*normal e esfera; normal null_space(E), orientada à origem. SLSQP ftol=1e-10/maxiter=500; igualdade <=1e-5, esfera <=1e-8, t em [-10,10]; vértices exatos, warm starts e oito resgates. Não reescala pela payoff global. Fórmulas, exceções e sementes em TRACEABILITY.md/PARAMETERS.md.',
    'cnbi': 'Núcleo combinatório original. B (10,m), P (m,m), Xstar (m,3), mse (m,), XtX_inv (10,10), todos no sentido de minimização. Retorna candidatos brutos recompostos e análise paralela com contadores. k=2..min(m,4); sigma_min>floor e quality<=ceiling; deltas normativos; IDs de resgate base zero só nas combinações aceitas. Sem deduplicação ou Pareto. Preserva falhas identificadas nas linhas retornadas.',
}
functions = {}
duplicate = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        if node.name in functions:
            duplicate.append({'function': node.name, 'identical_ast': ast.dump(node, include_attributes=False) == ast.dump(functions[node.name], include_attributes=False), 'lines': [functions[node.name].lineno, node.lineno]})
        functions[node.name] = node
manifest = []
baseline = ['# Excertos ORIGINAIS, sem reformatação; somente definições e constantes.\n# Fonte: '+nbpath+', célula 2 (base 1). Não é núcleo de produção.\nimport numpy as np\nfrom scipy.optimize import minimize\nfrom scipy.linalg import null_space\nfrom itertools import combinations, product\nALPHA=2**0.75; DELTA_BY_K={2:.10,3:.10,4:.20,5:.50}\n']
for module, (imports, names) in groups.items():
    parts = ['"""Extração conservadora do notebook 03. Ver TRACEABILITY.md e aviso MIT."""', imports]
    for name in names:
        node = functions[name]
        original = ast.get_source_segment(source, node)
        baseline.append(original)
        manifest.append({'module': f'cnbi/{module}.py', 'function': name, 'source': nbpath, 'cell_1based': 2, 'line_1based': node.lineno, 'end_line': node.end_lineno})
        new = ast.parse(original).body[0]
        if ast.get_docstring(new) is not None:
            new.body.pop(0)
        new.body.insert(0, ast.Expr(value=ast.Constant(value=docs[name])))
        parts.append(ast.unparse(ast.fix_missing_locations(new)))
    write(f'cnbi/{module}.py', '\n\n\n'.join(parts)+'\n')
write('cnbi/config.py', '''"""Constantes normativas copiadas do notebook 03, célula 2.

Demais literais do solver estão inventariados em PARAMETERS.md, preservados
nos corpos das funções para evitar alterar o comportamento experimental.
"""
ALPHA = 2**0.75
DELTA_BY_K = {2: .10, 3: .10, 4: .20, 5: .50}
PROFILE = "synthetic-notebook03-working-copy"
''')
write('tests/fixtures/original_core.py.txt', '\n\n'.join(baseline)+'\n')
write('provenance/EXTRACTION.json', json.dumps({'functions': manifest, 'duplicates': duplicate, 'final_release_hash': None}, indent=2, ensure_ascii=False)+'\n')
nb4 = json.loads((SOURCE/'notebooks/04_analise_resultados.ipynb').read_text(encoding='utf-8'))
s4 = ''.join(nb4['cells'][5]['source'])
n4 = next(n for n in ast.parse(s4).body if isinstance(n, ast.FunctionDef) and n.name == 'nondominated')
write('tests/fixtures/original_nondominated.py.txt', '# Origem: notebook 04, célula 6; critério original aplicado a ground truth.\nimport numpy as np\n\n'+ast.get_source_segment(s4, n4)+'\n')
# Preserve the existing license notice without creating an institutional grant.
shutil.copyfile(SOURCE/'LICENSE', DEST/'ORIGINAL_LICENSE.txt')

# Inventory every project file outside Git, environments and bundled node packages.
inventory = []
analysis = []
for p in sorted(ROOT.rglob('*')):
    rel = p.relative_to(ROOT)
    if not p.is_file() or rel.parts[0] not in ('CNBI-Synthetic-Benchmarks','docx_qa'):
        continue
    if any(x in rel.parts for x in ('.git','.venv','node_modules','__pycache__')):
        continue
    inventory.append({'path': rel.as_posix(), 'bytes': p.stat().st_size, 'suffix': p.suffix})
    if p.suffix not in ('.py','.ipynb'): continue
    text = p.read_text(encoding='utf-8-sig')
    cells = json.loads(text)['cells'] if p.suffix=='.ipynb' else [{'cell_type':'code','source':text}]
    for ci,cell in enumerate(cells,1):
        if cell['cell_type']!='code': continue
        s = ''.join(cell['source'])
        try: t = ast.parse(s)
        except SyntaxError as exc:
            analysis.append({'path': rel.as_posix(),'cell':ci,'syntax_error':str(exc)}); continue
        imports=[]; constants=[]; symbols=[]; literals=[]
        for node in ast.walk(t):
            if isinstance(node, ast.Import): imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom): imports.append(node.module)
            elif isinstance(node, (ast.FunctionDef,ast.ClassDef)): symbols.append({'name':node.name,'line':node.lineno})
            elif isinstance(node, ast.Constant) and isinstance(node.value,(int,float,str)):
                v=node.value
                if isinstance(v,(int,float)) or (isinstance(v,str) and ('seed' in v.lower() or ':\\' in v or '/home/' in v)):
                    literals.append({'line':node.lineno,'value':v})
        for node in t.body:
            if isinstance(node,(ast.Assign,ast.AnnAssign)):
                constants.append({'line':node.lineno,'source':ast.get_source_segment(s,node)})
        analysis.append({'path':rel.as_posix(),'cell':ci,'imports':imports,'symbols':symbols,'assignments':constants,'literals':literals})
write('provenance/PROJECT_INVENTORY.json',json.dumps(inventory,indent=2,ensure_ascii=False)+'\n')
write('provenance/STATIC_ANALYSIS.json',json.dumps(analysis,indent=2,ensure_ascii=False)+'\n')
print('Extração concluída:',len(manifest),'funções;',len(inventory),'arquivos inventariados; duplicação:',duplicate)
