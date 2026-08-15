# Critérios de aceitação executáveis

O repositório só pode ser declarado pronto quando todos os itens abaixo forem comprovados por artefatos gerados, não por flags ou mensagens impressas.

| Bloco | Evidência obrigatória | Regra de aprovação |
|---|---|---|
| Cenários | `scenario_diagnostics.csv` e NPZ por cenário | nove cenários no FULL; correlação realizada, posto e redundância registrados |
| RSM | tabela por cenário/semente | 19 ensaios, posto 10, R²/MSE/SNR e recuperação sem ruído |
| Payoff/CHIM | tabela e orientação testada | linhas=objetivos; colunas=ótimos; adaptador transposto equivalente |
| Análise paralela | espectro real e p95 por cenário/semente | somente independente; 2.000 MC; seed 777 |
| NBI direto | checkpoint por cenário/semente | válido apenas para m=4; m>4 explicitamente inválido |
| CNBI | checkpoint retomável por cenário/método/semente e ledger por combinação/beta | deltas adaptativos; orçamento real incluindo payoff; gradientes separados; restrições e convergência auditadas |
| VRF-NBI | PCA/FA/loadings/escores e checkpoint | PCA >=90%, principal+Varimax; invalidade estrutural não mascarada |
| Calibração EA | resultados por configuração/semente | estágios A/B/C realmente executados; vencedores congelados por método/m |
| Experimento final | manifesto por cenário/método/semente | mesmos RSMs pareados; nenhuma função verdadeira chamada pelo otimizador |
| Métricas | tabela completa e equalizada | GD, IGD, HV+erro, Spacing, Sparsity, factibilidade, custo e tempos |
| Estatística | tabela por cenário/métrica | Friedman, Wilcoxon vs CNBI, Holm e tamanho de efeito em blocos válidos |
| Recursos | manifesto JSON | parede, CPU, pico de RAM e disco medidos |

O executor deve falhar quando qualquer evidência estiver ausente, vazia, marcada como pendente ou contiver menos blocos do que a configuração exige.
