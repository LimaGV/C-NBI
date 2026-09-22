"""Requested sensitivity ANOVA replacing delta by objective count m."""
import argparse
import json
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.outliers_influence import variance_inflation_factor


SOURCE = Path("experimental_results/doe_legacy_generator/master_results.csv")
OUTPUT = Path("experimental_results/doe_legacy_generator/anova_usando_m")


def run():
    OUTPUT.mkdir(exist_ok=True)
    data = pd.read_csv(SOURCE)
    data = data[(data.comparison == "equal_cardinality") &
                (data.method == "CNBI_spectral") &
                data.scenario_id.str.startswith("doe")].copy()

    categorical = smf.ols(
        "IGD ~ C(nx)*C(m)*C(dependence_level) + C(seed)", data
    ).fit()
    matrix = categorical.model.exog
    diagnostic = {
        "observations": len(data),
        "categorical_columns": matrix.shape[1],
        "categorical_rank": int(np.linalg.matrix_rank(matrix)),
        "aliased_columns": int(matrix.shape[1] - np.linalg.matrix_rank(matrix)),
        "categorical_anova_identifiable": False,
        "reason": "nx and m are not crossed; m = nx + delta + 1 in this DOE",
    }
    (OUTPUT / "categorical_design_diagnostic.json").write_text(
        json.dumps(diagnostic, indent=2), encoding="utf-8"
    )
    data.groupby(["nx", "m"]).size().unstack(fill_value=0).to_csv(
        OUTPUT / "observed_nx_m_cells.csv"
    )

    data["nx_centered"] = data.nx - data.nx.mean()
    data["m_centered"] = data.m - data.m.mean()
    formula = ("nx_centered*m_centered*C(dependence_level, Sum) + "
               "C(seed, Helmert)")
    saturated = "C(scenario_id) + C(seed, Helmert)"
    summaries = []
    for response in ("IGD", "HV"):
        ordinary = smf.ols(f"{response} ~ {formula}", data).fit()
        robust = smf.ols(f"{response} ~ {formula}", data).fit(
            cov_type="cluster", cov_kwds={"groups": data.scenario_id}, use_t=True
        )
        full_cell = smf.ols(f"{response} ~ {saturated}", data).fit()
        lof = anova_lm(ordinary, full_cell).iloc[1]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            terms = robust.wald_test_terms().table.reset_index()
        terms = terms.rename(columns={terms.columns[0]: "term"})
        for column in ("statistic", "pvalue"):
            terms[column] = terms[column].map(lambda value: np.asarray(value).item())
        terms.to_csv(OUTPUT / f"{response}_numeric_m_terms.csv", index=False)
        summaries.append({
            "response": response,
            "R2": ordinary.rsquared,
            "adjusted_R2": ordinary.rsquared_adj,
            "RMSE": float(np.sqrt(np.mean(ordinary.resid ** 2))),
            "lack_of_fit_F": lof["F"],
            "lack_of_fit_p": lof["Pr(>F)"],
            "lack_of_fit_df": lof["df_diff"],
        })
    pd.DataFrame(summaries).to_csv(OUTPUT / "numeric_m_model_summary.csv", index=False)

    vif_model = smf.ols(f"IGD ~ {formula}", data).fit()
    vifs = [
        {"coefficient": name,
         "VIF": variance_inflation_factor(vif_model.model.exog, index)}
        for index, name in enumerate(vif_model.model.exog_names)
        if name != "Intercept"
    ]
    pd.DataFrame(vifs).to_csv(OUTPUT / "numeric_m_VIF.csv", index=False)
    print(f"Resultados gravados em {OUTPUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign_output", nargs="?", type=Path,
                        default=SOURCE.parent)
    args = parser.parse_args()
    SOURCE = args.campaign_output / "master_results.csv"
    OUTPUT = args.campaign_output / "anova_usando_m"
    run()
