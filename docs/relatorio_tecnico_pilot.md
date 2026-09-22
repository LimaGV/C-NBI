# Relatório técnico de implementação e validação

## 1. Identificação

- **Projeto:** CNBI Synthetic Benchmarks
- **Repositório local:** `CNBI-Synthetic-Benchmarks/`
- **Python:** 3.10.11, em ambiente local `.venv`
- **Commit científico validado:** `56f554c717c6a94da2e777dff19dddd8379161c5`
- **Escopo executado:** SMOKE e PILOT
- **Situação do FULL:** bloqueado até autorização explícita

## 2. Objetivo

O repositório implementa uma pipeline reprodutível para comparar NBI direto, CNBI, VRF-NBI, NSGA-III e MOEA/D em problemas sintéticos de otimização multiobjetivo com três variáveis de decisão, superfícies de resposta quadráticas e fronteira de Pareto verdadeira conhecida.

As funções verdadeiras são distâncias quadráticas a âncoras distintas. Elas são usadas somente na geração dos cenários, na construção da referência de Pareto, na calibração explicitamente separada e na avaliação final. Os métodos recebem exclusivamente o RSM ajustado às 19 observações do CCD com ruído experimental independente.

## 3. Correções realizadas

O estado inicial continha scaffolding que produzia listas de parâmetros pendentes e testes sobre dados artificiais sem executar a campanha científica. Esse material foi substituído pelos seguintes componentes executáveis:

1. geração e auditoria numérica dos cenários sintéticos;
2. ajuste pareado dos RSMs por cenário e semente;
3. payoff com orientação canônica — linhas como objetivos e colunas como ótimos individuais;
4. análise paralela legada independente, com 2.000 réplicas, semente 777 e percentil 95%;
5. NBI direto válido para `m=4` e status estruturalmente inválido para `m>4`;
6. CNBI com o fluxo robusto da v0;
7. VRF-NBI com padronização, PCA, retenção mínima de 90%, análise fatorial principal e rotação Varimax;
8. calibração executável de NSGA-III e MOEA/D em estágios A, B e C;
9. validação dos três finalistas por método e dimensão;
10. orçamento evolutivo pareado ao CNBI da mesma combinação cenário–semente;
11. checkpoints retomáveis e ledger de todos os subproblemas CNBI;
12. avaliação verdadeira somente após a otimização;
13. métricas completas e com cardinalidade igual;
14. rankings, estatística pareada e medição de recursos;
15. validador independente que rejeita artefatos ausentes ou inconsistentes.

## 4. Preservação metodológica do CNBI

O solver CNBI final preserva:

- vértices do simplex resolvidos pelas âncoras exatas da payoff;
- jacobianas analíticas para a igualdade NBI e a restrição esférica;
- ordenação dos pesos por vizinho mais próximo;
- warm start entre pesos consecutivos;
- combinação baricêntrica das âncoras;
- starts nas âncoras e no centro;
- até oito resgates pseudoaleatórios determinísticos;
- seleção priorizando factibilidade e, depois, maior deslocamento na normal;
- auditoria de `eq_inf`, violação esférica, start escolhido e tentativas;
- contagem das avaliações completas do RSM e das avaliações de gradiente em moedas separadas.

Foram usados os deltas adaptativos aprovados:

| Cardinalidade `k` | Delta |
|---:|---:|
| 2 | 0,10 |
| 3 | 0,10 |
| 4 | 0,20 |
| 5 | 0,50 |

Com três variáveis de decisão, os subproblemas utilizados chegam até `k=4`; `k=5` permanece registrado para preservar a configuração aprovada.

## 5. Configuração do PILOT

O PILOT utilizou:

- dimensões `m=4` e `m=12`;
- correlação estrutural média, alvo 0,60;
- sementes finais 101 e 102;
- sementes de calibração 1, 2 e 3;
- 50.000 pontos Sobol para calibração da correlação;
- 20.000 pontos na referência de Pareto por cenário;
- 100.000 amostras QMC no hipervolume;
- limite de 2.000 avaliações exclusivamente para a calibração operacional PILOT.

Esse limite não existe no `full.json`. As configurações escolhidas no PILOT não serão promovidas silenciosamente ao FULL.

## 6. Diagnóstico dos cenários

| Cenário | Correlação alvo | Correlação realizada | Posto afim | Posto efetivo | Redundância |
|---|---:|---:|---:|---:|---:|
| `m4_medium` | 0,60 | 0,600000011 | 3 | 2,1749 | 0,4563 |
| `m12_medium` | 0,60 | 0,599999996 | 3 | 2,5278 | 0,7894 |

Os dois cenários ficaram dentro da tolerância. As âncoras foram verificadas como distintas, factíveis e de posto afim três. A auditoria também confirmou ótimos individuais, reprodutibilidade da amostragem, pertencimento ao casco e não dominância aproximada da referência.

## 7. Execuções determinísticas

| Cenário | Semente | Método | Status | Soluções | Avaliações RSM | Gradientes | Convergência |
|---|---:|---|---|---:|---:|---:|---:|
| `m4_medium` | 101 | NBI | concluído | 56 | 10.268 | 182 | 55/56 |
| `m4_medium` | 102 | NBI | concluído | 56 | 2.508 | 187 | 56/56 |
| `m4_medium` | 101 | CNBI | concluído | 198 | 2.815 | 1.333 | 198/198 |
| `m4_medium` | 102 | CNBI | concluído | 320 | 4.615 | 2.077 | 320/320 |
| `m4_medium` | 101 | VRF-NBI | concluído | 11 | 516 | 108 | 11/11 |
| `m4_medium` | 102 | VRF-NBI | concluído | 11 | 568 | 110 | 11/11 |
| `m12_medium` | 101 | NBI | estruturalmente inválido | 0 | 0 | 0 | não aplicável |
| `m12_medium` | 102 | NBI | estruturalmente inválido | 0 | 0 | 0 | não aplicável |
| `m12_medium` | 101 | CNBI | concluído | 14.190 | 1.131.165 | 174.780 | 14.190/14.190 |
| `m12_medium` | 102 | CNBI | concluído | 1.365 | 21.332 | 8.648 | 1.365/1.365 |
| `m12_medium` | 101 | VRF-NBI | concluído | 66 | 2.555 | 176 | 66/66 |
| `m12_medium` | 102 | VRF-NBI | concluído | 66 | 2.564 | 194 | 66/66 |

A forte variação do orçamento CNBI entre sementes é consequência do posto retido pela análise paralela e da quantidade de combinações aceitas. Por esse motivo, usar a mediana entre sementes seria incorreto. A versão final aplica o orçamento de cada semente ao EA correspondente.

## 8. Orçamento dos algoritmos evolutivos

| Cenário | Semente | Método | Avaliações realizadas | Teto CNBI | Tempo de parede |
|---|---:|---|---:|---:|---:|
| `m4_medium` | 101 | NSGA-III | 2.800 | 2.815 | 0,27 s |
| `m4_medium` | 102 | NSGA-III | 4.585 | 4.615 | 0,41 s |
| `m4_medium` | 101 | MOEA/D | 2.800 | 2.815 | 1,54 s |
| `m4_medium` | 102 | MOEA/D | 4.585 | 4.615 | 2,59 s |
| `m12_medium` | 101 | NSGA-III | 1.130.948 | 1.131.165 | 215,81 s |
| `m12_medium` | 102 | NSGA-III | 21.112 | 21.332 | 3,88 s |
| `m12_medium` | 101 | MOEA/D | 1.130.948 | 1.131.165 | 729,39 s |
| `m12_medium` | 102 | MOEA/D | 21.112 | 21.332 | 13,26 s |

Nenhum algoritmo evolutivo ultrapassou o orçamento CNBI pareado.

## 9. Configurações vencedoras do PILOT

| Método | `m` | Partições | SBX prob. | SBX eta | PM eta | Vizinhança | Prob. mating |
|---|---:|---:|---:|---:|---:|---:|---:|
| NSGA-III | 4 | 4 | 0,9 | 20 | 30 | 0,20 | 0,90 |
| MOEA/D | 4 | 4 | 1,0 | 10 | 30 | 0,20 | 0,90 |
| NSGA-III | 12 | 3 | 0,9 | 10 | 20 | 0,20 | 0,90 |
| MOEA/D | 12 | 3 | 0,9 | 30 | 15 | 0,20 | 0,90 |

A ordem lexicográfica de seleção foi: menor mediana do IGD, maior mediana do HV, menor inviabilidade, menor IQR do IGD e menor tempo mediano.

## 10. Resultados descritivos das frentes completas

Valores abaixo são medianas das duas sementes do PILOT. Menor é melhor para GD e IGD; maior é melhor para HV.

### Cenário `m4_medium`

| Método | GD | IGD | HV |
|---|---:|---:|---:|
| CNBI | 0,0422 | **0,0644** | **0,9058** |
| MOEA/D | **0,0161** | 0,1390 | 0,7902 |
| NSGA-III | 0,0459 | 0,1725 | 0,7508 |
| VRF-NBI | 0,0918 | 0,1979 | 0,6317 |
| NBI | 0,2032 | 0,2101 | 0,6251 |

### Cenário `m12_medium`

| Método | GD | IGD | HV |
|---|---:|---:|---:|
| CNBI | 0,0411 | **0,0530** | **0,8053** |
| VRF-NBI | 0,1226 | 0,1824 | 0,5387 |
| NSGA-III | 0,0182 | 0,5234 | 0,5181 |
| MOEA/D | **0,0153** | 0,5683 | 0,4799 |

No PILOT, CNBI apresentou a melhor cobertura global pelos critérios IGD e HV nas duas dimensões. Os menores valores de GD dos algoritmos evolutivos indicam proximidade dos pontos retornados à referência, mas o IGD elevado revela cobertura insuficiente da extensão da fronteira. Essa observação é descritiva e não constitui conclusão inferencial.

Na comparação com cardinalidade igual, o CNBI permaneceu competitivo, mas as diferenças foram reduzidas, especialmente em `m=4`. As tabelas completas estão em `results/synthetic/tables/pilot_metrics.csv` e `pilot_summary.csv`.

## 11. Estatística

O PILOT possui apenas duas sementes finais. Consequentemente, os 20 blocos cenário–comparação–métrica foram registrados como `INSUFFICIENT_BLOCKS`. Não foram emitidos valores-p artificiais e nenhuma ausência de significância foi interpretada como equivalência.

O FULL, com dez sementes pareadas, executará:

- Friedman global;
- Wilcoxon pareado contra CNBI;
- correção de Holm;
- tamanho de efeito;
- mediana, IQR e ranking por repetição.

## 12. Recursos e estimativa do FULL

Na execução PILOT sem cache foram observados aproximadamente:

- 1.012,6 s de trabalho de parede acumulado;
- cerca de 18 minutos de execução total;
- pico agregado de 285.732.864 bytes, aproximadamente 272,5 MiB;
- 12,85 MB em dados e resultados locais.

A projeção conservadora do FULL é:

| Modo | Parede | Pico de RAM | Disco |
|---|---:|---:|---:|
| PILOT medido | ~18 min | 272,5 MiB | 12,85 MB |
| FULL estimado | 8–24 h | 0,5–1,5 GB | 0,2–1,0 GB |

A incerteza decorre dos nove cenários, dez sementes, inclusão de `m=6`, referências com 100.000 pontos, hipervolume com 1.000.000 de amostras e variação do orçamento CNBI entre RSMs.

## 13. Validações concluídas

Foram aprovados:

- Python 3.10.11 e `.venv` funcional;
- CCD com 19 ensaios e matriz quadrática de posto 10;
- recuperação sem ruído com erro numérico inferior a `1e-10`;
- cenário, âncoras e referência auditados;
- payoff e orientação transposta equivalentes;
- análise paralela legada reproduzível;
- deltas adaptativos corretos;
- restrições e convergência dos subproblemas CNBI;
- ausência de vazamento da função verdadeira para o otimizador;
- calibração separada das sementes finais;
- orçamento evolutivo pareado e não excedido;
- métricas completas e equalizadas;
- estatística explicitamente limitada no PILOT;
- medição de parede, CPU, RAM e disco;
- SMOKE executável;
- PILOT aprovado pelo validador forte;
- isolamento entre artefatos SMOKE e PILOT;
- notebooks sem outputs ou contagens de execução;
- ausência de caminhos pessoais, credenciais, PDF redistribuído e arquivos grandes versionados;
- worktree limpa após o commit científico;
- CI restrita ao SMOKE.

## 14. Limitações e interpretação

1. O PILOT cobre somente correlação média e duas sementes; não deve sustentar conclusões estatísticas finais.
2. Os vencedores do tuning PILOT são operacionais e não substituem a calibração FULL.
3. NBI direto é matematicamente sobre-determinado para `m=6/12` e será excluído apenas desses blocos inválidos.
4. Os alvos de correlação baixa para `m=6/12` têm limitações geométricas nesta construção de posto baixo; os valores realizados devem permanecer reportados no FULL.
5. O custo do FULL depende fortemente da dimensão retida na análise paralela e do número de sub-CHIMs aceitos.

## 15. Situação para publicação

O repositório local está sanitizado, validado e preparado para publicação. Não existe remote Git configurado e nenhum conteúdo foi enviado ao GitHub. A publicação exige autenticação externa e criação/configuração de `LimaGV/CNBI-Synthetic-Benchmarks`.

O modo FULL permanece bloqueado tanto no executor quanto nos quatro notebooks. Sua execução depende de autorização explícita após avaliação da estimativa de 8–24 horas.

## 16. Comandos de reprodução

```powershell
.venv\Scripts\python.exe scripts\run_notebooks.py --mode SMOKE
.venv\Scripts\python.exe scripts\run_notebooks.py --mode PILOT
.venv\Scripts\python.exe scripts\validate_run.py --mode PILOT
```

Não há opção `FULL` no executor automático.
