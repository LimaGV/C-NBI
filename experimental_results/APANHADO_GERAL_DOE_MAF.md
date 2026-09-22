# Apanhado geral dos experimentos CNBI

## Organização correta dos resultados

Os resultados finais estão divididos em três análises independentes:

1. **DOE sintético:** comparação entre CNBI, VRF-NBI, NSGA-III e MOEA/D em 27 cenários, com 10 sementes. CNBI all não participa.
2. **Benchmark MaF:** avaliação final somente do CNBI nas funções MaF8, MaF9 e MaF13. Esse bloco não participa da ANOVA do DOE.
3. **Ablação:** comparação isolada entre CNBI spectral e CNBI all em nove cenários sintéticos contrastantes.

## Métodos avaliados

- **CNBI:** usa análise paralela para selecionar combinações de objetivos. A resolução é 20% para combinações com até quatro objetivos e 50% acima disso.
- **VRF-NBI:** implementação baseada no artigo, mantendo no mínimo dois fatores ou os fatores necessários para reter 90% da variação.
- **NSGA-III e MOEA/D:** algoritmos evolutivos com parâmetros calibrados. O limite depende do número de objetivos e fornece aproximadamente 400 gerações completas.
- **CNBI all:** usado somente na ablação, fora do DOE e do MaF final.

# DOE sintético

## Validade

- 27 cenários fatoriais completos.
- 10 sementes por cenário.
- Quatro métodos.
- 1.080 execuções concluídas.
- Nenhuma frente vazia.
- CNBI e VRF sem teto de avaliações.
- EAs com limites entre 50.000 e 400.400 avaliações.
- Frentes completas como resultado principal.
- Cardinalidade controlada como análise de sensibilidade, incluindo curvas com 2, 5, 10 e 20 pontos.

## Resultado principal: frentes completas

As dez sementes foram resumidas dentro de cada cenário. Portanto, a comparação estatística usa 27 cenários, e não trata as 270 execuções como problemas independentes.

| Método | Posto médio IGD | Posto médio HV | Melhor IGD | Melhor HV | Avaliações medianas | Tempo mediano (s) |
|---|---:|---:|---:|---:|---:|---:|
| CNBI | **1,04** | **1,22** | **26/27** | **22/27** | 12.031 | 1,13 |
| NSGA-III | 1,96 | 1,81 | 1/27 | 5/27 | 84.000 | 11,46 |
| MOEA/D | 3,48 | 3,04 | 0/27 | 0/27 | 84.000 | 56,00 |
| VRF-NBI | 3,52 | 3,93 | 0/27 | 0/27 | 1.095 | 0,39 |

IGD mede cobertura da fronteira e deve ser minimizado. HV mede volume coberto e deve ser maximizado. Nesta análise principal, a quantidade de soluções faz parte do resultado entregue por cada método.

## Sensibilidade à quantidade de pontos

A redução para o mínimo de cada bloco produziu a classificação anterior: CNBI venceu 20 cenários em IGD e apenas 3 em HV. Essa análise por vezes reduziu todos os métodos a 2–6 pontos, mudando bastante a pergunta prática.

As novas curvas usam quantidades fixas e só incluem um cenário/semente quando os quatro métodos têm pontos suficientes:

| Pontos | Blocos pareados | Cenários representados |
|---:|---:|---:|
| 2 | 270 | 27 |
| 5 | 260 | 26 |
| 10 | 135 | 16 |
| 20 | 50 | 8 |

Em IGD, o CNBI fica 6,1% acima do melhor com apenas 2 pontos e passa a apresentar a melhor mediana relativa de 5 a 20 pontos. Em HV, sua distância relativa para o melhor cai de 62,4% com 2 pontos para 3,8% com 20 pontos. Isso confirma que a principal vantagem do CNBI aparece quando o método pode entregar uma frente mais informativa. Não se estendeu a curva acima de 20 pontos porque nenhum bloco completo teria suporte dos quatro métodos.

## Interpretação por método

### CNBI

O CNBI apresentou a melhor cobertura geral. Nas frentes completas, teve o menor IGD em 26 dos 27 cenários e o maior HV em 22. Também usou bem menos avaliações que as EAs na execução típica. Seu GD não foi o menor, indicando que alguns pontos podem ficar mais afastados da fronteira mesmo quando a cobertura geral é boa.

### NSGA-III

A NSGA-III ficou em segundo lugar na avaliação combinada e em IGD. Sua qualidade em HV não apresentou diferença estatística clara em relação ao CNBI e ao MOEA/D. Exigiu mais avaliações e tempo que o CNBI.

### MOEA/D

O MOEA/D apresentou o menor GD em várias análises, mostrando boa proximidade individual de seus pontos. Nas frentes completas, porém, seu IGD e HV foram inferiores porque os pontos cobrem menos regiões da fronteira. Sua vantagem de HV aparece somente depois de comprimir todos os métodos a frentes muito pequenas.

### VRF-NBI

O VRF foi o método mais rápido e usou poucas avaliações. Entretanto, apresentou a pior nota combinada, pior cobertura e frentes geralmente pequenas. Foi significativamente inferior ao CNBI em IGD e HV. A implementação seguiu a regra de no mínimo dois fatores ou 90% de retenção; o problema é de desempenho nestes cenários, não de interrupção por orçamento.

## Testes entre métodos

- Diferença global em IGD: p = 5,15 × 10⁻⁹.
- Diferença global em HV: p = 0,0020.
- CNBI foi melhor que VRF, NSGA-III e MOEA/D em IGD.
- CNBI foi melhor que VRF em HV.
- Não houve diferença clara em HV entre CNBI, NSGA-III e MOEA/D.
- VRF e MOEA/D não apresentaram diferença clara em IGD.

## ANOVA do CNBI

O modelo usa dimensão, delta, dependência, todas as interações até a interação tripla e um bloco para a semente.

| Resposta | R² | R² ajustado | Erro médio do modelo |
|---|---:|---:|---:|
| IGD | 0,8979 | 0,8826 | 0,0171 |
| HV | 0,9739 | 0,9700 | 0,0330 |

A interação tripla foi relevante para IGD e HV. Isso significa que o efeito de dimensão depende simultaneamente de delta e dependência. Não existe uma regra única como “aumentar a dimensão sempre piora na mesma proporção”.

O VIF máximo foi 1,0 com contrastes ortogonais, portanto não apareceu problema de colinearidade. A interação tripla representa separadamente as 27 combinações do DOE; por isso, a falta de ajuste desse modelo completo não pode ser testada. O teste entre o modelo de interações duplas e o modelo triplo mostrou que a interação tripla não deve ser removida.

Os resíduos contêm alguns valores extremos. Uma checagem robusta a esses valores confirmou todos os efeitos experimentais. Mesmo assim, os tamanhos dos efeitos e os gráficos são mais informativos que p-valores extremamente pequenos.

Usar **m** no lugar de **delta** não é recomendado neste DOE. Como m = nx + delta + 1, nx e m não foram cruzados de maneira independente. O modelo com m teve pior R² ajustado e falta de ajuste significativa.

# Benchmark MaF final

## Validade

- MaF8, MaF9 e MaF13.
- 13 configurações de número de objetivos.
- 10 sementes.
- 130 execuções.
- Somente CNBI.
- Sem teto de avaliações.
- Nenhuma frente vazia.
- Separado do DOE e da comparação entre métodos.

| Caso | Pontos medianos | Avaliações medianas | IGD mediano | GD mediano | HV mediano |
|---|---:|---:|---:|---:|---:|
| MaF8, M=4 | 38 | 2.796 | 0,0780 | 0,0094 | 0,3232 |
| MaF8, M=6 | 112 | 4.228 | 0,0685 | 0,0114 | 0,1512 |
| MaF8, M=8 | 212 | 7.478 | 0,0647 | 0,0123 | 0,0659 |
| MaF8, M=10 | 325 | 10.577 | 0,0574 | 0,0143 | 0,0282 |
| MaF8, M=15 | 489 | 20.310 | 0,0596 | 0,0161 | 0,0031 |
| MaF9, M=4 | 36 | 1.944 | 0,1288 | 0,0192 | 0,3901 |
| MaF9, M=6 | 91 | 2.996 | 0,0930 | 0,0142 | 0,2105 |
| MaF9, M=8 | 158 | 7.557 | 0,1003 | 0,0149 | 0,0913 |
| MaF9, M=10 | 293 | 17.752 | 0,0805 | 0,0172 | 0,0437 |
| MaF9, M=15 | 745 | 44.886 | 0,0699 | 0,0207 | 0,0059 |
| MaF13, M=8 | 18 | 21.395 | 0,3959 | 1,68 × 10⁶ | 0,3684 |
| MaF13, M=10 | 18 | 28.518 | 0,4249 | 1,99 × 10⁶ | 0,4040 |
| MaF13, M=15 | 18 | 46.963 | 0,4767 | 2,60 × 10⁶ | 0,5762 |

## MaF8 e MaF9

Os gráficos no espaço x e nas projeções dos objetivos mostram boa cobertura da região real. A quantidade de pontos aumenta com o número de objetivos. No MaF9, o IGD não melhora de forma perfeitamente monotônica, mas o resultado geral melhora entre M=4 e M=15.

O HV não deve ser comparado diretamente entre números diferentes de objetivos porque a dimensão do volume muda.

## MaF13

O MaF13 revelou uma limitação importante. O CNBI encontra alguns pontos próximos da fronteira real, mas também mantém soluções extremas muito afastadas. Por isso, o IGD parece apenas moderado enquanto o GD fica extremamente alto.

As métricas atuais já estavam normalizadas pela faixa teórica da fronteira real. A nova auditoria reproduziu exatamente esses valores: o GD alto não é falta de normalização. A distância mediana de cada ponto do CNBI à fronteira ficou entre 0,065 e 0,076, mas o percentil 95 ficou entre 5,84 milhões e 9,04 milhões; cerca de 36,1% dos pontos ficaram a mais de uma unidade normalizada. Assim, a mediana mostra um grupo próximo, enquanto a cauda extrema explica o GD médio.

A pequena frente final não é causada pelo orçamento. Para M=15, cada execução processou 228 subproblemas e aceitou 224 soluções. Depois da remoção de repetições, sobraram apenas 30 decisões diferentes; após remover dominadas, restaram de 17 a 19 pontos.

Isso ocorre porque os objetivos do quarto em diante no MaF13 têm a mesma equação. Diversas combinações de objetivos levam ao mesmo ponto x. A análise paralela encontrou dimensão efetiva igual a 2, coerente com a estrutura da fronteira, e o CNBI considerou combinações até k=3.

## Histórico MaF com todos os métodos

Existe uma campanha anterior com os quatro métodos, mas ela usou teto fixo de 50 mil e parâmetros anteriores das EAs. Seus resultados servem apenas como diagnóstico histórico.

| Método | Concluídas | Interrompidas pelo teto | IGD mediano exploratório | HV mediano exploratório |
|---|---:|---:|---:|---:|
| CNBI | 129 | 1 | 0,3352 | 0,0332 |
| VRF-NBI | 110 | 20 | 0,7999 | 0,0042 |
| NSGA-III | 20 | 110 | 0,7107 | 0,0033 |
| MOEA/D | 130 | 0 | 0,5840 | 0,0322 |

Esses números não sustentam uma comparação científica entre métodos. As políticas de parada são antigas e muitas execuções foram interrompidas. Conforme a metodologia adotada, a comparação entre métodos deve permanecer no DOE sintético.

# Ablação separada

A ablação usa nove cenários sintéticos contrastantes e 10 sementes. Cada nível de dimensão, excesso de objetivos e dependência aparece três vezes. O CNBI-all aparece somente aqui. Cada par reutiliza a mesma matriz payoff e os mesmos ótimos individuais do CNBI spectral, de modo que apenas o filtro de combinações muda.

| Cenário | Redução mediana de avaliações | Aumento mediano de IGD | Perda mediana de HV |
|---|---:|---:|---:|
| nx=2, M=4, dependência baixa | 16,0% | 0,0034 | 0,0049 |
| nx=2, M=6, dependência média | 25,7% | 0,0053 | 0,0051 |
| nx=2, M=8, dependência alta | 72,6% | 0,0058 | 0,0069 |
| nx=3, M=5, dependência alta | 94,7% | 0,0032 | 0,0053 |
| nx=3, M=7, dependência baixa | 46,1% | 0,0056 | 0,0096 |
| nx=3, M=9, dependência média | 70,5% | 0,0067 | 0,0072 |
| nx=5, M=7, dependência média | 96,7% | 0,0049 | 0,0111 |
| nx=5, M=9, dependência alta | 99,1% | 0,0133 | 0,0232 |
| nx=5, M=11, dependência baixa | 63,8% | 0,0037 | 0,0056 |

A redução mediana variou de 16,0% a 99,1%. O maior ganho apareceu em nx=5, M=9 e dependência alta, com aumento de IGD de 0,0133 e perda de HV de 0,0232. Nos outros oito casos, o aumento de IGD não passou de 0,0067 e a perda de HV não passou de 0,0111. A ablação mostra que o ganho depende bastante da estrutura e não sustenta uma taxa universal de economia.

# Conclusões gerais

1. O DOE sintético fornece evidência favorável ao CNBI, principalmente na cobertura medida por IGD.
2. MOEA/D apresenta pontos individualmente próximos e bom HV, mas cobertura inferior à do CNBI.
3. NSGA-III é o concorrente mais equilibrado depois do CNBI.
4. VRF é rápido, mas perde qualidade e cobertura nos cenários sintéticos.
5. MaF8 e MaF9 confirmam que o CNBI consegue representar frentes conhecidas com boa distribuição.
6. MaF13 expõe uma limitação real do CNBI: muitas soluções repetidas, poucos pontos finais e extremos afastados.
7. A comparação formal entre métodos deve usar o DOE sintético. O MaF final deve ser apresentado como benchmark específico do CNBI.
8. As frentes completas são o resultado principal; as curvas por cardinalidade mostram como a conclusão muda quando o usuário limita o número de alternativas.
