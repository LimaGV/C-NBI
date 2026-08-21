# CNBI Synthetic Benchmarks

Repositório científico reprodutível para avaliar NBI direto, CNBI, VRF-NBI, NSGA-III e MOEA/D em nove cenários sintéticos com três variáveis e 4, 6 ou 12 objetivos de minimização.

## Ideia científica

Cada objetivo verdadeiro é a distância quadrática até uma âncora: `f_j(x)=||x-a_j||²`. A função verdadeira serve apenas para construir a referência, calibrar cenários e avaliar soluções finais. O experimento observa `f_j(x)+erro`; um RSM quadrático é então ajustado e é o único modelo disponível aos otimizadores. Essa separação impede vazamento de ground truth.

Correlação estrutural significa que os objetivos variam juntos por causa da geometria das âncoras, não por ruído correlacionado. Para `m>4`, as respostas verdadeiras centralizadas vivem em um subespaço de dimensão máxima quatro, criando redundância natural. Por isso o repositório registra espectro singular, posto efetivo e índice de redundância.

Os nove cenários cruzam `m={4,6,12}` com correlação alvo baixa (0,25), média (0,60) e alta (0,85). Uma busca determinística multi-início ajusta direções e normas das âncoras, registra as tentativas e exige erro absoluto máximo de 0,03. Nenhum cenário fora da tolerância é renomeado.

## Região, experimento e incerteza

O domínio comum é `-alpha <= x_i <= alpha` e `x'x <= alpha²`, com `alpha=2^(3/4)`. O CCD tem 8 pontos fatoriais, 6 axiais e 5 centros. O RSM usa a ordem `[1,x1,x2,x3,x1²,x2²,x3²,x1x2,x1x3,x2x3]`.

Na análise paralela legada, `MSE_i h(x)` é a variância da média predita no ponto fixo, pois projeta a incerteza dos coeficientes através de `z(x)'(X'X)^-1z(x)`. Ela não mede incerteza na localização do ótimo. A amplitude é a diferença nadir–utopia da payoff e o Monte Carlo usa somente ruído independente, 2.000 réplicas, seed 777 e percentil 95%.

O CNBI preserva os deltas adaptativos da v0: `k=2:0.10`, `k=3:0.10`, `k=4:0.20`, `k=5:0.50`. A orientação pública da payoff é linhas=objetivos e colunas=configurações ótimas.

## Fronteira verdadeira e métricas

O conjunto de Pareto em decisões é o casco convexo das âncoras. A referência inclui explicitamente todas as âncoras e completa os pontos restantes por tetraedralização volumétrica e coordenadas baricêntricas, sem NSGA. Na avaliação externa, `ideal_true=0` e `nadir_true[j]=max_l ||a_l-a_j||²` são analíticos; dentro dos métodos, permanece a payoff do RSM. A análise calcula GD, IGD, hipervolume pareado, Spacing, Sparsity, factibilidade, convergência, avaliações e tempos, tanto para frentes completas quanto para cardinalidade igual.

## Instalação

Requer exatamente Python 3.10.11 e uma `.venv` local.

Windows:

```powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m ipykernel install --user --name cnbi-synthetic --display-name "Python (CNBI Synthetic)"
```

Linux:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m ipykernel install --user --name cnbi-synthetic --display-name "Python (CNBI Synthetic)"
```

## Execução

Ordem: notebooks `01`, `03`, `02` e `04`. O notebook `03` mede primeiro o orçamento real do CNBI; o `02` usa esse orçamento para calibrar e executar NSGA-III/MOEA-D; o `04` consolida a análise. Todos descobrem a raiz, leem `configs/<modo>.json`, gravam resultados e podem retomar por checkpoint.

```powershell
python scripts/run_notebooks.py --mode SMOKE
python scripts/run_notebooks.py --mode SCENARIO_AUDIT
python scripts/run_notebooks.py --mode PILOT
```

`SCENARIO_AUDIT` valida os nove cenários com 50.000 pontos sem executar otimizadores. `SMOKE` verifica invariantes e não produz resultados científicos. `PILOT` estima custo. `FULL` está bloqueado incondicionalmente no executor e nos notebooks e só pode ser habilitado por alteração versionada após nova autorização explícita.

Checkpoints usam schema e fingerprint, além de modo, cenário, método, dimensão, seed, orçamento, parâmetros e hashes da configuração, âncoras e RSM. Identidade divergente força recálculo. Caminhos públicos são gravados em formato POSIX.

NSGA-III e MOEA/D são calibrados separadamente por `m` apenas na correlação média e sementes 1–3. A configuração vencedora é congelada antes das sementes finais 101–110.

## Limites computacionais

O executor atual é sequencial — portanto permanece abaixo do limite de três processos científicos —, sem paralelismo aninhado e com bibliotecas BLAS limitadas a uma thread. Distâncias e hipervolume são processados em blocos, referências são carregadas cenário a cenário e `psutil` mede o pico agregado de memória do executor e de seus kernels.

## Estrutura e reprodutibilidade

- `notebooks/00_referencias_v0`: cópias sanitizadas das referências normativas.
- `configs/`: modos SMOKE, PILOT e FULL.
- `data/`: artefatos gerados não versionados.
- `results/`: checkpoints, calibração, tabelas e figuras não versionadas.
- `notebooks/05_figuras_cenarios_sinteticos.ipynb`: superfícies RSM, mapas de contorno e projeções das fronteiras de Pareto verdadeiras.
- `notebooks/06_sobreposicao_fronteiras_metodos.ipynb`: sobreposições separadas de cada método válido sobre a fronteira verdadeira.
- `notebooks/07_projecoes_comparativas_2D_3D.ipynb`: projeções 2D combinadas e vistas 3D isométricas para os cenários selecionados para o texto.
- `notebooks/08_clusterizacao_equalizacao_cardinalidade.ipynb`: benchmark de redução (FPS, K-Means, MiniBatch K-Means, GMM e Ward), seleção auditável e recálculo das comparações com cardinalidade igual.
- `docs/`: método, protocolo e mapeamento célula a célula da v0.

Notebooks são versionados sem outputs; `nbstripout`, pre-commit e CI verificam isso. Checkpoints permitem continuação após interrupção.

Licença MIT. Para citação, use `CITATION.cff`. O procedimento VRF-NBI segue Pereira et al. (2025), DOI [10.1016/j.engappai.2025.112510](https://doi.org/10.1016/j.engappai.2025.112510).
