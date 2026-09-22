"""Build a candid Portuguese technical report from persisted pilot evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .pilot import write_json, metrics
from .analysis import analyze


ABLATION_SCENARIO = 'doe_nx2_m4_low'


def report(output):
    data = pd.read_csv(output/'master_results.csv')
    # Recalculate metrics from persisted fronts/references; no optimizer rerun.
    # Also permits auditing the analytical MaF13 normalization independently.
    for sid, group in data.groupby('scenario_id'):
        ref = np.load(output/f'{sid}_reference.npz')
        R, ideal, amp = ref['F'], ref['ideal'], ref['amplitude']
        if sid.startswith('maf13'):
            ideal = np.r_[np.zeros(3), np.full(R.shape[1]-3, 1/16)]
            amp = 1-ideal
            np.savez_compressed(output/f'{sid}_reference.npz', F=R, ideal=ideal, amplitude=amp)
        for seed, block in group.groupby('seed'):
            fronts = {}
            for _, row in block[block.comparison == 'complete'].iterrows():
                prefix = f'{sid}_seed{seed}_{row.method.replace("/", "_")}'
                F = np.load(output/f'{prefix}_front.npz')['F']
                Fn = (F-ideal)/amp
                fronts[row.method] = Fn
                result = json.loads((output/f'{prefix}.json').read_text(encoding='utf-8'))
                if row.method == 'VRF-NBI':
                    phases = result.setdefault('evaluation_phases', {})
                    phases['training'] = result['diagnostics']['training_evaluations']
                    phases['recomposition'] = len(result['rows'])
                    write_json(output/f'{prefix}.json', result)
                assert sum(result['evaluation_phases'].values()) == result['evaluations']
                idx = data.index[(data.scenario_id == sid) & (data.seed == seed) & (data.method == row.method)]
                potential = sum(r['potential_subproblems'] for r in result.get('combinations', []) if r['selected'])
                data.loc[idx, 'selected_potential_subproblems'] = potential if result.get('combinations') else np.nan
                data.loc[idx, 'selection_percent'] = (100*row.selected_combinations/row.candidate_combinations
                                                     if pd.notna(row.candidate_combinations) else np.nan)
                data.loc[idx, 'filter_relative_cost'] = result.get('diagnostic_seconds', 0)/max(result['seconds'], 1e-15)
                data.loc[idx, 'external_rsm_validation_evaluations'] = sum(r.get('accepted', False) for r in result['rows']) if sid.startswith('doe') else 0
                for key, value in metrics(Fn, (R-ideal)/amp, int(seed)).items():
                    data.loc[idx[data.loc[idx, 'comparison'] == 'complete'], key] = value
            target = min(map(len, fronts.values()))
            from .reuse import METRICS
            for method, F in fronts.items():
                Fe = (METRICS['hierarchical_equal_cardinality'](F, target) if len(F) > target else F) if target else F[:0]
                idx = data.index[(data.scenario_id == sid) & (data.seed == seed) &
                                 (data.method == method) & (data.comparison == 'equal_cardinality')]
                data.loc[idx, 'n'] = len(Fe)
                data.loc[idx, 'cardinality_status'] = 'PASS' if target else 'BLOCKED_EMPTY_METHOD'
                for key, value in metrics(Fe, (R-ideal)/amp, int(seed)).items():
                    data.loc[idx, key] = value
    data = data.drop(columns=['experimental_block'], errors='ignore')
    data['benchmark_family'] = np.where(data.scenario_id.str.startswith('doe'), 'synthetic', 'MaF')
    data.to_csv(output/'master_results.csv', index=False)
    # Study exports are deliberately separate. CNBI_spectral is the primary
    # CNBI method in DOE/MaF and is also the reference arm of the ablation.
    regular = data.method.ne('CNBI_all')
    data[data.benchmark_family.eq('synthetic') & regular].to_csv(
        output/'DOE_synthetic_results.csv', index=False)
    data[data.benchmark_family.eq('MaF') & regular].to_csv(
        output/'MaF_benchmarks_results.csv', index=False)
    data[(data.scenario_id == ABLATION_SCENARIO) &
         data.method.isin(['CNBI_all', 'CNBI_spectral'])].to_csv(
        output/'ablation_results.csv', index=False)
    analyze(output)
    complete = data[data.comparison == 'complete']
    doe_complete = complete[complete.benchmark_family == 'synthetic']
    maf_complete = complete[complete.benchmark_family == 'MaF']
    full_coverage = (doe_complete.scenario_id.nunique() == 27 and
                     doe_complete.groupby('scenario_id').seed.nunique().min() >= 10 and
                     maf_complete.scenario_id.nunique() == 13 and
                     maf_complete.groupby('scenario_id').seed.nunique().min() >= 10)
    seed_count = int(complete.seed.nunique())
    ablation_seed_count = int(complete[(complete.scenario_id == ABLATION_SCENARIO) &
                                       (complete.method == 'CNBI_all')].seed.nunique())
    status = json.loads((output/'pilot_status.json').read_text(encoding='utf-8'))
    reasons = []
    if ((complete.scenario_id == 'maf9_m6') & (complete.method == 'VRF-NBI') &
            complete.status.eq('NO_NONDEGENERATE_COMBINATIONS')).any():
        reasons.append('MaF9 VRF factor payoff produces a degenerate CHIM; no unique NBI normal exists')
    if (complete.n == 0).any():
        reasons.append('Empty method fronts prevent equal-cardinality comparison')
    if ((complete.method == 'CNBI_all') & complete.status.eq('BUDGET_EXHAUSTED')).any():
        reasons.append('CNBI_all exhaustiveness is not established where the common budget was exhausted')
    if not full_coverage:
        reasons.append('The 27-condition DOE and 13-setting MaF grid with ten seeds are not complete')
    status['full_campaign_ready'] = bool(full_coverage and not reasons)
    status['full_campaign_executed'] = bool(full_coverage)
    status['blocking_reasons'] = reasons
    status['all_cardinality_checks_passed'] = bool(data.loc[data.comparison == 'equal_cardinality', 'cardinality_status'].eq('PASS').all())
    write_json(output/'pilot_status.json', status)
    prep = json.loads((output/'preparation.json').read_text(encoding='utf-8'))
    ranks = pd.read_csv(output/'pa_sensitivity.csv')
    ea_limits = complete.loc[complete.method.isin(['NSGA-III', 'MOEA/D']), 'budget'].dropna()
    ea_budget_min = int(ea_limits.min()) if len(ea_limits) else 0
    ea_budget_max = int(ea_limits.max()) if len(ea_limits) else 0
    budget_text = (f'{ea_budget_min:,}'.replace(',', '.') if ea_budget_min == ea_budget_max else
                   f'{ea_budget_min:,}–{ea_budget_max:,}'.replace(',', '.'))
    state_line = ('**Estado: campanha experimental completa executada.**' if full_coverage else
                  '**Estado: implementação experimental e piloto executados; campanha completa não liberada.**')
    study_word = 'A campanha' if full_coverage else 'O piloto'
    lines = ['# Relatório técnico — extensão DOE, MaF e ablação CNBI', '',
             state_line, '',
             f'{study_word} preserva falhas metodológicas/operacionais reais; os resultados abaixo não demonstram superioridade de método. '
             'Foram preservados dados brutos e por seed, inclusive execuções vazias ou interrompidas.', '',
             '## 1. Arquivos e reaproveitamento', '',
             'Criados `cnbi_experiments/{benchmarks,parallel_analysis,doe,solver,comparators,reuse,pilot,analysis,report}.py`, '
             f'testes, documentação e referências com revisão/hash. Resultados desta revisão em `{output.as_posix()}/`. '
             'A pasta `experimental_results/pilot/` é preliminar e não integra as tabelas deste relatório. '
             'Nenhum arquivo do núcleo `cnbi/`, notebook, resultado histórico ou metadado de versão foi alterado.', '',
             'Reuso direto: base/jacobiana RSM 3D, PA_unc 3D, pesos/ordenação, Pareto/deduplicação. '
             'Métricas e Ward são as funções do notebook 04 carregadas por AST sem executar a campanha, com hash em `provenance.json`. '
             'Gerador, solver genérico e comparadores são adaptações explícitas; detalhes e diferenças em `cnbi_experiments/README.md`.', '',
             '## 2. Formulações MaF', '',
             'MaF8: distância euclidiana aos vértices. MaF9: distância às retas das arestas e exclusão dos polígonos refletidos. '
             'Ambos usam D=2 e caixa [-10000,10000]². MaF13 conserva D=5 e os conjuntos de índices publicados; n=D resolve a notação da equação 39. '
             'Os objetivos adicionais repetem f1²+f2¹⁰+f3¹⁰ mais a penalidade de ligação. Não é DTLZ7.', '',
             'Referência/PA MaF8/9: amostra uniforme no polígono. MaF13: octante esférico nas três primeiras coordenadas, '
             'invertido para o conjunto Pareto ligado. Na normalização externa MaF13, os objetivos adicionais têm ideal=1/16 e nadir=1. '
             'Não se interpreta a imagem completa como esfera M-dimensional.', '',
             '## 3. Evidência de validação', '',
             '[Cheng et al.](https://link.springer.com/article/10.1007/s40747-017-0039-7) e '
             '[PlatEMO oficial, revisão fixada](https://github.com/BIMK/PlatEMO/tree/d25e65d1ffba58dbf4d7e1b5259786187d12968a/PlatEMO/Problems/Multi-objective%20optimization/MaF). '
             'Arquivos MATLAB originais e hashes estão em `cnbi_experiments/references/`. '
             'Confronto das equações e testes numéricos independentes passaram; MATLAB/Octave não foi executado.', '',
             '11 testes da extensão passaram: regra VRF mínimo 2/90%, regressão MaF9 do payoff/VRF, derivadas analíticas, status de CHIM degenerado, '
             'valores analíticos/escalares, domínio, região proibida, suporte Pareto, '
             'Horn sequencial/reprodutível, derivadas/dimensões, orçamento e equivalência da payoff/PA 3D. '
             'Os 16 testes do núcleo original passaram. A reprodutibilidade determinística é verificada por seed nos testes '
             'e novamente na auditoria final dos artefatos.', '',
             '## 4. DOE', '',
             '**DOE é somente dos cenários sintéticos e não contém CNBI_all. MaF8/9/13 formam outro bloco.** '
             f'`CNBI_all` é executado somente em `{ABLATION_SCENARIO}` e aparece apenas em `ablation_results.csv`, ao lado de `CNBI_spectral`. '
             'As tabelas `DOE_synthetic_results.csv`, `MaF_benchmarks_results.csv` e `ablation_results.csv` '
             'materializam essa separação. A mesma execução CNBI_spectral é reutilizada, sem duplicar cálculo.', '',
             '`doe_design.csv`: 27 condições × 10 seeds = 270 linhas. nx={2,3,5}, delta={1,3,5}, '
             'dependência={0,25;0,60;0,85}, tolerância ±0,03. Geometria fixa por condição e observações RSM independentes por seed. '
             + ('Todas as condições e seeds foram calibradas e executadas.' if full_coverage else
                'O piloto usa seeds 101/102 em três condições; as demais foram planejadas, não calibradas/executadas.'), '',
             '| Condição | Alvo | Obtido |', '|---|---:|---:|']
    for p in prep:
        lines.append(f"| {p['scenario_id']} | {p.get('target', 0):.2f} | {p.get('achieved', 0):.6f} |")
    transition_done = (output/'transition_results.csv').exists()
    lines += ['', ('Transição executada: nx=3, M={3,4,5}, delta={−1,0,1}, dependência média. '
                   'NBI clássico foi executado apenas quando M≤nx+1.' if transition_done else
                  'Transição planejada: nx=3, M={3,4,5}, delta={−1,0,1}, dependência média. '
                   'Não executada nesta etapa. O adaptador rejeita NBI clássico quando M>nx+1.'), '',
              '## 5. Horn por permutação', '',
              'B=1.000, quantil linear 0,95, permutações independentes por coluna, parada sequencial na primeira falha. '
              'Foram salvos os espectros observados, todos os limiares e espectros nulos, amostras X/F e seeds. '
              f'{len(ranks)} diagnósticos de sensibilidade foram executados com N=250/500/1000/5000; '
              f'os postos completos estão em `pa_sensitivity.csv`.', '',
              'O posto alimenta uma janela na SVD da payoff; autovalores de correlação não são usados como limiares de valores singulares. '
              'RSM continua usando a PA_unc original em 3D e a extensão dimensional da mesma fórmula nos demais nx.', '',
              '## 6. Ablação', '',
              f'A ablação usa somente o cenário sintético `{ABLATION_SCENARIO}` (nx=2, M=4, dependência baixa), '
              'pois `CNBI_all` concluiu nas duas seeds. Nos demais cenários somente `CNBI_spectral` representa o CNBI.', '',
              '`all` enumera todos os subconjuntos admissíveis; degenerados são registrados sem inventar normal. '
              '`spectral` aplica o filtro e usa o mesmo solucionador. Sementes dos resgates são pareadas pelo índice canônico da combinação. '
              'A resolução experimental é Δ₂=0,20, Δ₃=0,20, Δ₄=0,20, Δ₅=0,50 e Δ₆=0,50. '
              'O cenário escolhido usa apenas k=2 e k=3, portanto 6 e 21 pesos por subconjunto. '
              'Δ₂, Δ₃ e Δ₆ são ajustes experimentais; `cnbi.config.DELTA_BY_K` permanece intacto. '
              'Não foi criada terceira variante com limiar arbitrário. Execuções truncadas não constituem ablação exaustiva.', '',
              '## 7. Orçamento', '',
              'CNBI e VRF-NBI executam até seu término natural, sem teto de avaliações. '
              f'Para NSGA-III e MOEA/D, o limite observado é {budget_text} avaliações por caso/seed; a regra padrão garante '
              'pelo menos 50.000 avaliações e 400 gerações completas. Custo de referências e sensibilidade externa separado. '
              'Gradientes analíticos, tempo e tempo de diagnóstico registrados. '
              'Maxiter=100 e até dois resgates no piloto, limites explicitamente menores que os padrões 500/8 do núcleo.', '',
              'EAs usam configuração base anterior, sem alegação de tuning dos novos M. Cardinalidade usa o mínimo dos métodos presentes '
              'por cenário/seed e Ward do notebook 04; um método vazio bloqueia a comparação, sem exclusão silenciosa.', '',
              '## 8. Resultados do piloto', '',
              f'{len(complete)} execuções em {complete.scenario_id.nunique()} casos e {complete.seed.nunique()} seeds; '
              f'{len(data)} linhas incluindo cardinalidade equalizada.', '',
              f'| Caso | Método | Avaliações mín–máx | N não dominados mín–máx | IGD mediana completa (seeds válidas/{seed_count}) |',
              '|---|---|---:|---:|---:|']
    for (sid, method), group in complete.groupby(['scenario_id', 'method'], sort=False):
        igd = group.IGD.median() if group.IGD.notna().any() else np.nan
        label = (f'{igd:.6g} ({int(group.IGD.notna().sum())}/{seed_count})'
                 if np.isfinite(igd) else f'indisponível (0/{seed_count})')
        lines.append(f'| {sid} | {method} | {int(group.evaluations.min())}–{int(group.evaluations.max())} | '
                     f'{int(group.n.min())}–{int(group.n.max())} | {label} |')
    lines += ['', 'As medianas acima usam somente as seeds disponíveis, identificadas na última coluna. '
              'Há frentes vazias e truncamento; não interpretar esses números como ranking científico. '
              '`master_results.csv` preserva IGD/HV/GD/Spacing/Sparsity, seeds, contagens e tempos. '
              '`paired_ablation.csv` contém diferenças e ganhos relativos pareados; oito figuras estão em `figures/`.', '',
              '| Caso/seed | Combinações removidas | Variação avaliações | Variação IGD | Variação HV |',
              '|---|---:|---:|---:|---:|']
    paired = pd.read_csv(output/'paired_ablation.csv')
    for _, r in paired[(paired.comparison == 'complete') & paired.IGD_relative_change.notna()].iterrows():
        lines.append(f'| {r.scenario_id}/{r.seed} | {100*r.combinations_removed_fraction:.1f}% | '
                     f'{100*r.evaluations_relative_change:+.1f}% | {100*r.IGD_relative_change:+.1f}% | {100*r.HV_relative_change:+.1f}% |')
    lines += ['', 'Variações = (spectral−all)/all. IGD menor e HV maior são melhores. '
              'Os números descrevem o teto piloto; redução de avaliações em braços truncados não mede o custo exaustivo eliminado. '
              'Ausência de par válido não é substituída por zero.', '',
              '## 9. Problemas encontrados e alternativas', '',
              '1. VRF atualizado por solicitação do usuário: k=max(2,k90), mantendo pelo menos 90% de variância acumulada. '
              'A quantidade escolhida e a retenção real estão nos diagnósticos. O limite dimensional continua sendo verificado.',
              '2. MaF13: as derivadas analíticas e os pontos iniciais geométricos reduziram a payoff para cerca de 2.300 avaliações. '
              'Com teto comum de 50.000, CNBI_spectral completou as seeds executadas e produziu frentes não vazias.',
              '3. MaF9 CNBI: a falha estava na adaptação numérica do otimizador. As restrições eram verificadas somente depois '
              'da otimização e a payoff escolhia o mesmo representante para mínimos não únicos. Uma margem contínua equivalente '
              'à região viável, pontos iniciais por aresta e desempate determinístico produziram seis representantes distintos. '
              'CNBI_spectral passou a concluir bem abaixo do teto, sem alterar equações, filtro ou enumeração CNBI.',
              '4. MaF9 VRF: o colapso anterior dos fatores também era numérico. Ao propagar a mesma restrição, usar pontos iniciais '
              'geométricos e aplicar a regra da cadeia ao Jacobiano dos escores, a payoff fatorial tornou-se não degenerada e '
              'as seeds executadas concluíram. Permanecem três fatores, pois dois retêm apenas cerca de 75%.',
              f'5. CNBI_all: foi limitado à ablação em `{ABLATION_SCENARIO}`. As {ablation_seed_count} seeds concluíram a enumeração, '
              'permitindo comparar o filtro com uma referência all não truncada.',
              '6. Cardinalidade: comparar frentes com o mesmo número de soluções só funciona quando todos os métodos '
              'devolvem alguma solução. Uma frente vazia impede essa comparação nesse benchmark/seed. '
              + ('A ANOVA usa somente os 27 cenários sintéticos com blocos por seed.' if full_coverage else
                 'Separadamente, a ANOVA é somente dos sintéticos: foram executadas três das 27 condições, insuficientes '
                 'para separar estatisticamente os efeitos de nx, delta e dependência.'),
              '7. A normalização MaF13 foi conferida analiticamente no pós-processamento: ideal adicional=1/16. '
              'É apenas a escala comum usada para calcular as métricas, não uma falha do benchmark. '
              'Nenhum objetivo de otimização foi alterado para esse ajuste externo.', '',
              'Na revisão VRF, a biblioteca também emitiu avisos de matriz singular no cálculo dos pesos dos scores '
              'e utilizou seu fallback para cargas fatoriais. Isso merece diagnóstico antes de interpretar cientificamente '
              'esses casos; não foi criada uma nova regra de regularização.', '',
              '## 10. Custo da campanha e estado final', '']
    total = complete.seconds.sum()
    ranges = complete.groupby('method').seconds.agg(['min', 'max', 'median'])
    # Four regular methods cover 270 DOE + 130 MaF instances; CNBI_all covers
    # only the ten seeds of the single selected synthetic ablation scenario.
    projected_runs = pd.Series({method: (10 if method == 'CNBI_all' else 400)
                                for method in ranges.index})
    lo = (ranges['min']*projected_runs).sum()/3600
    hi = (ranges['max']*projected_runs).sum()/3600
    mid = (ranges['median']*projected_runs).sum()/3600
    lines += [f'Tempo somado dos métodos nesta {"campanha" if full_coverage else "etapa"}: {total:.1f} s '
              '(não inclui preparação, PA de sensibilidade, métricas e gráficos). '
              f'Os EAs usam limites de {budget_text} avaliações; CNBI e VRF-NBI têm custo determinado pelo término natural '
              'de cada execução, por isso não existe um máximo global pré-fixado para a campanha.', '',
              f'Extrapolação operacional grosseira dos tempos observados por método: {mid:.2f} h; '
              f'envelope mín–máx observado {lo:.2f}–{hi:.2f} h. Não é intervalo de confiança nem estimativa de campanha exaustiva: '
              'não cobre novos M, calibração de 27 geometrias, tuning, pós-processamento ou maiores tetos necessários. '
              'O custo científico completo permanece indeterminado até resolver os bloqueios.', '',
              ('**Campanha completa executada.** `campaign_status.json` registra a cobertura final.' if full_coverage else
                 '**Campanha completa não executada.** `pilot_status.json` registra `full_campaign_ready=false`. '
                 'Esta entrega cobre a infraestrutura e o relatório do piloto; não declara cumpridas comparações MaF válidas, '
                 'transição executada, calibração de todos os cenários ou análise estatística da campanha completa.'), '']
    (output/'RELATORIO_TECNICO.md').write_text('\n'.join(lines), encoding='utf-8')
    write_json(output/'implementation_hashes.json', {str(p.relative_to(Path(__file__).parent)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in Path(__file__).parent.rglob('*.py')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('output', type=Path)
    report(parser.parse_args().output)
