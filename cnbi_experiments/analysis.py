"""Seed-preserving pilot plots; inference only for a complete replicated DOE."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def paired_ablation(data):
    keys = ['scenario_id', 'seed', 'comparison']
    a = data[data.method == 'CNBI_all']
    b = data[data.method == 'CNBI_spectral']
    out = a.merge(b, on=keys, suffixes=('_all', '_spectral'), validate='one_to_one')
    for metric in ('IGD', 'HV', 'seconds', 'evaluations'):
        out[f'{metric}_difference_spectral_minus_all'] = out[f'{metric}_spectral']-out[f'{metric}_all']
        denominator = out[f'{metric}_all'].replace(0, np.nan)
        out[f'{metric}_relative_change'] = out[f'{metric}_difference_spectral_minus_all']/denominator
    out['combinations_removed_fraction'] = 1-out.selected_combinations_spectral/out.candidate_combinations_all
    out['feasibility_all'] = out.feasible_subproblems_all/out.processed_subproblems_all.replace(0, np.nan)
    out['feasibility_spectral'] = out.feasible_subproblems_spectral/out.processed_subproblems_spectral.replace(0, np.nan)
    return out


def inference(data, output):
    """Do not fit interactions to three pilot conditions or pseudo-replicates.

    Full DOE: seed fixed blocks, scenario-cluster robust coefficient intervals;
    two-way factorial effects. Paired contrasts retain scenario and seed.
    """
    import statsmodels.formula.api as smf
    d = data[(data.comparison == 'equal_cardinality') & data.scenario_id.str.startswith('doe')]
    d = d[d.method == 'CNBI_spectral'].copy()
    if d.scenario_id.nunique() != 27 or d.groupby('scenario_id').seed.nunique().min() < 2:
        (output/'inference_status.txt').write_text(
            'Não estimado: o piloto não contém as 27 condições replicadas. '
            'ANOVA/interações e intervalos populacionais seriam inadequados.\n', encoding='utf-8')
        return
    terms = '(C(nx)+C(delta)+C(dependence_level))**2 + C(seed)'
    for response in ('IGD', 'HV'):
        (output/f'{response}_factorial_effects.csv').unlink(missing_ok=True)
    missing_by_response = {}
    for response in ('IGD', 'HV'):
        fit_data = d.dropna(subset=[response])
        observed = set(zip(fit_data.scenario_id, fit_data.seed.astype(int)))
        expected = set(zip(d.scenario_id, d.seed.astype(int)))
        missing_by_response[response] = sorted(expected - observed)
    if any(missing_by_response.values()):
        details = '; '.join(
            f'{response}: ' + ', '.join(f'{scenario}/seed{seed}' for scenario, seed in missing)
            for response, missing in missing_by_response.items() if missing)
        (output/'inference_status.txt').write_text(
            'Não estimado: existem respostas fatoriais ausentes após frentes vazias. '
            'Nenhum modelo por casos completos foi ajustado, para preservar o DOE balanceado. '
            f'Ausências: {details}.\n', encoding='utf-8')
        return
    for response in ('IGD', 'HV'):
        fit_data = d.dropna(subset=[response])
        model = smf.ols(f'{response} ~ {terms}', fit_data).fit(
            cov_type='cluster', cov_kwds={'groups': fit_data.scenario_id}, use_t=True)
        ci = model.conf_int()
        pd.DataFrame(dict(coefficient=model.params, ci_low=ci[0], ci_high=ci[1],
                          p=model.pvalues, standardized_effect=model.params/fit_data[response].std(ddof=1))).to_csv(
            output/f'{response}_factorial_effects.csv')
    (output/'inference_status.txt').write_text(
        'Estimado: DOE sintético completo e balanceado, com 27 condições e 10 sementes.\n',
        encoding='utf-8')


def analyze(output):
    data = pd.read_csv(output/'master_results.csv')
    paired = paired_ablation(data)
    paired.to_csv(output/'paired_ablation.csv', index=False)
    inference(data, output)
    figures = output/'figures'; figures.mkdir(exist_ok=True)
    colors = {'CNBI_all': '#737373', 'CNBI_spectral': '#0072B2', 'VRF-NBI': '#D55E00',
              'NSGA-III': '#009E73', 'MOEA/D': '#CC79A7'}
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    complete = data[data.comparison == 'complete']
    def scatter(frame, x, y, name, xlabel, ylabel):
        fig, ax = plt.subplots(figsize=(8, 5), layout='constrained')
        for method, group in frame.groupby('method', sort=False):
            ax.scatter(group[x], group[y], label=method, color=colors.get(method), alpha=.75, s=45)
        ax.set(xlabel=xlabel, ylabel=ylabel, title='Piloto — pontos individuais por seed')
        ax.legend(fontsize=8); ax.grid(alpha=.15)
        fig.savefig(figures/f'{name}.png', dpi=180); plt.close(fig)
    doe = complete[complete.scenario_id.str.startswith('doe') & complete.method.ne('CNBI_all')]
    scatter(doe, 'delta', 'IGD', '01_igd_delta', 'Excesso dimensional δ', 'IGD (frente completa)')
    scatter(doe, 'dependence_obtained', 'IGD', '02_igd_dependence', 'Dependência obtida', 'IGD')
    # Pilot nx, delta and dependence are confounded: no invented interaction surface.
    fig, ax = plt.subplots(figsize=(8, 5), layout='constrained')
    design = pd.read_csv(output/'doe_design.csv').drop_duplicates('scenario_id')
    for nx, group in design.groupby('nx'):
        ax.scatter(group.delta+(nx-3)*.035, group.target, label=f'nx={nx}', s=50)
    ax.set(xlabel='δ', ylabel='Dependência alvo', title='03 — desenho fatorial; interação ainda não estimada')
    ax.legend(); fig.savefig(figures/'03_interaction_design.png', dpi=180); plt.close(fig)
    scatter(complete[complete.method == 'CNBI_spectral'], 'm', 'rank', '04_rank_m', 'M', 'Posto estimado')
    fig, ax = plt.subplots(figsize=(8, 5), layout='constrained')
    pa = paired[paired.comparison == 'complete']
    ax.scatter(100*pa.combinations_removed_fraction, pa.IGD_difference_spectral_minus_all, s=50)
    ax.axhline(0, color='gray', linewidth=.8)
    ax.set(xlabel='Combinações removidas (%)', ylabel='IGD spectral − all', title='05 — ablação pareada por seed')
    fig.savefig(figures/'05_filter_quality.png', dpi=180); plt.close(fig)
    scatter(complete[complete.method.str.startswith('CNBI')], 'delta', 'seconds', '06_cost', 'δ', 'Tempo total (s)')
    scatter(complete[complete.scenario_id.str.startswith('maf') & complete.method.ne('CNBI_all')],
            'm', 'IGD', '07_maf_pilot', 'M (um caso por MaF no piloto)', 'IGD')
    fig, axes = plt.subplots(1, 2, figsize=(12, 7))
    for _, row in pa.iterrows():
        for ax, metric in zip(axes, ('IGD', 'HV')):
            ax.plot([0, 1], [row[f'{metric}_all'], row[f'{metric}_spectral']], marker='o', alpha=.65,
                    label=f'{row.scenario_id}, seed {row.seed}')
            ax.set(xticks=[0, 1], xticklabels=['all', 'spectral'], ylabel=metric,
                   title=f'{metric} por cenário/seed')
            ax.grid(alpha=.15)
    axes[0].set_yscale('log')
    axes[0].set_ylabel('IGD (escala logarítmica)')
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=3, fontsize=8, frameon=False)
    fig.suptitle('Ablação do piloto — lacunas indicam frente indisponível; há execuções truncadas', fontsize=11)
    fig.subplots_adjust(bottom=.27, top=.89, wspace=.3)
    fig.savefig(figures/'08_ablation.png', dpi=180); plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    analyze(parser.parse_args().output)
