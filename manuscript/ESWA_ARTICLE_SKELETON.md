# Article skeleton for Expert Systems with Applications

## Working title

**Combinatorial normal boundary intersection with spectral objective screening for structurally dependent many-objective optimization**

Alternative, more application-oriented title:

**Spectral decomposition of structurally dependent objectives for many-objective decision support: The CNBI method and an eight-response turning application**

> Editorial note: use the first title if the algorithm is the central contribution. Use the second if the journal fit is built around intelligent decision support in manufacturing.

## Authors and affiliations

- Gabriel Victor de Lima — affiliation, email, ORCID
- Mirelli de Castro Cesário — affiliation, email, ORCID
- Matheus Costa Pereira — affiliation, email, ORCID
- Anderson Paulo de Paiva — affiliation, email, ORCID
- Corresponding author: **to be defined**

> Confirm author order, affiliations, ORCIDs and corresponding author before submission. The final author list must reflect actual contributions.

## Central claim

CNBI extends normal boundary intersection to problems in which the number of objectives exceeds the dimensional limit of conventional NBI. It estimates the effective structure of the objectives, selects informative and geometrically admissible objective subsets, solves lower-dimensional NBI subproblems, and recomposes the solutions in the complete objective space. Its value is demonstrated through controlled synthetic experiments, standard many-objective stress tests, and an eight-response manufacturing application.

## Research questions

**RQ1.** Can CNBI generate well-covered Pareto approximations when the number of objectives exceeds the conventional NBI dimensional condition?

**RQ2.** How do decision-space dimension, dimensional excess and structural dependence affect CNBI performance?

**RQ3.** How does CNBI compare with VRF-NBI, NSGA-III and MOEA/D in solution quality and computational cost?

**RQ4.** Does CNBI remain useful in a real manufacturing problem with eight correlated responses?

**RQ5.** How much computational effort does spectral screening remove, and what quality is preserved?

**RQ6.** Under which structures does CNBI lose performance or produce sparse or extreme solutions?

## Intended contributions

1. A combinatorial extension of NBI that handles the regime (m>n_x+1) through temporary objective subsets and full-space recomposition.
2. A noise-aware spectral screening procedure that estimates effective objective structure and avoids solving every admissible subset.
3. A controlled factorial study separating the effects of (n_x), dimensional excess and structural dependence.
4. A comparison with VRF-NBI, NSGA-III and MOEA/D using solution quality, computational cost and both native and controlled cardinality.
5. Validation on an eight-response turning problem and complementary MaF8, MaF9 and MaF13 stress tests.
6. An auditable implementation with fixed seeds, checkpointed experiments, preserved raw candidates and documented numerical tolerances.

## Proposed highlights

- CNBI extends normal boundary intersection to many-objective problems.
- Spectral screening identifies informative objective subsets.
- Controlled experiments isolate dimension and dependence effects.
- CNBI improves Pareto-front coverage in most synthetic scenarios.
- An eight-response turning case demonstrates practical usefulness.

> Check the journal-specific highlight limit immediately before submission. Elsevier commonly requests three to five bullets with no more than 85 characters each.

## Abstract skeleton

Many-objective optimization becomes difficult when the number of objectives exceeds the dimensional structure supported by classical normal boundary intersection (NBI). This study proposes combinatorial normal boundary intersection (CNBI), a method that estimates effective objective structure, selects geometrically informative subsets, solves lower-dimensional NBI subproblems, and recomposes candidate solutions in the full objective space. The method is evaluated in a controlled (3\times3\times3) factorial experiment that varies decision-space dimension, dimensional excess, and structural dependence. Ten independent replications are used for each of the 27 conditions, and CNBI is compared with VRF-NBI, NSGA-III and MOEA/D. With native output cardinality, CNBI obtains the best IGD in 26 of 27 scenarios and the best hypervolume in 22. Under cardinality control, it retains the best IGD in 20 scenarios, showing that its main advantage is broad Pareto-front coverage. The factorial model explains 88.3% of the adjusted variation in IGD and 97.0% in hypervolume, with a relevant three-way interaction among the structural factors. In an eight-response turning application, CNBI attains an IGD of 0.0754 and a hypervolume of 0.5023, remaining competitive with NSGA-III and outperforming VRF-NBI and MOEA/D in coverage. MaF8 and MaF9 confirm stable front approximation, whereas MaF13 exposes limitations caused by duplicated objective structure and extreme solutions. These results support CNBI as an interpretable many-objective decision-support method while identifying the conditions under which its spectral decomposition is most beneficial.

> Values in this draft are taken from the current validated outputs. Recheck every number from the final manuscript tables before submission.

## Keywords

Many-objective optimization; Normal boundary intersection; Objective screening; Parallel analysis; Response surface methodology; Manufacturing decision support

# 1. Introduction

### Paragraph 1 — Practical problem

Explain why engineering and manufacturing decisions increasingly involve many correlated and conflicting responses. Use the turning case to make the problem concrete: productivity, reliability, wear, surface quality, capability, return and equipment effectiveness must be considered simultaneously.

### Paragraph 2 — Limitation of classical NBI

Introduce NBI and its value for generating evenly distributed Pareto solutions. State clearly that its conventional geometric formulation becomes structurally incompatible when the number of objectives is larger than the admissible dimension defined by the decision space.

### Paragraph 3 — Limitations of existing responses

Discuss three common approaches:

- evolutionary many-objective algorithms, which can require many evaluations;
- factor-based reduction, which replaces the original objectives and may reduce interpretability;
- objective selection, which may permanently discard responses that remain relevant to decision makers.

### Paragraph 4 — Proposed idea

Present CNBI in accessible terms: it does not permanently remove original objectives. It temporarily solves carefully selected lower-dimensional problems and evaluates each solution again in the complete response space.

### Paragraph 5 — Evidence gap

State that a useful validation must distinguish the effects of decision dimension, dimensional excess and objective dependence; compare against both the closest factor-based method and established evolutionary methods; and test a real application.

### Paragraph 6 — Contributions

Present the six contributions listed above. Avoid claiming universal superiority.

### Paragraph 7 — Article organization

Briefly describe Sections 2–7.

# 2. Related work

## 2.1 Normal boundary intersection and response-surface optimization

- Classical NBI geometry and dimensional condition.
- NBI coupled with response surface methodology.
- Benefits and limitations in problems with many responses.

## 2.2 Many-objective evolutionary optimization

- NSGA-III and reference directions.
- MOEA/D and decomposition into scalar subproblems.
- Recent reference-vector or decomposition methods relevant to the final baseline set.

> Decision before final submission: determine whether one modern baseline, such as RVEA or MOEA/DD, will be added. If it is not added, justify why VRF-NBI, NSGA-III and MOEA/D cover the closest methodological families.

## 2.3 Objective reduction and multivariate methods

- PCA and factor-analysis approaches.
- VRF-NBI and rotated factor scores.
- Objective selection versus objective transformation.
- Loss of interpretability and loss of trade-offs.

## 2.4 Research gap

End with a direct gap statement:

> Existing methods either optimize all objectives at high computational cost, transform the original objectives into latent factors, or permanently reduce the objective set. A method is still needed that uses dependence information to select solvable objective subsets while preserving full-space evaluation and the original meaning of every response.

# 3. The CNBI method

## 3.1 Problem definition

Define the constrained minimization problem

\[
\min_{x\in\Omega} F(x)=\left(f_1(x),\ldots,f_m(x)\right),
\]

with (x\in\mathbb{R}^{n_x}), (m) objectives and the dimensional excess

\[
\delta=m-(n_x+1).
\]

Clarify that objective directions are converted to minimization before optimization.

## 3.2 Response-surface representation

- Quadratic RSM and design matrix.
- Estimated coefficients, residual mean squares and prediction uncertainty.
- Individual optima and payoff matrix.

## 3.3 Spectral diagnosis

- Global payoff normalization.
- Construction of the CHIM difference matrix.
- Singular-value spectrum.
- Parallel analysis using propagated RSM uncertainty.
- Effective dimension and screening window.

Explain the logic before presenting equations: observed geometric components must be stronger than components expected from model noise.

## 3.4 Combinatorial objective subsets

- Enumerate (k=2,\ldots,\min(m,n_x+1)).
- Construct every candidate subset.
- Evaluate the sub-CHIM spectrum.
- Retain subsets that fall inside the global spectral window.

### Final resolution rule and versioning

The final method evaluated in this article uses a resolution of 20% for (k\leq4) and 50% for (k>4). This rule is fixed for the final synthetic campaign, MaF benchmarks and reported application analyses.

The registered historical core used (0.10,0.10,0.20,0.50) for (k=2,3,4,5). Preserve that package as the audited CNBI 1.0 record and identify the multidimensional 20%/50% implementation as the final extended article version. The Methods and reproducibility files must state this version distinction explicitly.

## 3.5 Lower-dimensional NBI solution

- Local payoff normalization.
- Simplex-Lattice weights.
- CHIM point and outward normal.
- SLSQP formulation, bounds, spherical constraint, warm starts and deterministic rescue starts.
- Feasibility and convergence criteria.

## 3.6 Full-space recomposition and Pareto processing

- Reevaluate each decision vector in all (m) objectives.
- Preserve raw candidates and failure statuses.
- Remove duplicates and dominated points only during declared post-processing.
- Distinguish RSM-estimated fronts from externally evaluated true fronts.

## 3.7 Algorithm and complexity

Include pseudocode as **Algorithm 1** and report complexity in terms of:

- number of candidate subsets;
- number of retained subsets;
- weights per subset;
- solver starts and evaluations;
- cost of parallel analysis.

# 4. Experimental methodology

## 4.1 Overview and hypotheses

Map each experiment to the research questions. Keep the three blocks separate:

1. controlled synthetic DOE;
2. MaF stress tests;
3. eight-response turning application.

The ablation remains an independent analysis.

## 4.2 Controlled synthetic DOE

- (n_x\in\{2,3,5\}).
- (delta\in\{1,3,5\}).
- (m=n_x+1+\delta).
- structural dependence: low, medium and high.
- 27 structural conditions.
- 10 seeds per condition.
- true objectives defined by squared distances to controlled anchors.
- multidimensional extension preserves the original generator logic.
- realized dependence tolerance: 0.04.
- independent Gaussian observation noise calibrated to the stated RSM fit.

Explain why DOE is used only for synthetic cases: the three factors can be controlled independently only in the synthetic generator.

## 4.3 Compared methods

- CNBI.
- VRF-NBI with at least two factors or 90% retained variation and the loading-based library fallback.
- NSGA-III with frozen calibrated parameters.
- MOEA/D with frozen calibrated parameters.

CNBI-all must not appear in the main DOE. It belongs only to the ablation.

## 4.4 Stopping rules and computational cost

- CNBI and VRF-NBI run until their deterministic procedures finish.
- Evolutionary algorithms use the calibrated population-dependent limit corresponding to approximately 400 generations, from 50,000 to 400,400 evaluations.
- Report evaluations and wall-clock time as outcomes.
- Explain that the natural-output analysis measures the complete service delivered by each method.

## 4.5 Pareto reference and performance indicators

- IGD: lower is better; reflects convergence and coverage.
- GD: lower is better; reflects average point proximity.
- HV: higher is better; reflects dominated objective-space volume.
- Spacing and sparsity as secondary indicators.
- Explicitly document normalization and the common HV reference point.

## 4.6 Cardinality policy

Use two complementary analyses:

1. **Primary — native fronts:** retains the number of solutions naturally produced by each method.
2. **Sensitivity — controlled cardinality:** compares point placement when only the same number of alternatives is retained.

Do not describe minimum-cardinality reduction as inherently fairer. Some current blocks fall to only 2–6 points, which changes the scientific question and strongly affects HV. Add fixed-cardinality curves at meaningful values when all compared fronts contain enough points. Runs unable to provide the required number must be identified rather than forcing every method down to the smallest front.

## 4.7 Statistical analysis

- Summarize the 10 seeds within each structural scenario.
- Use 27 scenarios as paired blocks for method comparisons.
- Friedman global test followed by paired Wilcoxon tests with Holm correction.
- For CNBI structural behavior, use categorical (n_x\), (delta\), dependence and interactions, with seed as a block.
- Report adjusted (R^2), residual error, robust checks and the limitation that lack of fit cannot be estimated for the saturated three-way model.
- Explain why replacing (delta) with (m) creates aliasing in this design.

## 4.8 MaF stress tests

- MaF8 and MaF9: (M=4,6,8,10,15).
- MaF13: (M=8,10,15).
- Formulations checked against Cheng et al. and the fixed PlatEMO revision.
- Horn parallel analysis by independent column permutation.
- Sensitivity sample sizes: 250, 500, 1,000 and 5,000.
- CNBI only in the final MaF campaign.
- For MaF13, retain the original metric table and add an explicit normalization audit with point-distance quantiles so that the influence of extreme solutions remains visible.

State explicitly that MaF evaluates CNBI generalization and failure modes; it is not a formal method-comparison block.

## 4.9 Eight-response turning application

### Process and variables

- Tempered cylindrical steel-bar turning process.
- Decision variables: cutting speed, feed rate and depth of cut.
- Responses: (T), MTTF, WR, Ra, Rt, Kp, ROI and OEE.
- Original optimization directions must be listed.
- Describe the experimental design and RSM quality.

### Comparison protocol

- CNBI and VRF-NBI deterministic fronts.
- NSGA-III and MOEA/D with 10 final seeds.
- Equal budget of 19,830 evaluations for each EA run.
- Independent empirical Pareto reference.
- Normalized GD, IGD and paired Sobol-QMC HV.
- Bootstrap confidence intervals and Holm-adjusted comparisons.

### Prior-use disclosure

The turning data were previously used in the 2025 VRF-NBI article. Cite that article as the data and application source. Clearly state that the new contribution is the CNBI method, the corrected common evaluation protocol and the new comparisons. Do not describe the dataset as a new physical experiment.

## 4.10 Ablation study

- Nine predeclared synthetic cases selected as a balanced subset: each level of decision dimension, dimensional excess and dependence appears three times.
- CNBI-all versus CNBI-spectral.
- Same problem and seeds.
- Compare IGD, GD, HV, evaluations and selected combinations.

Limit the inference to these selected structures. Present the ablation as mechanism verification rather than universal evidence.

## 4.11 Reproducibility

- Python and library versions.
- Seeds and random-number streams.
- Calibration and final seeds separated.
- Checkpoint fingerprints and implementation hashes.
- Raw candidates, failure statuses and audit ledgers.
- Public code and data repository with DOI before acceptance, if possible.

# 5. Results

## 5.1 Synthetic DOE validity

Report first:

- 1,080 unique completed executions;
- no empty fronts;
- 27 conditions, 10 seeds and four methods;
- all dependence targets within tolerance;
- audit and verification status.

## 5.2 Method comparison with native fronts

Lead with the main practical result:

- CNBI best IGD in 26 of 27 scenarios.
- CNBI best HV in 22 of 27 scenarios.
- Identify the losses rather than hiding them.
- Compare evaluations and time.

Interpretation: CNBI's main strength is producing a broad representation of the frontier with fewer evaluations than the evolutionary methods in the typical run.

## 5.3 Cardinality-controlled sensitivity

- CNBI best IGD in 20 of 27 scenarios.
- NSGA-III wins 3, VRF-NBI wins 3 and MOEA/D wins 1.
- CNBI best HV in only 3 scenarios after minimum-cardinality reduction.
- Explain that several blocks were reduced to 2–6 points.
- Present fixed-cardinality curves at 2, 5, 10 and 20 points. At each size, include only paired scenario/seed blocks in which all methods contain enough points and report the number of available blocks.

Interpretation: CNBI remains strong in IGD, but part of its HV advantage comes from producing richer fronts. Extremely small decision sets favor methods that preserve a few extreme points.

## 5.4 Structural effects from the factorial model

Report:

- IGD: (R^2=0.8979\), adjusted (R^2=0.8826\), RMSE (=0.0171\).
- HV: (R^2=0.9739\), adjusted (R^2=0.9700\), RMSE (=0.0330\).
- significant three-way interaction for both responses;
- maximum VIF of 1 under orthogonal contrasts;
- robust tests confirming the experimental terms;
- residual outliers and the resulting emphasis on effects and plots.

Avoid turning the interaction into a single rule. Show which combinations of dimension, excess and dependence are favorable or difficult.

## 5.5 Computational effort

Current typical medians:

| Method | Evaluations | Time (s) |
|---|---:|---:|
| CNBI | 12,031 | 1.13 |
| VRF-NBI | 1,095 | 0.39 |
| NSGA-III | 84,000 | 11.46 |
| MOEA/D | 84,000 | 56.00 |

Explain quality and cost together. VRF-NBI is the fastest but has poorer coverage; CNBI occupies an intermediate-cost, high-coverage position.

## 5.6 MaF results and failure analysis

### MaF8 and MaF9

- Good visual coverage in decision and objective projections.
- IGD generally improves or remains stable as (M) increases.
- Final front size increases with (M).

### MaF13

- Median IGD: 0.3959, 0.4249 and 0.4767 for (M=8,10,15).
- Final fronts contain approximately 17–19 points.
- Objectives from the fourth onward share the same equation.
- Many accepted subproblem solutions collapse to repeated decisions.
- Extreme solutions produce very large raw GD.
- Retain the original values and report the normalized audit with median, 90th percentile, 95th percentile and maximum point-to-front distances. This separates typical behavior from the effect of a few extreme solutions.

Interpretation: MaF13 is evidence of a limitation, not an optimizer-budget failure.

## 5.7 Turning application

Report the native-front results:

| Method | IGD | GD | HV |
|---|---:|---:|---:|
| CNBI | **0.0754** | 0.0269 | **0.5023** |
| NSGA-III | 0.0958 | 0.0282 | 0.5018 |
| VRF-NBI | 0.3782 | 0.0375 | 0.3236 |
| MOEA/D | 0.4257 | **0.00073** | 0.1979 |

Explain the trade-off:

- CNBI and NSGA-III provide the best global coverage.
- Their HV values are practically equal and not statistically different.
- MOEA/D places points very close to a limited region of the reference front, producing excellent GD but poor IGD and HV.
- VRF-NBI is sparse and covers less of the full eight-response trade-off surface.

Because the article is centered on the method, keep the practical discussion concise. Use one or two representative Pareto solutions to show how cutting speed, feed and depth of cut change reliability, surface quality, productivity and economic responses.

## 5.8 Ablation

The paired ablation contains nine contrasting synthetic scenarios and 10 seeds per scenario. Each level of decision dimension, dimensional excess and dependence appears three times. CNBI-all is restricted to this analysis. Both arms use the same saved payoff matrix and individual optima, so the only methodological difference is whether the spectral filter selects combinations.

| Scenario | Median evaluation reduction | Median IGD increase | Median HV loss |
|---|---:|---:|---:|
| (n_x=2,m=4), low dependence | 16.0% | 0.0034 | 0.0049 |
| (n_x=2,m=6), medium dependence | 25.7% | 0.0053 | 0.0051 |
| (n_x=2,m=8), high dependence | 72.6% | 0.0058 | 0.0069 |
| (n_x=3,m=5), high dependence | 94.7% | 0.0032 | 0.0053 |
| (n_x=3,m=7), low dependence | 46.1% | 0.0056 | 0.0096 |
| (n_x=3,m=9), medium dependence | 70.5% | 0.0067 | 0.0072 |
| (n_x=5,m=7), medium dependence | 96.7% | 0.0049 | 0.0111 |
| (n_x=5,m=9), high dependence | 99.1% | 0.0133 | 0.0232 |
| (n_x=5,m=11), low dependence | 63.8% | 0.0037 | 0.0056 |

The median evaluation reduction ranges from 16.0% to 99.1%. The largest saving occurs at (n_x=5,m=9) with high dependence, where the median IGD increase is 0.0133 and the median HV loss is 0.0232. In the other eight cases, the IGD increase remains at or below 0.0067 and the HV loss at or below 0.0111. Treat these results as evidence about the filtering mechanism across contrasting structures, not as a universal saving rate.

# 6. Discussion

## 6.1 What CNBI contributes

- Preserves the meaning of every original objective.
- Avoids optimizing only latent factor scores.
- Enables NBI-style search beyond the classical dimensional condition.
- Produces an interpretable ledger connecting each solution to an objective subset.

## 6.2 When CNBI works best

- Problems where multiple objective subsets contain complementary trade-offs.
- Problems where complete-front coverage is valuable.
- RSM-based engineering problems with expensive evaluations.
- Structures in which spectral screening removes noisy or redundant sub-CHIMs without collapsing the search.

## 6.3 Why CNBI loses in some cases

- At very small output cardinalities, its distributed front is compressed and may lose extremes important to HV.
- High dependence can favor VRF-NBI because a small latent-factor representation matches the low-dimensional structure.
- MOEA/D can achieve very low GD by concentrating points near a narrow Pareto region.
- MaF13 collapses many objective combinations into repeated decisions and permits extreme candidates.

## 6.4 Practical decision-support value

Discuss the number and diversity of alternatives available to the decision maker. Explain why cardinality is part of the method's output, while controlled cardinality answers a separate practical question about a limited decision set.

## 6.5 Relationship to VRF-NBI

State the distinction explicitly:

- VRF-NBI transforms correlated responses into latent factors and solves NBI in factor space.
- CNBI keeps original objectives, selects subsets using spectral evidence and recomposes every candidate in the complete objective space.

The comparison must focus on this structural difference rather than only numerical performance.

# 7. Limitations and threats to validity

- The registered core is specialized to quadratic RSMs with three decision variables.
- The extended experimental solver generalizes dimensions but must be versioned separately and documented.
- The DOE generator uses squared-distance objectives; other landscapes may behave differently.
- The MaF final block evaluates only CNBI.
- The ablation uses a small, deliberately contrasting subset of synthetic scenarios and does not support universal cost-saving claims.
- CNBI and VRF-NBI are deterministic for a fixed RSM, whereas the evolutionary methods are stochastic.
- Minimum-cardinality equalization can reduce fronts to very few points.
- The turning application reuses a previously published experimental dataset.
- MaF13 raw distance metrics are influenced by extreme objective scales.
- Additional modern baselines may strengthen the state-of-the-art comparison.

# 8. Conclusions

Use four short parts:

1. CNBI successfully extends NBI-style search to structurally overdetermined many-objective problems.
2. The controlled DOE shows strong IGD performance and a joint dependence on decision dimension, dimensional excess and structural dependence.
3. The turning application confirms practical competitiveness, while MaF13 identifies a clear limitation.
4. Future work should study adaptive cardinality, broader nonlinear models, additional benchmark families and safeguards against repeated or extreme solutions.

Avoid claims such as “CNBI is universally superior” or “CNBI always reduces cost without quality loss.”

# Declarations

## Funding

**To be completed with the exact agencies, grant numbers and author recipients.**

## Competing interests

The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.

## Data availability

Draft:

> The source code, experiment configurations, random seeds, raw results and processed tables supporting this study will be deposited in a public repository. The repository and archived DOI will be added before publication.

## Author contributions

Prepare a CRediT statement covering conceptualization, methodology, software, validation, formal analysis, investigation, data curation, writing, visualization, supervision and funding acquisition.

## Declaration of generative AI and AI-assisted technologies

Draft consistent with the current Elsevier policy:

> During the preparation of this work, the authors used OpenAI Codex to support the organization of the manuscript, code review, data-analysis verification and language editing. The authors reviewed and edited all outputs and take full responsibility for the content of the publication.

The authors must adjust this statement to describe the actual final use.

# Planned tables

1. Notation and differences among NBI, VRF-NBI and CNBI.
2. CNBI algorithm stages and numerical rules.
3. Synthetic factorial design.
4. Comparator parameters and stopping rules.
5. Native-front method comparison across 27 scenarios.
6. Cardinality-controlled sensitivity results.
7. Factorial-model ANOVA and interaction plots.
8. MaF summary and spectral ranks.
9. Turning application metrics and confidence intervals.
10. Ablation results.

# Planned figures

1. CNBI workflow from RSM to full-space Pareto front.
2. Geometric explanation of objective subsets and recomposition.
3. DOE main effects and interactions in Minitab-style panels.
4. Method ranks for native IGD and HV.
5. IGD and HV versus retained cardinality.
6. MaF8, MaF9 and MaF13: true front versus CNBI.
7. Turning application: normalized parallel coordinates and representative trade-offs.
8. Quality-versus-evaluation-cost comparison.
9. Ablation: quality retained versus evaluations removed.

# Supplementary material

- S1. Full mathematical derivation and pseudocode.
- S2. Complete parameter table and software versions.
- S3. All 27 scenario-by-method summaries and seed-level results.
- S4. Residual diagnostics and robust factorial tests.
- S5. Complete MaF equations and validation against PlatEMO.
- S6. Parallel-analysis spectra and sample-size sensitivity.
- S7. Turning RSM coefficients and response diagnostics.
- S8. All Pareto solutions and cardinality-reduction diagnostics.
- S9. Audit reports, hashes, checkpoints and reproduction instructions.

# Claims supported by the current evidence

- CNBI provides the best native-front IGD in 26 of 27 controlled scenarios.
- CNBI remains best in equal-cardinality IGD in 20 of 27 scenarios.
- CNBI has strong complete-front coverage and competitive computational cost.
- CNBI and NSGA-III have comparable HV in the turning application.
- Spectral screening can preserve quality while reducing evaluations in the selected ablation scenarios; the magnitude depends on problem structure.
- MaF13 reveals a structural limitation involving repeated decisions and extreme candidates.

# Claims that must not be made

- CNBI is universally superior to evolutionary methods.
- Cardinality equalization is always fairer than native-front comparison.
- The turning dataset is a new physical experiment.
- MaF proves superiority over other methods.
- Any ablation saving observed in the selected cases generalizes to all problems.
- Large MaF13 GD is caused by an evaluation budget.

# Work remaining before submission

## Essential

1. Align the versioned article code and documentation with the fixed 20%/50% rule while preserving the audited historical release.
2. Incorporate the generated quality-versus-cardinality curves and their availability counts.
3. Incorporate the normalized MaF13 audit while retaining the original table.
4. Add a concise practical interpretation using one or two turning trade-offs.
5. Complete the literature review and novelty comparison with recent methods.
6. Consolidate code and data into a public, citable release.
7. Verify every table and number against immutable result files.

## Strengthening, if computationally feasible

1. Add one modern many-objective baseline on the controlled DOE or a representative subset.
2. Consider additional ablation scenarios only if the nine-case balanced subset reveals an unresolved mechanism.

## Manuscript positioning sentence

> CNBI is an interpretable decomposition and decision-support framework for many-objective response-surface optimization, designed to preserve original objectives while exploiting their effective spectral structure.
