# Metodologia

O estudo cruza `m={4,6,12}` com correlação estrutural alvo `{0.25,0.60,0.85}`. Cada objetivo verdadeiro é `f_j(x)=||x-a_j||²`, com âncoras distintas numa esfera interna e posto afim três. Uma busca determinística multi-início ajusta direções e normas, com penalidades explícitas de correlação, separação, posto e factibilidade. O ruído experimental é gaussiano e independente, calibrado por objetivo para R² alvo 0,95. Os métodos recebem exclusivamente o mesmo RSM quadrático ajustado.

A referência verdadeira reserva `m` posições para as âncoras e completa `N-m` pontos no casco convexo por tetraedralização e coordenadas baricêntricas; ela nunca é descoberta por algoritmo evolucionário. Ideal e nadir externos são analíticos, enquanto os três métodos NBI preservam a normalização pela payoff do RSM. A análise paralela é somente a variante independente da v0. CNBI usa deltas adaptativos por cardinalidade. NBI direto é válido apenas para quatro objetivos.

NBI direto, subproblemas CNBI e NBI fatorial chamam uma única função-base anchor-safe: maximização de `t`, igualdade e jacobianas analíticas, esfera, pesos em ordem de vizinho mais próximo, warm start, início baricêntrico, âncoras, centro e até oito resgates determinísticos. O VRF orienta cada fator para carga dominante positiva e testa invariância exata a inversão artificial de sinal.

NSGA-III e MOEA/D são calibrados no cenário de correlação média com sementes 1–3 e congelados antes das sementes finais 101–110. O orçamento real do CNBI, incluindo payoff, define o teto de avaliações dos algoritmos evolucionários.
