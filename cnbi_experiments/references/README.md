# Referências e validação

Referência teórica: [Cheng et al. (2017)](https://link.springer.com/article/10.1007/s40747-017-0039-7), equações 16, 17 e 38–40. Código oficial consultado: [BIMK/PlatEMO](https://github.com/BIMK/PlatEMO/tree/d25e65d1ffba58dbf4d7e1b5259786187d12968a/PlatEMO/Problems/Multi-objective%20optimization/MaF), revisão registrada em `provenance.json`. Os três arquivos MATLAB são cópias de consulta, com avisos autorais intactos. Seu uso e redistribuição seguem os termos presentes nos próprios arquivos; não recebem automaticamente a licença MIT do núcleo CNBI.

A formulação Python foi confrontada com essas fontes. Os testes numéricos usam valores analíticos independentes: centro e cordas do polígono, distâncias a retas, região refletida do hexágono, equações escalares MaF13 e identidades na frente. **MATLAB/Octave não foi executado** nesta máquina; isso não é uma alegação de comparação entre runtimes.

MaF13: D=5, n=D no denominador da equação 39; x1,x2 em [0,1], demais em [-2,2]. Índices publicados J1={4}, J2={5}, J3={3}, J4={4,5}. M não determina D. O octante esférico descreve as três primeiras coordenadas; os objetivos restantes repetem a expressão não linear, não uma esfera M-dimensional.

MaF8/9: D=2, domínio [-10000,10000]^2 e polígono regular de raio 1. MaF8 mede distâncias a vértices; MaF9, a retas infinitas, com regiões proibidas refletidas. O teste de fronteira de região adota `inpolygon` inclusivo do PlatEMO; o texto do artigo sobre contornos merece ser citado com essa convenção explícita.

Amostras PA: área uniforme do polígono por triângulos congruentes para MaF8/9; área uniforme do octante esférico, invertida para o conjunto Pareto ligado, para MaF13. O suporte é normativo; a distribuição e a cardinalidade exata diferem da grade/UniformPoint do gerador de referência PlatEMO e estão declaradas.
