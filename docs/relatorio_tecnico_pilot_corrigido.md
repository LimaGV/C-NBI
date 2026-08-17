# Relatório técnico do PILOT corrigido

## Identificação e escopo

- Python 3.10.11 em `.venv` local recriada; `pip check` aprovado.
- Modos executados: validação estática, `SCENARIO_AUDIT`, SMOKE e PILOT.
- FULL: não executado e bloqueado incondicionalmente no executor e nos notebooks.
- Função sintética preservada: `f_j(x)=||x-a_j||²`.
- Deltas CNBI preservados: `k=2:0,10`, `k=3:0,10`, `k=4:0,20`, `k=5:0,50`.

## Origem dos resultados

O PILOT definitivo foi calculado integralmente do zero depois que os artefatos anteriores foram movidos para backups datados ignorados pelo Git. O manifesto final registra `cache_used=false` e `checkpoints_reused=0`. Nenhum resultado numérico anterior foi reutilizado. O `SCENARIO_AUDIT` também foi recalculado com 50.000 pontos Sobol e permaneceu isolado dos artefatos PILOT.

As tentativas interrompidas durante a correção foram preservadas em backups e não participam das tabelas ativas. A causa observada foi engenharia de exportação do ledger (lookup antigo, ordem reconstruída e descompactação repetida), não mudança das equações científicas.

## Correções implementadas

1. busca determinística multi-início de direções e normas das âncoras, com penalidades e auditoria completa;
2. referência com todas as âncoras explicitamente incluídas;
3. ideal `0` e nadir analítico usados somente no tuning e avaliação externa;
4. solver-base anchor-safe único para NBI, CNBI e VRF-NBI;
5. orientação determinística dos fatores e teste exato de invariância a troca de sinal;
6. status `COMPLETED_WITH_FAILURES` quando há qualquer falha de subproblema;
7. estágio B balanceado sem recorte de produto cartesiano;
8. três finalistas validados antes do congelamento do vencedor;
9. checkpoints com schema, fingerprint e hashes científicos;
10. ledger copiado diretamente das linhas do solver, na ordem efetiva;
11. efeito rank-biserial por postos das diferenças, com sinal positivo favorável ao CNBI;
12. redução/equalização calculada uma única vez;
13. caminhos de manifestos em POSIX e remoção do filtro Git absoluto do `nbstripout`;
14. monitoramento de parede, CPU do runner e descendentes, RSS e disco.

## Auditoria dos nove cenários

| Cenário | Alvo | Realizada | Desvio absoluto | Posto afim | Distância mínima |
|---|---:|---:|---:|---:|---:|
| `m4_low` | 0,25 | 0,250866 | 0,000866 | 3 | 1,248692 |
| `m4_medium` | 0,60 | 0,599296 | 0,000704 | 3 | 0,330685 |
| `m4_high` | 0,85 | 0,850552 | 0,000552 | 3 | 0,168188 |
| `m6_low` | 0,25 | 0,250146 | 0,000146 | 3 | 1,011162 |
| `m6_medium` | 0,60 | 0,599047 | 0,000953 | 3 | 0,606064 |
| `m6_high` | 0,85 | 0,849491 | 0,000509 | 3 | 0,169260 |
| `m12_low` | 0,25 | 0,253074 | 0,003074 | 3 | 0,168171 |
| `m12_medium` | 0,60 | 0,599763 | 0,000237 | 3 | 0,217131 |
| `m12_high` | 0,85 | 0,839189 | 0,010811 | 3 | 0,168038 |

Todos ficaram dentro de ±0,03. O validador também confirmou âncoras distintas e internas, ótimos individuais, espectro, referência reprodutível, inclusão exata das âncoras e ideal/nadir analíticos.

## Métodos determinísticos

| Cenário | Seed | Método | Status | Soluções | Avaliações RSM | Gradientes | Convergência |
|---|---:|---|---|---:|---:|---:|---:|
| `m4_medium` | 101 | NBI | COMPLETED | 56 | 1.185 | 584 | 100% |
| `m4_medium` | 102 | NBI | COMPLETED | 56 | 4.572 | 832 | 100% |
| `m4_medium` | 101 | CNBI | COMPLETED | 55 | 892 | 578 | 100% |
| `m4_medium` | 102 | CNBI | COMPLETED | 386 | 6.572 | 2.734 | 100% |
| `m4_medium` | 101 | VRF-NBI | COMPLETED | 11 | 242 | 182 | 100% |
| `m4_medium` | 102 | VRF-NBI | COMPLETED | 11 | 226 | 166 | 100% |
| `m12_medium` | 101 | NBI | STRUCTURALLY_INVALID | 0 | 0 | 0 | n/a |
| `m12_medium` | 102 | NBI | STRUCTURALLY_INVALID | 0 | 0 | 0 | n/a |
| `m12_medium` | 101 | CNBI | COMPLETED_WITH_FAILURES | 22.694 | 3.336.350 | 428.509 | 99,8281% |
| `m12_medium` | 102 | CNBI | COMPLETED | 28.448 | 719.455 | 205.869 | 100% |
| `m12_medium` | 101 | VRF-NBI | COMPLETED | 66 | 967 | 516 | 100% |
| `m12_medium` | 102 | VRF-NBI | COMPLETED | 66 | 963 | 516 | 100% |

A falha parcial do CNBI em `m12_medium`, seed 101, permaneceu visível no manifesto e esse bloco não foi tratado como frente concluída na análise.

## Tuning e parâmetros congelados

O tuning usou seeds 1–3 e teto operacional de 2.000 avaliações. Os vencedores abaixo foram escolhidos somente depois da validação dos três finalistas por menor IGD mediano, maior HV mediano, menor inviabilidade mediana, menor IQR do IGD e menor tempo mediano.

| Método | m | Partições | SBX prob. | SBX eta | PM eta | Vizinhança | Mating vizinho |
|---|---:|---:|---:|---:|---:|---:|---:|
| NSGA-III | 4 | 4 | 1,0 | 30 | 30 | 0,2 | 0,9 |
| MOEA/D | 4 | 4 | 0,9 | 30 | 20 | 0,1 | 1,0 |
| NSGA-III | 12 | 3 | 0,9 | 20 | 30 | 0,2 | 0,9 |
| MOEA/D | 12 | 3 | 0,9 | 10 | 15 | 0,3 | 1,0 |

## Verificação dos orçamentos evolucionários

| Cenário | Seed | Teto CNBI | NSGA-III | MOEA/D |
|---|---:|---:|---:|---:|
| `m4_medium` | 101 | 892 | 875 | 875 |
| `m4_medium` | 102 | 6.572 | 6.545 | 6.545 |
| `m12_medium` | 101 | 3.336.350 | 3.336.060 | 3.336.060 |
| `m12_medium` | 102 | 719.455 | 719.264 | 719.264 |

Nenhuma execução excedeu o orçamento CNBI do mesmo cenário e seed. O teto de tuning PILOT não aparece na identidade de uma execução FULL e o modo faz parte do fingerprint.

## Recursos medidos

| Medida | Valor |
|---|---:|
| Parede end-to-end | 3.839,33 s (63,99 min) |
| Soma das paredes dos métodos | 3.584,28 s |
| CPU do runner | 88,05 s |
| CPU dos descendentes | 3.748,67 s |
| CPU total medida | 3.836,72 s |
| Pico agregado real de RSS | 981.590.016 bytes (936,12 MiB) |
| Disco ativo | 46.718.258 bytes (44,55 MiB) |
| Cache | não utilizado |
| Checkpoints reutilizados | 0 |

A medição cobre geração, métodos determinísticos, tuning, EAs, notebook 04, filtragem, equalização, estatística, runner e kernels descendentes.

## Métricas e estatística

GD, IGD, HV com erro padrão, Spacing, Sparsity, factibilidade, convergência, avaliações e tempos foram calculados para frentes completas e cardinalidade equalizada. Todas as métricas validadas são finitas. Os 20 blocos estatísticos foram marcados como `INSUFFICIENT_BLOCKS`, pois o PILOT possui somente duas seeds; não há inferência conclusiva nem alegação de superioridade científica.

## Limitações e falhas

1. o PILOT cobre apenas correlação média e duas seeds;
2. um bloco CNBI teve falhas explícitas e não deve ser interpretado como frente completa;
3. os vencedores PILOT são operacionais e não podem ser promovidos ao FULL;
4. NBI direto é estruturalmente inválido para `m>4`;
5. o custo é muito sensível ao posto retido e ao número de subproblemas CNBI.

## Estimativa revisada do FULL

Extrapolando quatro blocos cenário-seed do PILOT para 90 blocos do FULL, acrescentando `m=6`, referências cinco vezes maiores e hipervolume dez vezes maior, a faixa prudente passa a ser:

- parede: 24–96 horas;
- pico de RAM: 1–4 GB, ainda dependente da equalização e das referências;
- disco adicional: 0,5–2 GB.

Essa estimativa não autoriza a execução. O FULL permanece bloqueado porque exige nova autorização explícita, recalibração própria sem `tuning_budget_cap=2000` e avaliação prévia do tempo disponível.

## Validações executadas

- compilação de todas as células e validação nbformat;
- ausência de outputs e `execution_count`;
- invariantes CCD/RSM, ruído, payoff e análise paralela;
- `SCENARIO_AUDIT` forte;
- SMOKE completo;
- PILOT limpo e validador forte;
- `pip check`;
- sanitização e nova rodada de validação (registrada no commit final);
- busca de caminhos pessoais/segredos, `git fsck`, status e pacote `git archive` (registrados no commit final).

## Publicação

Em 2026-08-17, a API pública do GitHub retornou `404` para `LimaGV/CNBI-Synthetic-Benchmarks`, indicando que o repositório não existe publicamente. O GitHub CLI não está instalado e não há sessão autenticada disponível neste ambiente; por isso nenhum remoto foi criado e nenhum push foi feito. Não foi solicitado token ou senha no chat, não houve force push e o FULL não foi executado.
