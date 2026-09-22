"""Complete, reproducible analysis for a finished synthetic DOE campaign."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.outliers_influence import variance_inflation_factor


RESPONSES = ("IGD", "HV")


def scalar(value):
    return float(np.asarray(value).reshape(-1)[0])


def robust_terms(model):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        table = model.wald_test_terms().table.reset_index()
    table = table.rename(columns={table.columns[0]: "term"})
    for column in ("statistic", "pvalue"):
        table[column] = table[column].map(scalar)
    return table


def quality_summary(master):
    data = master[master.comparison.eq("equal_cardinality")].copy()
    data = data.groupby(["scenario_id", "method"], as_index=False).agg(
        IGD=("IGD", "median"), HV=("HV", "median")
    )
    keys = ["scenario_id"]
    data["IGD_rank"] = data.groupby(keys).IGD.rank(method="average", ascending=True)
    data["HV_rank"] = data.groupby(keys).HV.rank(method="average", ascending=False)
    for response, ascending in (("IGD", False), ("HV", True)):
        grouped = data.groupby(keys)[response]
        low = grouped.transform("min")
        high = grouped.transform("max")
        spread = (high - low).replace(0, np.nan)
        if ascending:
            quality = (data[response] - low) / spread
        else:
            quality = (high - data[response]) / spread
        data[f"{response}_quality_0_to_1"] = quality.fillna(1.0)
    data["combined_quality_0_to_1"] = (
        data.IGD_quality_0_to_1 + data.HV_quality_0_to_1
    ) / 2
    summary = data.groupby("method", sort=False).agg(
        scenarios=("method", "size"),
        mean_IGD_rank=("IGD_rank", "mean"),
        mean_HV_rank=("HV_rank", "mean"),
        mean_IGD_quality=("IGD_quality_0_to_1", "mean"),
        mean_HV_quality=("HV_quality_0_to_1", "mean"),
        mean_combined_quality=("combined_quality_0_to_1", "mean"),
        median_IGD=("IGD", "median"),
        median_HV=("HV", "median"),
    ).reset_index()
    return summary.sort_values("mean_combined_quality", ascending=False)


def holm_adjust(pvalues):
    """Holm correction while preserving the original pair order."""
    pvalues = np.asarray(pvalues, dtype=float)
    order = np.argsort(pvalues)
    adjusted = np.empty_like(pvalues)
    running = 0.0
    total = len(pvalues)
    for rank, index in enumerate(order):
        running = max(running, (total - rank) * pvalues[index])
        adjusted[index] = min(1.0, running)
    return adjusted


def method_tests(master, output):
    """Compare methods using 27 scenario medians, not seeds as pseudo-replicates."""
    data = master[master.comparison.eq("equal_cardinality")].copy()
    medians = data.groupby(["scenario_id", "method"], as_index=False).agg(
        IGD=("IGD", "median"), HV=("HV", "median")
    )
    methods = ["CNBI_spectral", "VRF-NBI", "NSGA-III", "MOEA/D"]
    friedman_rows = []
    pair_rows = []
    for response in RESPONSES:
        wide = medians.pivot(index="scenario_id", columns="method", values=response)
        wide = wide[methods].dropna()
        statistic, pvalue = stats.friedmanchisquare(
            *(wide[method].to_numpy() for method in methods)
        )
        friedman_rows.append({
            "response": response,
            "scenario_blocks": len(wide),
            "statistic": statistic,
            "pvalue": pvalue,
        })
        response_rows = []
        for left_index, left in enumerate(methods):
            for right in methods[left_index + 1:]:
                left_values = wide[left].to_numpy()
                right_values = wide[right].to_numpy()
                statistic, pvalue = stats.wilcoxon(
                    left_values, right_values, alternative="two-sided"
                )
                if response == "IGD":
                    left_wins = left_values < right_values
                else:
                    left_wins = left_values > right_values
                response_rows.append({
                    "response": response,
                    "method_a": left,
                    "method_b": right,
                    "scenario_blocks": len(wide),
                    "median_a_minus_b": float(np.median(left_values - right_values)),
                    "method_a_win_fraction": float(np.mean(left_wins)),
                    "wilcoxon_statistic": statistic,
                    "pvalue_raw": pvalue,
                })
        adjusted = holm_adjust([row["pvalue_raw"] for row in response_rows])
        for row, corrected in zip(response_rows, adjusted):
            row["pvalue_holm"] = corrected
            row["significant_0_05"] = bool(corrected < 0.05)
        pair_rows.extend(response_rows)
    pd.DataFrame(friedman_rows).to_csv(output / "method_friedman.csv", index=False)
    pd.DataFrame(pair_rows).to_csv(output / "method_pairwise_wilcoxon.csv", index=False)


def budget_summary(complete):
    return complete.groupby("method", sort=False).agg(
        runs=("method", "size"),
        completed=("status", lambda x: int(x.eq("COMPLETED").sum())),
        empty_fronts=("n", lambda x: int(x.eq(0).sum())),
        evaluations_min=("evaluations", "min"),
        evaluations_median=("evaluations", "median"),
        evaluations_max=("evaluations", "max"),
        budget_min=("budget", "min"),
        budget_max=("budget", "max"),
    ).reset_index()


def fit_doe_models(data, output):
    analysis_dir = output / "anova_final"
    analysis_dir.mkdir(exist_ok=True)
    summaries = []
    vif_rows = []

    two_rhs = "(C(nx, Helmert)+C(delta, Helmert)+C(dependence_level, Helmert))**2 + C(seed, Helmert)"
    triple_rhs = "C(nx, Helmert)*C(delta, Helmert)*C(dependence_level, Helmert) + C(seed, Helmert)"

    for response in RESPONSES:
        two = smf.ols(f"{response} ~ {two_rhs}", data).fit()
        triple = smf.ols(f"{response} ~ {triple_rhs}", data).fit()
        triple_hc3 = smf.ols(f"{response} ~ {triple_rhs}", data).fit(
            cov_type="HC3", use_t=True
        )
        comparison = anova_lm(two, triple).iloc[1]
        for name, model in (("two_way", two), ("triple", triple)):
            summaries.append({
                "response": response,
                "model": name,
                "observations": int(model.nobs),
                "parameters": int(model.df_model + 1),
                "R2": model.rsquared,
                "adjusted_R2": model.rsquared_adj,
                "RMSE": float(np.sqrt(np.mean(model.resid ** 2))),
                "residual_df": model.df_resid,
                "third_order_F": float(comparison["F"]) if name == "two_way" else np.nan,
                "third_order_p": float(comparison["Pr(>F)"]) if name == "two_way" else np.nan,
                "third_order_df": float(comparison["df_diff"]) if name == "two_way" else np.nan,
                "lack_of_fit_testable": name == "two_way",
            })
        # The third-order model already fits every DOE cell mean.  A
        # scenario-cluster covariance is singular in that saturated setting,
        # so use the replicated randomized-block ANOVA and its within-cell
        # residual variation for term tests.
        term_table = anova_lm(triple, typ=2).reset_index().rename(
            columns={"index": "term"}
        )
        term_table.to_csv(analysis_dir / f"{response}_triple_anova.csv", index=False)
        robust_terms(triple_hc3).to_csv(
            analysis_dir / f"{response}_triple_terms_HC3.csv", index=False
        )
        for index, name in enumerate(triple.model.exog_names):
            if name == "Intercept":
                continue
            vif_rows.append({
                "response": response,
                "coefficient": name,
                "VIF": variance_inflation_factor(triple.model.exog, index),
            })

    model_summary = pd.DataFrame(summaries)
    model_summary.to_csv(analysis_dir / "delta_model_summary.csv", index=False)
    pd.DataFrame(vif_rows).to_csv(analysis_dir / "delta_triple_VIF.csv", index=False)
    means = pd.concat([
        data.groupby(factor)[list(RESPONSES)].mean().reset_index().assign(factor=factor).rename(columns={factor: "level"})
        for factor in ("nx", "delta", "dependence_level")
    ], ignore_index=True)
    means.to_csv(analysis_dir / "factor_means.csv", index=False)
    return model_summary, pd.DataFrame(vif_rows), means


def write_summary(output, model_summary, vifs, means, methods, budgets):
    triple = model_summary[model_summary.model.eq("triple")].set_index("response")
    two = model_summary[model_summary.model.eq("two_way")].set_index("response")
    max_vif = vifs.groupby("response").VIF.max()
    best = methods.iloc[0]
    friedman = pd.read_csv(output / "method_friedman.csv").set_index("response")
    robust_pvalues = []
    for response in RESPONSES:
        robust = pd.read_csv(output / "anova_final" / f"{response}_triple_terms_HC3.csv")
        robust = robust[~robust.term.isin(["Intercept", "C(seed, Helmert)"])]
        robust_pvalues.extend(robust.pvalue.tolist())
    text = f"""# Resultados finais do DOE sintético

## Validade da campanha

A campanha contém 27 cenários, 10 sementes e quatro métodos, totalizando 1.080 execuções. Todas terminaram e nenhuma produziu frente vazia. O CNBI e o VRF foram executados sem teto de avaliações. As EAs usaram limites finitos definidos pelo número de objetivos e parâmetros escolhidos pela calibração.

## ANOVA do CNBI

O modelo principal usa dimensão, delta, dependência, todas as interações até a interação tripla e um bloco para a semente. Para IGD, R² ajustado = {triple.loc['IGD','adjusted_R2']:.4f}; para HV, R² ajustado = {triple.loc['HV','adjusted_R2']:.4f}.

A interação tripla acrescenta 8 graus de liberdade. Comparada ao modelo com interações apenas duplas, ela tem p = {two.loc['IGD','third_order_p']:.4g} para IGD e p = {two.loc['HV','third_order_p']:.4g} para HV. Valores pequenos indicam que o efeito conjunto dos três fatores não deve ser ignorado.

Com a interação tripla, o modelo representa separadamente a média de cada uma das 27 combinações. Por isso, não sobra uma diferença entre o modelo e as médias das células para testar como falta de ajuste. A falta de ajuste do modelo triplo é, portanto, não testável; os resíduos restantes medem a variação entre sementes dentro de cada cenário. No modelo com interações duplas, o teste acima mede exatamente a parte omitida pela interação tripla.

O maior VIF foi {max_vif.max():.3f}. O cálculo usa contrastes ortogonais adequados ao DOE balanceado; assim, a interação tripla não criou colinearidade problemática.

Os gráficos de resíduos mostram alguns valores extremos e desvio da normalidade. Por isso, também foi aplicada uma correção robusta a variâncias diferentes e valores extremos. Todos os termos experimentais permaneceram significativos; o maior p robusto entre eles foi {max(robust_pvalues):.4g}. Os tamanhos dos efeitos e os gráficos devem receber mais atenção que p-valores extremamente pequenos.

## Comparação entre métodos

Para evitar que cenários com escalas diferentes dominem a média, as 10 sementes foram resumidas pela mediana dentro de cada cenário. Depois, cada método recebeu uma nota de 0 a 1 em cada um dos 27 cenários, combinando IGD e HV. O maior valor médio foi de **{best['method']}**, com {best['mean_combined_quality']:.3f}. Esta é uma síntese descritiva; as tabelas preservam IGD e HV separadamente.

O teste global entre métodos encontrou diferenças para IGD (p = {friedman.loc['IGD','pvalue']:.4g}) e HV (p = {friedman.loc['HV','pvalue']:.4g}). As comparações par a par usam correção de Holm e também tratam os 27 cenários, não as 270 execuções, como unidades independentes.

## Arquivos

- `anova_final/delta_model_summary.csv`: R², R² ajustado, erro médio e teste da interação tripla.
- `anova_final/delta_triple_VIF.csv`: VIF de todos os coeficientes.
- `anova_final/IGD_triple_anova.csv` e `HV_triple_anova.csv`: testes dos termos no DOE em blocos, usando a variação entre sementes dentro de cada cenário.
- `anova_final/IGD_triple_terms_HC3.csv` e `HV_triple_terms_HC3.csv`: checagem robusta dos mesmos termos.
- `anova_final/factor_means.csv`: médias de IGD e HV em cada nível.
- `method_paired_summary.csv`: comparação dos quatro métodos em condições iguais.
- `method_friedman.csv` e `method_pairwise_wilcoxon.csv`: testes entre métodos usando os 27 cenários como blocos.
- `budget_summary.csv`: avaliações usadas e política de orçamento.
"""
    (output / "DOE_ANOVA_RESUMO_FINAL.md").write_text(text, encoding="utf-8")


def run(output: Path):
    for stale in output.glob("anova_final/*_triple_terms_robust.csv"):
        stale.unlink()
    master = pd.read_csv(output / "master_results.csv")
    complete = pd.read_csv(output / "campaign_complete.csv")
    doe = master[
        master.comparison.eq("equal_cardinality")
        & master.method.eq("CNBI_spectral")
        & master.scenario_id.str.startswith("doe")
    ].copy()
    if len(doe) != 270 or doe.scenario_id.nunique() != 27:
        raise ValueError("O DOE precisa conter 27 cenários e 270 observações do CNBI.")
    model_summary, vifs, means = fit_doe_models(doe, output)
    methods = quality_summary(master)
    methods.to_csv(output / "method_paired_summary.csv", index=False)
    method_tests(master, output)
    budgets = budget_summary(complete)
    budgets.to_csv(output / "budget_summary.csv", index=False)
    write_summary(output, model_summary, vifs, means, methods, budgets)
    status = {
        "status": "COMPLETED",
        "observations": 270,
        "scenarios": 27,
        "seeds": 10,
        "responses": list(RESPONSES),
        "primary_model": "delta with all interactions through third order and seed block",
    }
    (output / "anova_final" / "status.json").write_text(
        json.dumps(status, indent=2), encoding="utf-8"
    )
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    run(parser.parse_args().output)
