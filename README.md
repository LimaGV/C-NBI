# CNBI — Combinatorial Normal Boundary Intersection

Versão explícita: **1.0.0rc2**, candidata técnica ainda não congelada. A implementação foi extraída conservadoramente do `notebooks/03_pipeline_CNBI_comparacoes.ipynb`, selecionado nesta auditoria como referência normativa. A rc2 acrescenta parâmetros autorizados e pós-processamento opcional sem mudar os padrões numéricos.

## Finalidade

O CNBI decompõe temporariamente um problema com muitos objetivos em subconjuntos dimensionalmente admissíveis, seleciona sub-CHIMs por uma janela espectral, executa NBI em cada subconjunto e recompõe cada candidato no espaço completo dos objetivos. Esta versão recebe modelos RSM quadráticos de três variáveis e objetivos já orientados para minimização.

Fluxo implementado:

`B, MSE, (DᵀD)⁻¹` → payoff individual → diagnóstico global/análise paralela → combinações `k=2..min(m,4)` → seleção espectral → NBI local → recomposição RSM completa → candidatos brutos → filtro Pareto auxiliar opcional.

O pacote não contém NSGA-III, MOEA/D, VRF-NBI, funções verdadeiras dos benchmarks, métricas, plotting ou clusterização. Esses componentes pertencem ao repositório experimental e não ao núcleo consolidado.

## Requisitos e instalação

- Python exatamente 3.10.11;
- NumPy 1.26.4;
- SciPy 1.14.1.

Em um ambiente virtual limpo, na raiz desta pasta:

```powershell
py -3.10 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install --no-deps .
```

## Entradas

As entradas públicas seguem o notebook normativo:

- `B`: matriz NumPy `(10, m)` dos coeficientes RSM na ordem `[1,x1,x2,x3,x1²,x2²,x3²,x1x2,x1x3,x2x3]`; todas as colunas devem estar no sentido de minimização;
- `mse`: vetor `(m,)` dos quadrados médios residuais;
- `XtX_inv`: matriz `(10,10)` igual a `(DᵀD)⁻¹` do ajuste;
- `P`: payoff `(m,m)`, com objetivos nas linhas e configurações ótimas nas colunas;
- `Xstar`: matriz `(m,3)` das configurações ótimas individuais.

O notebook 03 não implementa validação formal de shapes, finitude, simetria ou definitude. A candidata conserva esse comportamento: entradas incompatíveis falham nas operações NumPy/SciPy correspondentes.

## Parâmetros preservados

`ALPHA=2**0.75`; deltas `{2:0.10, 3:0.10, 4:0.20, 5:0.50}`; análise paralela com 2.000 réplicas, seed 777 e percentil 95. Payoff e NBI usam 500 iterações por padrão. Tolerâncias, limites e sementes completas estão em `PARAMETERS.md`.

`individual_payoff(B, starts=None, maxiter=500)` usa sete pontos normativos quando `starts=None`. Para alterar sua quantidade, forneça uma sequência explícita de vetores `(3,)`; a quantidade é `len(starts)`. Isso evita inventar uma distribuição de novos pontos.

`cnbi(..., maxiter=500, max_rescues=8)` permite configurar o limite do SLSQP e o número máximo de resgates. Não há parâmetro para substituir solver, normalização, janela, número de variáveis, critério de aceitação ou regras combinatórias.

## Execução

```python
import numpy as np
from cnbi import individual_payoff, cnbi, postprocess_frontier

xstar, payoff = individual_payoff(B, maxiter=500)
raw_candidates, diagnostic = cnbi(
    B, payoff, xstar, mse, XtX_inv,
    maxiter=500, max_rescues=8,
)

accepted = [row for row in raw_candidates if row["accepted"]]
X = np.vstack([row["x"] for row in accepted])
F_rsm = np.vstack([row["F_rsm"] for row in accepted])
estimated_frontier = postprocess_frontier(
    X, F_rsm,
    duplicate_tolerance=1e-5,
    dominance_tolerance=1e-10,
)
```

`cnbi` sempre preserva todos os candidatos, inclusive falhas com `subproblem_status="NO_FEASIBLE_INTERSECTION"`. Cada linha inclui combinação, beta, ordem, solução `x`, respostas recompostas `F_rsm`, resíduos, violações, start e log de tentativas.

`diagnostic` inclui dimensão efetiva, espectro observado, limiares de ruído, piso/teto da janela e contadores. O contador RSM tem o mesmo alcance do notebook 03; veja `AUDIT_REPORT.md`, D09.

## Exemplo mínimo

```powershell
python examples/minimal_example.py
```

O exemplo lê uma pequena entrada RSM reproduzível, executa o CNBI sem chamar funções verdadeiras e sempre grava `examples/output/cnbi_candidates_raw.csv`. Por padrão, também grava `cnbi_frontier_estimated_rsm.csv` e `summary.json`. Use `--no-postprocess` para gerar somente os candidatos brutos; `--help` mostra os limites e tolerâncias configuráveis.

`postprocess_frontier(X,F,...)` é opcional. Se `F` contiver previsões, o resultado é uma fronteira **estimada**; se o usuário avaliar os mesmos `X` nas funções reais e passar `F_real`, o resultado é uma fronteira **real**. O pacote não confunde nem combina as duas. A etapa pode remover duplicatas e dominadas, com opções e tolerâncias configuráveis. Os candidatos brutos nunca são apagados.

## Testes

```powershell
python -m unittest discover -s tests -v
```

A suíte compara por AST os corpos não parametrizados, executa fixtures de 4, 6 e 12 objetivos e verifica payoff, parâmetros, normalização, CHIM/SVD, seleção, NBI, recomposição, determinismo, pós-processamento e checkpoint histórico v4. Com os padrões, os resultados continuam exatamente iguais ao notebook 03.

O workflow `.github/workflows/tests.yml` repete a instalação, a suíte e o exemplo mínimo em cada push e pull request no GitHub, usando Python 3.10.11.

## Arquitetura

- `cnbi/rsm.py`: base quadrática e jacobiana;
- `cnbi/payoff.py`: otimização individual e payoff;
- `cnbi/spectral.py`: análise paralela e janela global;
- `cnbi/combinations.py`: Simplex-Lattice e ordem dos pesos;
- `cnbi/nbi.py`: solucionador NBI local comum;
- `cnbi/core.py`: seleção combinatória e orquestração;
- `cnbi/pareto.py`: dominância e pós-processamento opcional com tolerâncias configuráveis;
- `examples/`: exemplo e entrada RSM;
- `tests/fixtures/`: fontes originais, entradas e checkpoint de regressão;
- `provenance/`: extração, inventário e análise estática.

## Limitações conhecidas

- três variáveis de decisão e RSM quadrático com dez termos são fixos;
- somente minimização; conversão de sentidos deve ocorrer antes da chamada;
- execução sequencial e em memória;
- `null_space(E).ravel()` pressupõe nulidade unidimensional nas combinações aceitas;
- a análise paralela usa exclusivamente perturbações independentes;
- o pós-processamento não é automático: o chamador escolhe avaliações RSM estimadas ou avaliações reais e preserva a saída bruta;
- avisos do SLSQP sobre clipping aos bounds podem ocorrer e também aparecem na fonte normativa;
- não há alegação de equivalência à implementação aplicada v0 nem ao texto atual da dissertação nas divergências D01–D16.

## Dependências, autoria e licença

Autores oficiais declarados:

- Gabriel Victor de Lima;
- Mirelli de Castro Cesário;
- Anderson Paulo de Paiva.

O arquivo `CITATION.cff` fornece esses nomes em formato reconhecido pelo GitHub e por gerenciadores bibliográficos. Veja `DEPENDENCIES_AND_ATTRIBUTIONS.md`. `ORIGINAL_LICENSE.txt` preserva o aviso MIT encontrado no repositório de origem. A autoria está definida; a candidata ainda não declara titularidade institucional nem cria uma nova licença, pois essas decisões permanecem pendentes.

## Estado da versão

Esta pasta é a **CNBI v1.0 — candidata técnica ao registro**. Ainda não deve receber hash definitivo nem ser declarada pronta para protocolo porque há divergências documentais/metodológicas e uma decisão de licenciamento pendentes. Não foi executado nenhum modo FULL.
