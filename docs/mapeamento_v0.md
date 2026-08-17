# Mapeamento metodológico da v0

| Componente | Origem | Comportamento original | Adaptação sintética | Justificativa | Estado |
|---|---|---|---|---|---|
| CCD/RSM | `RSM-CNBI_orcamento`, células 5–10 | CCD rotacional; RSM quadrático completo por OLS | 3 fatores, 19 ensaios, ordem fixa de 10 termos | Cenário aprovado | Preservado |
| Região factível | `RSM-CNBI_orcamento`, 17–21; `pareto_8D`, 2 e 6 | Caixa auxiliar e esfera `x'x <= alpha²` | `alpha=2^(3/4)` comum | Decisão explícita | Preservado |
| Payoff | `RSM-CNBI_orcamento`, 21–26 | Otimização individual; linhas são âncoras/objetivos | Todos os objetivos já são minimizados | Remove apenas conversão max/min | Preservado |
| Normalização | `RSM-CNBI_orcamento`, 23–24 | `(P-utopia)/(nadir-utopia)` | Idêntica | Necessária ao CHIM | Preservado |
| Análise paralela | `RSM-CNBI_orcamento`, 27–28 | `Var[yhat_i(xj*)]=MSE_i h(xj*)`; amplitude payoff; MC independente e sensibilidade correlacionada | Somente ramo independente, 2.000 réplicas, seed 777, p95 | Decisão explícita proíbe segunda análise | Preservado (ramo canônico) |
| Janela singular | `RSM-CNBI_orcamento`, 28–35 | `d=sum(s_real>p95)`, piso `sigma_(d+1)`, teto `sigma1/sigma_d` | Idêntica | Núcleo do CNBI v0 | Preservado |
| Combinações CNBI | `RSM-CNBI_orcamento`, 29–36 | combinações de `k=2..min(m,nx+1)` filtradas | `nx=3`, portanto `k<=4` | Sobre-determinação evitada | Preservado |
| Delta CNBI | `RSM-CNBI_orcamento`, célula 1 e 36 | adaptativo: 0.10, 0.10, 0.20, 0.50 para k=2..5 | Mesmo dicionário; k=5 fica documentado mas não ocorre com nx=3 | Aprovado pelo usuário em 2026-08-15 | Preservado |
| Subproblema NBI | `RSM-CNBI_orcamento`, 37 | SLSQP, normal orientada à origem, âncoras exatas nos vértices, warm starts e retries | Generalizado para m sintético | Sem mudar equações | Preservado |
| Orçamento | `RSM-CNBI_orcamento`, 2, 21, 37, 45–47 | uma chamada do vetor completo conta como uma avaliação; moedas separadas | Contador central único | Comparabilidade | Preservado |
| VRF-NBI | `VRF-NBI(Matheus)`, 5–14; artigo, seções 2.2–2.4 e 4.1 | padronização, PCA ≥90%, FA principal/Varimax, escores, RSM, NBI reduzido | CCD e domínio comuns; `delta=0.10` | Decisões explícitas | Preservado |
| Métricas | `comparacao_fronteiras`, 4–7 | GD/IGD p=1, HV MC pareado, Spacing e Sparsity por vizinho mais próximo | chunks e QMC em alta dimensão | Limite de RAM | Preservado |
| Cardinalidade igual | `comparacao_fronteiras`, 13–19 | clusterização hierárquica Ward e representante real mais próximo do centroide | alvo = menor cardinalidade válida no bloco | Comparação pareada | Preservado |
| Ground truth | `pareto_8D`, 5–16 | referência separada do ajuste/otimização | casco convexo analítico das âncoras | Fronteira verdadeira conhecida | Adaptação necessária e aprovada |

## Orientação canônica

A payoff pública usa **linhas = objetivos** e **colunas = configurações ótimas individuais**. A v0 armazena inicialmente cada configuração em uma linha; o adaptador transpõe explicitamente e testa `P_publica == P_v0.T`.

## Observação sobre a v0 VRF

A célula 14 do notebook de exemplo contém um objetivo `T` degenerado no trecho executável. A formulação operacional segue as equações NBI descritas no artigo e o subproblema anchor-safe da v0 CNBI, sem copiar esse defeito de implementação.

## Adaptações explicitamente autorizadas em 2026-08-17

### 1. Gerador determinístico de âncoras

- **Comportamento da v0:** os problemas originais não continham o gerador sintético atual; a primeira implementação sintética usava uma única concentração.
- **Problema:** esse parâmetro não alcançava correlação 0,25 em `m=6/12`.
- **Adaptação aprovada:** busca multi-início sobre direções e normas, com seed e penalidades explícitas.
- **Equações preservadas:** `f_j(x)=||x-a_j||²` e correlação média absoluta de Pearson sobre Sobol uniforme na esfera.
- **Efeito esperado:** nove cenários dentro de ±0,03, mantendo âncoras internas, distintas e de posto afim três.
- **Testes:** `SCENARIO_AUDIT` com 50.000 pontos, reprodutibilidade, separação, normas, posto, ótimos individuais e espectro.

### 2. Solucionador-base comum

- **Comportamento da v0:** o CNBI robusto continha equality NBI, starts, warm start e resgates; implementações auxiliares divergiam.
- **Problema:** NBI direto e VRF-NBI não herdavam todas as salvaguardas.
- **Adaptação aprovada:** `_solve_nbi_base` único dentro do notebook 03, chamado pelas três formulações.
- **Equações preservadas:** maximização de `t`, CHIM/payoff do RSM, normal orientada à origem, esfera e deltas específicos de cada método.
- **Efeito esperado:** tolerâncias, `maxiter`, jacobianas, tentativas e seleção uniformes sem igualar objetivos nem deltas.
- **Testes:** compilação, vértices anchor-safe, igualdade/esfera, ordem dos pesos, tentativas, convergência e contadores separados.

### 3. Orientação determinística dos fatores

- **Comportamento da v0:** PCA, fatores principais, Varimax, escores e RSM fatorial, mas o sinal rotacional era arbitrário.
- **Problema:** uma troca matematicamente equivalente de sinal podia inverter o sentido operacional.
- **Adaptação aprovada:** tornar positiva a carga de maior módulo de cada fator e aplicar o mesmo sinal às cargas, escores e coeficientes derivados.
- **Equações preservadas:** padronização, PCA >=90%, `principal`, Varimax e NBI fatorial minimizado.
- **Efeito esperado:** resultado independente da convenção de sinal do estimador.
- **Testes:** inversão artificial da primeira coluna antes da orientação reproduz exatamente cargas e escores orientados.

### 4. Utopia e nadir analíticos externos

- **Comportamento da v0:** normalização interna pela payoff; a primeira implementação sintética estimava extremos externos pela amostra.
- **Problema:** referência finita podia deslocar a escala das métricas e do tuning.
- **Adaptação aprovada:** `ideal_true[j]=0` e `nadir_true[j]=max_l ||a_l-a_j||²` apenas na avaliação externa.
- **Equações preservadas:** normalização interna de NBI/CNBI/VRF-NBI continua baseada na payoff do RSM.
- **Efeito esperado:** métricas, tuning e hipervolume reprodutíveis e independentes da densidade da referência.
- **Testes:** comparação analítica com todas as âncoras, inclusão exata das âncoras na referência e validação por cenário.
