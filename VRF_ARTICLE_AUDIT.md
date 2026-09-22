# Auditoria da implementação VRF-NBI contra o artigo de Pereira et al. (2025)

## Conclusão

A implementação usada nos benchmarks MaF não reproduz o VRF-NBI apresentado no artigo. Ela preserva a análise fatorial, a rotação Varimax e a grade simplex-lattice, mas substitui a função VRF do artigo pelo escore fatorial direto. Essa diferença explica a geração de soluções válidas no espaço dos fatores que são dominadas no espaço dos objetivos originais.

## Comparação

| Etapa | Artigo | Implementação MaF atual | Avaliação |
|---|---|---|---|
| Padronização e análise fatorial | Padronização, decomposição e rotação Varimax | StandardScaler, PCA e FactorAnalyzer com Varimax | Compatível em propósito |
| Escore fatorial | Eq. 11: combinação das cargas usando a inversa de `LᵀL` | Transformação da biblioteca baseada em `solve(correlação, estrutura)`, com fallback por cargas | Diferente |
| Modelo do fator | Superfície de resposta quadrática ajustada ao escore, Eqs. 17-18 | No MaF, transformação direta dos objetivos em cada avaliação | Ausente |
| Objetivo usado no NBI | Eq. 21: distância quadrática do escore ao alvo mais variância do fator | Escore fatorial bruto | Diferença crítica |
| Utopia, nadir e payoff | Calculados com a função VRF e normalizados, Eqs. 21-26 | Calculados diretamente nos escores fatoriais | Diferente |
| Grade de pesos | Simplex-lattice com passo delta, Eqs. 27-28 | Simplex-lattice com resolução configurada | Compatível |
| Não dominância | Algoritmo 3 só adiciona solução não dominada e viável | A filtragem é feita depois de resolver os subproblemas | Resultado final filtrado, mas orçamento e trajetórias podem ser afetados |

## Evidência encontrada nos resultados

Nas 130 execuções MaF do VRF-NBI, 1.288 soluções foram aceitas pelo NBI reduzido. Apenas 20 eram repetidas; 606 eram dominadas nos objetivos originais. Restaram 662 pontos.

No exemplo MaF8, m=4, semente 102, as seis soluções eram diferentes. Uma delas tinha objetivos `[0, 1,414, 2, 1,414]` e dominava todas as outras. Outra tinha aproximadamente `[117,75, 118,74, 119,75, 118,77]`. O NBI aceitou ambas porque trabalhou com os escores fatoriais, não com a função de erro quadrático VRF definida no artigo.

Nesse mesmo exemplo, a transformação por `solve(correlação, estrutura)` produziu pesos de escore com magnitudes próximas de -1.990 e +1.773. A correlação era quase singular, mas não exatamente singular, então o fallback não foi acionado. Isso agravou a perda da ordem de preferência dos objetivos originais.

## Consequência científica

Os resultados atuais do VRF-NBI nos MaF avaliam uma extensão experimental baseada em escores fatoriais diretos. Eles não devem ser apresentados como reprodução do método de Pereira et al. nem usados como comparação final contra o VRF-NBI publicado.

Os resultados do CNBI, NSGA-III e MOEA/D não precisam ser refeitos por causa desse problema. Uma correção pode rerodar somente os braços VRF dos MaF e reconstruir as comparações com igual cardinalidade.

## Caminho para uma reprodução fiel nos MaF

1. Criar um DOE no espaço das variáveis de decisão de cada MaF.
2. Avaliar os objetivos originais nesse DOE e padronizá-los.
3. Calcular os escores pela fórmula do artigo e aplicar a rotação Varimax.
4. Ajustar uma superfície quadrática para cada escore e validar R² ajustado, R² predito e resíduos.
5. Definir alvo e variância de cada fator e construir `VRFi(x) = [Fator_i(x) - alvo_i]² + variância_i(x)`.
6. Construir utopia, nadir e payoff usando essas funções VRF normalizadas.
7. Executar o NBI, aceitando somente soluções viáveis e não dominadas.
8. Reavaliar as soluções nos objetivos MaF originais e refazer a comparação pareada.

A regra solicitada de pelo menos dois fatores ou 90% de retenção pode ser mantida, mas deve ser registrada como uma adaptação experimental, pois o artigo descreve um número predeterminado de fatores e depende da interpretação dos grupos de respostas.
