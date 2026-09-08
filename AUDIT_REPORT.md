# Auditoria CNBI v1.0 — candidata, sem congelamento

Data: 2026-09-07. Inspeção inicial realizada antes da criação deste arquivo.
Fonte: checkout de trabalho local `CNBI-Synthetic-Benchmarks/`, excluído do repositório publicável, incluindo suas alterações locais preexistentes. Nenhum original foi sanitizado, corrigido ou sobrescrito.

## Decisões do usuário

- Referência normativa selecionada nesta sessão: **pipeline sintético atual, notebook 03**. A v0 aplicada não será mesclada com ele.
- Modularização Python expressamente solicitada prevalece sobre a regra histórica de manter metodologia em notebooks do AGENTS.md original.
- Em 2026-09-08, o autor definiu 500 iterações como padrão configurável no payoff e NBI; os sete starts do payoff permanecem padrão e uma lista explícita permite alterar sua quantidade.
- A fronteira bruta é sempre entregue. A remoção de duplicatas e dominadas é opcional, com tolerâncias configuráveis, e aceita separadamente avaliações RSM estimadas ou avaliações reais externas.
- Autores oficiais declarados em 2026-09-08, nesta ordem: Gabriel Victor de Lima, Mirelli de Castro Cesário, Matheus Costa Pereira e Anderson Paulo de Paiva. Titularidade patrimonial e licença permanecem decisões separadas.

## Mapa reconstruído antes da consolidação

Entrada: notebook 01 gera CCD de 19 ensaios, três fatores, observações sintéticas e ajuste RSM quadrático completo. Notebook 03 também reconstrói esse ajuste por cenário/semente.

`B (10 × m), MSE (m), (DᵀD)⁻¹ (10 × 10)` → `individual_payoff`: ótimos individuais SLSQP, payoff com objetivos nas linhas → `parallel_analysis`: normalização GLOBAL, arestas por diferenças de âncoras, SVD, propagação MSE × alavancagem, 2.000 réplicas independentes/seed 777/p95, dimensão e janela → `cnbi`: combinações lexicográficas de k=2..min(m,4), SVD do sub-CHIM na escala GLOBAL e seleção pela janela → `_solve_nbi_base`: normalização LOCAL da subpayoff, normal por null_space, malha adaptativa, SLSQP/warm starts/resgates → recomposição `z(x) @ B` em todos os objetivos RSM → candidatos brutos, sucesso e diagnósticos.

Fluxo externo: notebook 04 aplica sucesso/factibilidade, reavalia funções VERDADEIRAS e filtra dominância exata; calcula métricas e equalização. Portanto esse fluxo externo não é uma fronteira filtrada no RSM. O notebook 03 termina em candidatos, incluindo falhas identificadas.

## Inventário inicial e separação

32 notebooks, 251 células: quatro referências v0; notebooks 01–04 geração/otimização/comparação; 05–08 figuras/equalização; 09–14 referência e avaliação aplicada/análises complementares; 15–28 figuras e resumos. Nove scripts Python em scripts/, além de caches. Seis documentos Markdown metodológicos em docs/, quatro configurações, dados, checkpoints NPZ/JSON, tabelas CSV e figuras. Pastas tmp/, output/, outputs/ e `docx_qa/` contêm preparação editorial, documentos, renders e dependências auxiliares.

O ZIP externo tem 36.192 entradas e 8 notebooks; o ZIP de dist tem 58 entradas e 8 notebooks. Não representam o checkout atual de 32 notebooks. `scripts/package_release.py` usa git archive HEAD e omite alterações locais/arquivos não rastreados: inadequado para empacotar esta candidata.

Núcleo específico selecionado: análise paralela do CHIM, janela singular e seleção combinatória, orquestração dos subproblemas e recomposição. RSM, payoff, NBI, simplex e dominância são operações científicas compartilhadas: sua implementação no projeto não constitui reivindicação de autoria dos algoritmos matemáticos. IO, exportação e interface são infraestrutura. NSGA-III, MOEA/D, VRF-NBI, PCA/FA/Varimax, métricas e clusterização ficam fora do pacote computacional.

## Divergências e decisões

Células numeradas a partir de 1, incluindo Markdown; documentos antigos usam outra numeração.

| ID | Arquivo e função/bloco | Encontrado e alternativas | Impacto potencial | Recomendação/decisão |
|---|---|---|---|---|
| D01 | 03, cél. 2, cnbi/_solve_nbi_base; v0 RSM, cél. 38, calcular_chim_local | Seleção global e NBI local no 03; v0 usa escala global também no NBI | Muda normal, trajetória e candidatos | Preservar 03 por decisão explícita; não alegar equivalência à v0 |
| D02 | 03, individual_payoff; v0 cél. 21–22 | 7 starts centro/±0,99α, jacobiana, ftol=1e-11 e 500 iterações versus starts axiais/aleatórios seed123, diferenças finitas, ftol=1e-12 e 1000 | Muda payoff, seleção e custo | Resolvido: padrão do 03; starts explícitos e maxiter configuráveis por autorização de 2026-09-08 |
| D03 | 03, _solve_nbi_base; v0 cél. 38; dissertação §3.4.4 | 500 iterações no 03; 1000 na v0/texto; texto descreve início central, código tem vértices exatos e múltiplos starts | Não equivale ao procedimento textual | Resolvido no software: 500 configurável, âncoras/warm/baricêntrico/centro/8 resgates; dissertação precisa ser alinhada |
| D04 | 03, parallel_analysis e _solve_nbi_base | Amplitude global <=1e-12 vira 1; amplitude local é limitada inferiormente a 1e-12 | Tratamento distinto de objetivos degenerados | Preservar ambos; não unificar normalização |
| D05 | 03, _nearest_weight_order, cél. 2 linhas 82 e 88 | Duas definições textualmente iguais; a segunda sobrescreve a primeira | Sem diferença comportamental observada | Manter uma definição; comprovar igualdade estrutural |
| D06 | 03, cnbi; v0 cél. 30/36/38 | IDs aceitos e betas base zero/ordem lexicográfica versus IDs globais base um/ordenação por k,q,sigma | Muda seeds de resgate e ordem das saídas | Preservar 03 sem reindexação |
| D07 | 03, _solve_nbi_base; v0 calcular_chim_local | null_space(E).ravel() versus último vetor de SVD; v0 verifica orientação indefinida e âncoras | Nulidade >1 ou geometria degenerada pode falhar no 03 | Não substituir decomposição nem acrescentar filtros; registrar limite |
| D08 | 03 saída; 04 analyze_filtered_results; v0 cél. 41–42; dissertação §3.4.5 | 03 bruto RSM; 04 dominância exata em ground truth sem deduplicação; v0 arredonda X a 5 casas, desempata por soma escalada e usa tol=1e-10 | Cardinalidade, identidade e fronteira diferentes | Resolvido na interface: bruto sempre; etapa opcional recebe F estimado ou real e tolerâncias configuráveis |
| D09 | 03 contadores; v0 ContadorAvaliacoes | Gradientes separados no 03; recomposição não incrementa full; payoff final também não incrementa contador | Orçamentos não equivalem a todas as operações RSM nem à moeda v0 | Preservar contagem e documentar alcance |
| D10 | v0 cél. 29; 03 parallel_analysis | v0 calcula sensibilidade correlacionada; 03 somente independente | Diagnósticos adicionais não equivalentes | Manter exclusivamente independente conforme AGENTS/docs |
| D11 | 19_retencao_recomposicao_cnbi, cél. 3 | Percentuais de retenção digitados em records, não calculados de checkpoints | Figura não comprova deduplicação no pipeline 03/04 | Excluir do núcleo e não usar como teste de regressão |
| D12 | 13,25–28 e scripts de benchmark aplicado | Caminhos pessoais absolutos; figuras leem arquivos externos | Não portável | Excluir auxiliares; não alterar originais |
| D13 | README versus scripts/run_notebooks.py | README diz FULL bloqueado incondicionalmente; executor permite --confirm-full | Documentação operacional desatualizada | Não executar FULL; executor não integra candidata |
| D14 | v0 build_design_matrix/PA; 03 ajuste no escopo de campanha | v0 pinv; sintético inv(DᵀD), três variáveis fixas e minimização em todos os objetivos | Generalização não demonstrada | Limitar API ao RSM sintético existente; sem solver/normalização novos |
| D15 | LICENSE/CITATION.cff/references | MIT com aviso LimaGV existe; os quatro autores foram declarados nesta auditoria; titularidade patrimonial e autorização institucional não foram definidas | Licenciamento e titularidade ainda exigem confirmação documental | Autoria registrada em `CITATION.cff`; preservar aviso existente sem inventar titularidade ou nova licença |
| D16 | scripts/run_notebooks.py; notebook 06, cél. 4 | O SMOKE desativa otimizadores, então o notebook 04 não cria `smoke_method_runs.csv`; o executor ainda chama o notebook 06, que exige esse arquivo | O smoke completo sempre pode falhar depois de validar o núcleo e o notebook 05 | Não alterar o experimento durante a consolidação; corrigir em decisão versionada separada |

## Auditoria estática original

`python scripts/validate_notebooks.py` executado com Python 3.10.11 da .venv original: **falhou**, por outputs/execution_count em notebooks posteriores e caminhos pessoais. A análise AST das células de código não identificou erros de sintaxe. Não foi executada sanitização que apagasse esses outputs. Esta falha preexiste à consolidação.

Dependências importadas adicionais ao requirements original incluem plotly, deap e pyDOE2 nas referências/auxiliares; python-docx/Pillow no trabalho editorial. Não são dependências do núcleo selecionado. A lista detalhada de imports, constantes, seeds, duplicações e arquivos será anexada em arquivos de auditoria.

## Proposta conservadora após auditoria

Extrair funções do notebook 03 sem mudar seus corpos matemáticos; expandir formatação e adicionar documentação. Separar módulos por responsabilidade, conservar fontes de referência para testes, gerar pequeno fixture RSM com o procedimento original, comparar valores/ordem/status/contadores contra as funções originais e um checkpoint histórico. Instalar apenas dependências necessárias em ambiente limpo. Manter parâmetros literais críticos quando centralizá-los ampliar o risco; inventariá-los em PARAMETERS.md. Nunca executar campanhas FULL.

## Estado

Consolidação técnica da candidata rc2 concluída. Divergências com a dissertação permanecem registradas mesmo após a escolha do notebook 03. Não declarar pronta para protocolo nem gerar hash definitivo enquanto houver pendências de alinhamento metodológico/documental e institucional.

## Impacto medido da normalização

Foi executada uma comparação auditável mantendo seleção, combinações, betas, starts, solver e tolerâncias iguais; somente a escala do NBI local mudou. A normalização local recalcula ideal/amplitude na payoff reduzida. A global usa ideal/amplitude da payoff completa, restritos à combinação.

| Fixture | Candidatos | Decisões iguais até 1e-8 | Distância mediana em x | Distância máxima em x | Pareto exato local/global | Pós-processado padrão local/global | Aceitos local/global |
|---|---:|---:|---:|---:|---:|---:|---:|
| m4_low seed103 | 386 | 215 | 0,0000 | 0,2822 | 309 / 314 | 285 / 290 | 386 / 386 |
| m6_medium seed101 | 2.045 | 369 | 0,0455 | 0,3537 | 1.045 / 1.043 | 921 / 919 | 2.045 / 2.045 |
| m12_high seed101 | 1.706 | 142 | 0,0082 | 2,8062 | 667 / 649 | 546 / 528 | 1.706 / 1.705 |

Conclusão: as escalas não são equivalentes; alteram soluções e cardinalidade, e no caso 12D alteraram uma convergência. A normalização local permanece padrão provisório por ser a fonte escolhida. A alternativa global não foi adicionada à API. Dados completos: `provenance/NORMALIZATION_IMPACT.json`.

## Registro de verificação da candidata

- Ambiente original Python 3.10.11: 16 testes passaram; exemplo mínimo passou.
- Primeira instalação limpa: NumPy 1.26.4 e SciPy 1.14.1 foram instalados, mas a instalação editável da candidata falhou em `bdist_wheel` porque Wheel não estava declarado. Os testes nesse ambiente não puderam importar `cnbi`. O exemplo ainda executou por inserir a raiz explicitamente no `sys.path`; isso não comprova instalação.
- Correção de infraestrutura: `wheel==0.45.1` foi acrescentado exclusivamente à seção de build. Nenhum corpo matemático foi alterado.
- A repetição em ambiente limpo, a instalação normal do wheel rc2 e seus resultados estão registrados em `VERIFICATION_REPORT.md`.
- O SMOKE original passou nos notebooks 01, 03, 02, 04 e 05; o 08 foi corretamente ignorado, e o 06 falhou pela divergência D16. Os notebooks 07 e seguintes da ordem não foram executados após a falha.
