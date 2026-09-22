# Extensão experimental isolada

Este diretório não altera `cnbi/`, a versão 1.0.0rc2 ou seu empacotamento. Usa o ambiente existente Python 3.10.11 do acervo. A execução é sequencial, com BLAS em uma thread. Não há execução FULL automática.

```powershell
& CNBI-Synthetic-Benchmarks/.venv/Scripts/python.exe -m unittest discover -s cnbi_experiments/tests -v
& CNBI-Synthetic-Benchmarks/.venv/Scripts/python.exe -m cnbi_experiments.pilot --output experimental_results/pilot_verified --seeds 101 102
& CNBI-Synthetic-Benchmarks/.venv/Scripts/python.exe -m cnbi_experiments.analysis experimental_results/pilot_verified
```

O comando de piloto escreve no diretório solicitado e refaz as execuções; use um diretório novo para preservar uma execução anterior. As referências, dados por seed e diagnósticos completos acompanham os resultados. `experimental_results/pilot_resolution20` é a revisão atual, com teto de 50.000 avaliações. DOE contém somente casos sintéticos e exclui `CNBI_all`. MaF é um bloco separado. A ablação usa apenas `doe_nx2_m4_low` e contém `CNBI_all` e `CNBI_spectral`; `CNBI_all` não é executado nos demais cenários. `CNBI_spectral` é reutilizado como braço de referência, sem uma segunda execução. Os três estudos são exportados em `DOE_synthetic_results.csv`, `MaF_benchmarks_results.csv` e `ablation_results.csv`.

## Reuso e extensões explícitas

* Base e derivadas RSM com nx=3: chamadas diretas a `cnbi.rsm`; payoff verificada numericamente contra a original.
* PA_unc com nx=3: chamada direta a `cnbi.spectral.parallel_analysis`. Sua regra legada não foi substituída pela regra sequencial.
* Pesos, ordem de vizinhança e pós-processamento: chamadas diretas ao pacote `cnbi`.
* IGD, GD, HV QMC, Spacing, Sparsity e Ward: extração AST somente das funções do notebook 04, com hash; não executa células de campanha. Ward é a convenção do notebook 04, não uma alegação de vencedor do estudo do notebook 08.
* DOE: generaliza o gerador de distâncias às âncoras e a base quadrática. Mantém ALPHA, lei de ruído e alvos; a tolerância de correlação foi ampliada de 0,03 para 0,04 para comportar o caso de oito objetivos em duas dimensões. Generaliza CCD para 2^nx pontos fatoriais, 2nx axiais e cinco centros; não afirma rotatabilidade em toda dimensão. Geometria fixa por condição; seed varia a observação RSM e os otimizadores. Calibração usa momentos amostrais suficientes em vez de reconstruir toda a matriz F a cada tentativa. A amostra uniforme na bola usa Sobol com rejeição, como no gerador original, estendida para qualquer dimensão.
* Solver experimental comum às duas ablações: preserva equação NBI, normalização, limites de t e tolerâncias de aceitação; adapta domínio/dimensão e usa Jacobianas analíticas das equações MaF. Não se alega identidade de todos os candidatos com o solver legado. Sementes de resgate dependem da posição canônica do subconjunto, igual nos dois braços.
* Resolução experimental: Δ₂=0,20, Δ₃=0,20, Δ₄=0,20, Δ₅=0,50 e Δ₆=0,50. Isso produz respectivamente 6, 21, 56, 15 e 21 pesos por subconjunto. `cnbi.config.DELTA_BY_K` permanece intacto.
* PA_perm: B=1000, quantil linear 0,95, retenção sequencial até primeira falha. Coluna constante é erro explícito. Posto zero/incompatível com a payoff interrompe o método, sem truncamento silencioso. O posto vem da correlação, mas os limites da janela vêm da SVD da payoff. Isso é uma extensão aprovada, não uma equivalência teórica provada entre as duas PA.
* MaF9: regiões proibidas seguem a construção e inclusão de contorno do PlatEMO. O SLSQP recebe uma margem contínua equivalente ao mesmo conjunto viável, sem reparação aleatória. A payoff usa pontos iniciais nas arestas e desempate determinístico entre os mínimos não únicos das retas. O VRF propaga a restrição, os pontos geométricos e a Jacobiana analítica dos escores fatoriais. EAs usam reparação explícita.
* VRF: por solicitação expressa do usuário, usa k=max(2,k90): pelo menos dois fatores e retenção acumulada de pelo menos 90%. Registra k90, k escolhido e retenção real; verifica k<=nx+1 sem reduzir silenciosamente a retenção. Mantém principal/varimax e orientação dos sinais. RSM ajusta os scores por mínimos quadrados; MaF usa mapa afim de scores sobre avaliações diretas, treinado em 256 pontos uniformes factíveis do domínio, cobrado no orçamento. Esta é uma adaptação experimental, não a rotina RSM inalterada.
* EAs: operadores base do notebook 02, partições=2, SBX p=1/eta=20, PM p=1/nx/eta=20; MOEA/D vizinhança=20%, cruzamento local=90%. Sem alegação de recalibração para os novos casos. Entrega a última população concluída, preservando o total real de avaliações, inclusive as de uma geração interrompida.

## Orçamento, ablação e interpretação

A revisão atual usa teto comum de 50.000 avaliações vetoriais por método/caso/seed; o comando de exemplo conserva o piloto rápido de 8.000. Payoff, diferenças finitas quando necessárias, recomposição e os 500 vetores da PA usada pelo método entram no teto. Gradientes analíticos são registrados separadamente, assim como tempo de diagnóstico. Observações RSM fornecidas são dados de entrada comuns; referência externa e sensibilidade de PA são auditorias separadas. A contagem não é a moeda incompleta D09 do legado. Um teto de avaliações não implica igualdade de CPU ou gasto realizado.

`all` enumera todos os subconjuntos k=2..min(M,nx+1), sem filtro; degenerados ficam registrados como tais, sem normal inventada. Ao atingir o teto, registra os não alcançados. Portanto uma execução interrompida **não é** uma ablação exaustiva completa. `spectral` usa o mesmo solver e a janela correspondente ao problema.

Cardinalidade: todos os cinco métodos entram no mínimo por caso/seed. Se qualquer um não retorna frente, a comparação equalizada é marcada bloqueada, sem excluir o método. As diferenças all–spectral são pareadas por caso/seed. As três condições do piloto não permitem estimar efeitos fatoriais/interações: o módulo estatístico exige as 27 condições replicadas.

Limitações e falhas do piloto estão no relatório. Não extrapole superioridade científica de resultados truncados ou de configurações base não recalibradas. A infraestrutura atual entrega desenho e piloto; não constitui uma campanha completa validada.
