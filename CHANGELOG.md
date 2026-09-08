# Changelog

## 1.0.0rc2 — 2026-09-08

- mantidos 500 como padrão configurável para payoff e NBI;
- mantidos os sete starts normativos; uma sequência explícita permite alterar sua quantidade;
- mantidos âncoras exatas, warm start, baricêntrico, centro e oito resgates por padrão;
- candidatos brutos permanecem sempre disponíveis;
- adicionada etapa opcional para duplicatas e dominância, com tolerâncias configuráveis;
- separada semanticamente a fronteira estimada RSM da fronteira real fornecida externamente;
- quantificado o impacto da normalização local versus global sem adicionar a alternativa à API;
- ampliada a suíte de 13 para 16 testes.
- promovida a candidata para uma raiz Git limpa, com materiais locais excluídos;
- adicionados atributos de texto/binário e verificação automática pelo GitHub Actions;
- sanitizados caminhos pessoais nos inventários públicos, preservando os originais na área local ignorada.

## 1.0.0rc1 — 2026-09-08

- extraído o núcleo selecionado do notebook 03 para sete módulos Python;
- preservados corpos computacionais, constantes, ordem, seeds, tolerâncias e SLSQP;
- removida uma redefinição textualmente idêntica de `_nearest_weight_order`;
- separado o núcleo CNBI de VRF-NBI, NSGA-III, MOEA/D, métricas e plotting;
- adicionado filtro Pareto auxiliar extraído do notebook 04, sem acoplá-lo ao núcleo;
- adicionados testes estruturais, unitários, integração, determinismo e checkpoint histórico;
- adicionado exemplo mínimo sem funções verdadeiras;
- adicionadas rastreabilidade, auditoria, parâmetros, dependências/atribuições e inventários;
- fixado Wheel 0.45.1 como dependência de build após falha reproduzida em ambiente limpo;
- mantido o aviso MIT original sem decisão institucional de relicenciamento;
- hash definitivo deliberadamente não gerado.

Esta é uma refatoração conservadora do pipeline selecionado, não uma alegação de equivalência à v0 aplicada.
