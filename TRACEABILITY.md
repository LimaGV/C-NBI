# Rastreabilidade metodologia ↔ código

Fonte normativa computacional: `CNBI-Synthetic-Benchmarks/notebooks/03_pipeline_CNBI_comparacoes.ipynb`, célula 2. O filtro auxiliar vem do notebook 04, célula 6. Linhas originais constam em `provenance/EXTRACTION.json`.

| Etapa | Formulação/critério preservado | Arquivo | Função |
|---|---|---|---|
| base RSM | `z=[1,x1,x2,x3,x1²,x2²,x3²,x1x2,x1x3,x2x3]` | `cnbi/rsm.py` | `z` |
| derivadas RSM | `∂z/∂x` analítica e na mesma ordem | `cnbi/rsm.py` | `dz` |
| payoff | mínimo SLSQP de `z(x)B[:,j]` na caixa e esfera; `P[:,j]=z(x*j)B` | `cnbi/payoff.py` | `individual_payoff` |
| normalização global | `ideal=min(P,axis=1)`; `amp=max(P)-ideal`; `(P-ideal)/amp` | `cnbi/spectral.py` | `parallel_analysis` |
| CHIM global | âncoras em linhas `A=Pscaled.T`; `E=A[1:]-A[:1]`; SVD | `cnbi/spectral.py` | `parallel_analysis` |
| incerteza RSM | `h_i=z(x*i)ᵀ(XᵀX)⁻¹z(x*i)`; `sd_ij=sqrt(h_i MSE_j)/amp_j` | `cnbi/spectral.py` | `parallel_analysis` |
| análise paralela | ruído normal independente; SVD por réplica; p95 posicional; `d=max(1,sum(s>p95))` | `cnbi/spectral.py` | `parallel_analysis` |
| janela global | piso `s[d]` se existir, senão zero; teto `s1/sd` | `cnbi/spectral.py` | `parallel_analysis` |
| combinações | todos os subconjuntos lexicográficos para `2≤k≤min(m,4)` | `cnbi/core.py` | `cnbi` |
| seleção sub-CHIM | SVD de `Pscaled[combo,combo].T`; `smin>floor` e `s1/smin≤ceiling`; `smin≤1e-12` implica infinito | `cnbi/core.py` | `cnbi` |
| Simplex-Lattice | `p=round(1/delta)`; inteiros não negativos com soma p; divisão por p | `cnbi/combinations.py` | `simplex_weights` |
| ordem dos betas | vizinho mais próximo desde o índice zero, desempate pelo índice | `cnbi/combinations.py` | `_nearest_weight_order` |
| normalização local | `ideal=min(Psub,axis=1)`; `amp=max(max(Psub)-ideal,1e-12)` | `cnbi/nbi.py` | `_solve_nbi_base` |
| sub-CHIM/normal | `A=Psub_scaled.T`; null space de `A[1:]-A[:1]`; sinal para a origem | `cnbi/nbi.py` | `_solve_nbi_base` |
| ponto CHIM | `phi=beta@A` | `cnbi/nbi.py` | `_solve_nbi_base` |
| NBI | minimizar `-t`, igualdade `Fscaled(x)=phi+t n`, esfera `α²-xᵀx≥0` | `cnbi/nbi.py` | `_solve_nbi_base` |
| aceitação | sucesso SLSQP e `eq_inf≤1e-5`, violação esférica `≤1e-8` | `cnbi/nbi.py` | `_solve_nbi_base` |
| starts/resgate | vértices exatos; warm, baricêntrico, âncoras, centro; até 8 resgates determinísticos | `cnbi/nbi.py` | `_solve_nbi_base` |
| recomposição | `F_rsm=z(x)@output_B` para todos os m objetivos | `cnbi/nbi.py` | `_solve_nbi_base` |
| união | concatenação dos candidatos por k e combinação; falhas permanecem identificadas | `cnbi/core.py` | `cnbi` |
| fronteira bruta | todos os candidatos e estados permanecem na saída do núcleo | `cnbi/core.py` | `cnbi` |
| dominância opcional | `Fj≤Fi+tol` em todos e `Fj<Fi-tol` em pelo menos um | `cnbi/pareto.py` | `nondominated` |
| duplicatas opcionais | quantização de X na resolução configurada; menor soma de F; índice desempata | `cnbi/pareto.py` | `postprocess_frontier` |
| fronteira estimada/real | a semântica depende de F fornecido pelo chamador; nenhum ground truth interno | `cnbi/pareto.py` | `postprocess_frontier` |

## Hipóteses e escopo

`B` contém objetivos já convertidos para minimização. A orientação pública da payoff é linhas=objetivos e colunas=configurações ótimas. As amplitudes e limiares são derivados da payoff RSM. O solver opera somente em três variáveis e esfera de raio `2**0.75`. A função verdadeira dos benchmarks não é entrada e não está presente no pacote.

O diagnóstico espectral usa normalização global para selecionar combinações. Cada NBI usa nova normalização restrita à subpayoff. Essa diferença é deliberadamente preservada do notebook 03 e é a divergência D01 em `AUDIT_REPORT.md`.

## Critérios de parada e tolerâncias

Payoff e NBI usam SLSQP. O payoff usa `ftol=1e-11`, `maxiter=500` por padrão; o NBI usa `ftol=1e-10`, `maxiter=500` por padrão. Ambos os limites de iteração são parâmetros autorizados. A aceitação posterior do NBI é independente do `ftol`: exige as tolerâncias acima. Os valores completos estão em `PARAMETERS.md`.

## Evidência de preservação

`tests/test_preservation.py` compara a AST das funções não parametrizadas. Para payoff, NBI e orquestração, compara os resultados padrões exatamente em três dimensões de objetivo e com `full_m4_low_seed103_CNBI_071001488d2e.npz`, identificado pelo fingerprint `common-nbi-valid-payoff-v4`. Testes adicionais cobrem starts/iterações configuráveis e pós-processamento estimado/real.
