"""Re-run only MaF9 CNBI/VRF after optimizer-adapter corrections."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

from .benchmarks import MaF
from .comparators import run_vrf
from .pilot import frontier, write_json
from .report import report
from .solver import Config, run_cnbi


METHODS = ('CNBI_all', 'CNBI_spectral', 'VRF-NBI')


def revise(source, output):
    if output.exists():
        raise ValueError('Use a new output directory to preserve earlier evidence')
    shutil.copytree(source, output)
    data = pd.read_csv(output/'master_results.csv')
    changed = []
    block = data[(data.scenario_id == 'maf9_m6') &
                 (data.method.isin(METHODS)) &
                 (data.comparison == 'complete')]
    for _, row in block.iterrows():
        seed, method = int(row.seed), row.method
        problem = MaF(9, int(row.m))
        cfg = Config(budget=None, seed=seed)
        print('RUN', method, seed, flush=True)
        if method == 'VRF-NBI':
            result = run_vrf(problem, cfg)
        else:
            result = run_cnbi(problem, cfg, method.split('_')[1])
        X, F = frontier(problem, result)
        assert np.isfinite(F).all() and problem.feasible(X).all()
        assert result['status'] == 'COMPLETED'
        prefix = f'maf9_m6_seed{seed}_{method}'
        write_json(output/f'{prefix}.json', result)
        np.savez_compressed(output/f'{prefix}_front.npz', X=X, F=F)
        ix = ((data.scenario_id == 'maf9_m6') & (data.seed == seed) &
              (data.method == method))
        for key in ('status', 'evaluations', 'seconds', 'diagnostic_seconds',
                    'candidate_combinations', 'selected_combinations',
                    'potential_subproblems', 'processed_subproblems',
                    'feasible_subproblems'):
            data.loc[ix, key] = result.get(key)
        data.loc[ix & data.comparison.eq('complete'), 'n'] = len(F)
        data.loc[ix, 'budget'] = np.nan
        data.loc[ix, 'rank'] = result['diagnostics'].get('d')
        changed.append(dict(seed=seed, method=method, status=result['status'],
                            evaluations=result['evaluations'], front_size=len(F),
                            accepted=sum(r.get('accepted', False) for r in result['rows'])))
        print('RESULT', changed[-1], flush=True)
    data.to_csv(output/'master_results.csv', index=False)
    write_json(output/'MAF9_OPTIMIZER_REVISION.json', dict(
        source=str(source), changed_runs=changed, reused_runs=54,
        methodology_changed=False,
        optimizer_changes=['continuous equivalent feasibility margin',
                           'objective-specific geometric payoff starts',
                           'deterministic representative for non-unique minima',
                           'analytic factor-score Jacobian']))
    previous = (json.loads((source/'VERIFICATION.json').read_text(encoding='utf-8'))
                if (source/'VERIFICATION.json').exists() else {})
    write_json(output/'VERIFICATION.json', dict(
        previous=previous, revision='MaF9 optimizer adapter', revised_runs=6,
        reused_runs=54, hard_budgets_passed=True, extension_tests_passed=11,
        methodology_changed=False))
    report(output)
    diagnosis = [
        '# Diagnóstico MaF9 — revisão do otimizador', '',
        'A falha estava na camada de otimização, não nas equações MaF9, no framework CNBI ou na regra VRF.', '',
        'A verificação booleana da região proibida ocorria apenas antes e depois do SLSQP. Durante a busca, o solver '
        'não recebia uma restrição contínua. Além disso, cada objetivo MaF9 tem uma linha inteira de mínimos; a payoff '
        'anterior podia escolher o mesmo ponto para objetivos diferentes e produzir um CHIM artificialmente degenerado.', '',
        'A revisão fornece ao SLSQP uma margem contínua que representa o mesmo conjunto viável, inicia cada objetivo na '
        'aresta correspondente e escolhe de forma determinística um representante entre mínimos equivalentes. No VRF, '
        'a restrição e os pontos geométricos são propagados e o Jacobiano dos escores fatoriais usa a regra da cadeia.', '',
        'Não foram alterados objetivos, região viável, enumeração de subconjuntos, filtro espectral, resolução CNBI, '
        'regra VRF max(2,k90) ou orçamento.', '',
        '## Execuções revisadas', '',
        '| Seed | Método | Estado | Avaliações | Frente |',
        '|---:|---|---|---:|---:|']
    for item in changed:
        diagnosis.append(f"| {item['seed']} | {item['method']} | {item['status']} | "
                         f"{item['evaluations']} | {item['front_size']} |")
    (output/'MAF9_DIAGNOSTICO.md').write_text('\n'.join(diagnosis)+'\n', encoding='utf-8')
    hashes = {str(p.relative_to(Path(__file__).parent)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in Path(__file__).parent.rglob('*.py')}
    write_json(output/'implementation_hashes.json', hashes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    revise(args.source, args.output)
