# Protocolo experimental

1. Execute `01_geracao_cenarios_sinteticos.ipynb` para CCD, âncoras e referências.
2. Execute `03_pipeline_CNBI_comparacoes.ipynb` com checkpoints por cenário/semente/método para medir o orçamento CNBI completo, incluindo payoff.
3. Execute `02_calibracao_NSGAIII_MOEAD.ipynb` apenas para PILOT/FULL; as execuções finais usam o orçamento CNBI pareado do mesmo cenário e da mesma semente.
4. Execute `04_analise_resultados.ipynb` para métricas e inferência pareada.

SMOKE valida estrutura e invariantes, mas não produz evidência científica. PILOT estima custo. FULL requer confirmação explícita e nunca é iniciado pela CI.

No PILOT, `tuning_budget_cap=2000` limita somente a busca de hiperparâmetros para estimativa operacional. As configurações PILOT são válidas para a campanha PILOT e não são promovidas silenciosamente ao FULL. O `full.json` não contém esse teto: após autorização, o FULL recalibra por `m` no cenário médio usando o orçamento CNBI correspondente e congela novos vencedores antes das sementes finais.

## Medição do PILOT e estimativa do FULL

O PILOT validado (`m=4/12`, correlação média, sementes 101–102) mediu 1.012,6 s de trabalho de parede acumulado nos métodos, pico agregado de 285.732.864 bytes (272,5 MiB) e 12,85 MB de dados/resultados locais. O executor completo levou aproximadamente 18 minutos na execução sem cache.

| Modo | Parede estimada | Pico de RAM | Disco |
|---|---:|---:|---:|
| PILOT medido | ~18 min | 272,5 MiB | 12,85 MB |
| FULL (incluindo análise) | 8–24 h | 0,5–1,5 GB | 0,2–1,0 GB |

A projeção de FULL parte de 90 blocos cenário–semente contra quatro no PILOT, acrescenta `m=6`, referências cinco vezes maiores e dez vezes mais amostras de hipervolume. A faixa permanece ampla porque o posto retido pela análise paralela e o orçamento CNBI variam fortemente entre RSMs. O FULL continua bloqueado até autorização explícita.
