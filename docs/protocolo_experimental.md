# Protocolo experimental

1. Execute `01_geracao_cenarios_sinteticos.ipynb` para CCD, âncoras e referências.
2. Execute `03_pipeline_CNBI_comparacoes.ipynb` com checkpoints por cenário/semente/método para medir o orçamento CNBI completo, incluindo payoff.
3. Execute `02_calibracao_NSGAIII_MOEAD.ipynb` apenas para PILOT/FULL; as execuções finais usam o orçamento CNBI pareado do mesmo cenário e da mesma semente.
4. Execute `04_analise_resultados.ipynb` para métricas e inferência pareada.

SMOKE valida estrutura e invariantes, mas não produz evidência científica. PILOT estima custo. FULL requer confirmação explícita e nunca é iniciado pela CI.

Antes do PILOT, execute `python scripts/run_notebooks.py --mode SCENARIO_AUDIT` e `python scripts/validate_scenarios.py`. Resultados anteriores são movidos para `results/synthetic/backups/<data>/`, nunca apagados silenciosamente. A campanha limpa começa apenas com `.gitkeep` nos diretórios ativos.

O estágio B usa 12 configurações balanceadas: 6 por `n_partitions`, 6 por probabilidade SBX, 4 por eta SBX e 4 por eta PM, sem duplicatas. O vencedor é congelado somente depois da validação dos três finalistas nas seeds 1–3 pelos cinco critérios lexicográficos.

No PILOT, `tuning_budget_cap=2000` limita somente a busca de hiperparâmetros para estimativa operacional. As configurações PILOT são válidas para a campanha PILOT e não são promovidas silenciosamente ao FULL. O `full.json` não contém esse teto: após autorização, o FULL recalibra por `m` no cenário médio usando o orçamento CNBI correspondente e congela novos vencedores antes das sementes finais.

## Medição do PILOT e estimativa do FULL

Os valores abaixo pertencem ao PILOT histórico e são substituídos pela campanha corrigida documentada em `docs/relatorio_tecnico_pilot_corrigido.md`.

O PILOT histórico (`m=4/12`, correlação média, sementes 101–102) mediu 1.012,6 s de trabalho de parede acumulado nos métodos, pico agregado de 285.732.864 bytes (272,5 MiB) e 12,85 MB de dados/resultados locais. O executor completo levou aproximadamente 18 minutos na execução sem cache.

| Modo | Parede estimada | Pico de RAM | Disco |
|---|---:|---:|---:|
| PILOT medido | ~18 min | 272,5 MiB | 12,85 MB |
| FULL (incluindo análise) | 8–24 h | 0,5–1,5 GB | 0,2–1,0 GB |

A projeção de FULL parte de 90 blocos cenário–semente contra quatro no PILOT, acrescenta `m=6`, referências cinco vezes maiores e dez vezes mais amostras de hipervolume. A faixa permanece ampla porque o posto retido pela análise paralela e o orçamento CNBI variam fortemente entre RSMs. O FULL continua bloqueado até autorização explícita.

## Medição corrigida de 2026-08-17

O PILOT definitivo sem cache mediu 3.839,33 s end-to-end, 3.836,72 s de CPU total do runner e descendentes, pico agregado de 981.590.016 bytes e 46.718.258 bytes de disco ativo. Nenhum checkpoint foi reutilizado. A estimativa revisada do FULL é 24–96 h, 1–4 GB de RAM e 0,5–2 GB de disco. Os detalhes e limitações estão em `docs/relatorio_tecnico_pilot_corrigido.md`.
