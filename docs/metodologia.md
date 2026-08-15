# Metodologia

O estudo cruza `m={4,6,12}` com correlação estrutural alvo `{0.25,0.60,0.85}`. Cada objetivo verdadeiro é `f_j(x)=||x-a_j||²`, com âncoras distintas numa esfera interna e posto afim três. O ruído experimental é gaussiano e independente, calibrado por objetivo para R² alvo 0,95. Os métodos recebem exclusivamente o mesmo RSM quadrático ajustado.

A referência verdadeira é amostrada diretamente do casco convexo tridimensional das âncoras por tetraedralização e coordenadas baricêntricas; ela nunca é descoberta por algoritmo evolucionário. A análise paralela é somente a variante independente da v0. CNBI usa deltas adaptativos por cardinalidade da combinação. NBI direto é válido apenas para quatro objetivos; casos estruturalmente sobre-determinados são registrados como inválidos.

NSGA-III e MOEA/D são calibrados no cenário de correlação média com sementes 1–3 e congelados antes das sementes finais 101–110. O orçamento real do CNBI, incluindo payoff, define o teto de avaliações dos algoritmos evolucionários.
