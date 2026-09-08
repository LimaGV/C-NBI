# Parâmetros normativos e literais preservados

| Local | Parâmetro | Valor | Papel |
|---|---|---:|---|
| config | `ALPHA` | `2**0.75` | raio da esfera e bounds auxiliares |
| config | `DELTA_BY_K` | `2:.10, 3:.10, 4:.20, 5:.50` | resolução Simplex-Lattice |
| payoff | starts padrão | centro e `±0.99*ALPHA` nos três eixos (7) | multi-início determinístico; sequência explícita altera quantidade |
| payoff | SLSQP `ftol` | `1e-11` | parada do solver |
| payoff | SLSQP `maxiter` | padrão `500`, configurável | limite por start |
| payoff | factibilidade | `xᵀx≤ALPHA²+1e-7` | conjunto de resultados elegíveis |
| análise paralela | `nmc` | `2000` | réplicas padrão |
| análise paralela | seed | `777` | gerador local NumPy |
| análise paralela | percentil | `95` | limiar posicional |
| normalização global | amplitude degenerada | `≤1e-12 → 1` | denominador |
| dimensão efetiva | mínimo | `1` | `d=max(1,...)` |
| seleção | singular degenerado | `≤1e-12 → q=∞` | rejeição pelo teto |
| NBI local | amplitude mínima | `1e-12` | denominador |
| normal | sinal | `normal·(-mean(A))≥0` | orientação à origem |
| vértice | `np.isclose` | `atol=1e-12`, `rtol` padrão NumPy | detecção de beta unitário |
| t | bounds | `[-10,10]` | variável NBI e projeções |
| start | esfera tolerada | `ALPHA*(1+1e-10)` | descarte do start |
| start | projeção interna | `ALPHA*(1-1e-12)` | correção de roundoff |
| start | chave | arredondamento a 12 casas | eliminar starts repetidos |
| NBI SLSQP | `ftol` | `1e-10` | parada do solver |
| NBI SLSQP | `maxiter` | padrão `500`, configurável | limite por tentativa |
| aceitação | igualdade | `eq_inf≤1e-5` | candidato factível |
| aceitação | esfera | violação `≤1e-8` | candidato factível |
| resgate | máximo | padrão `8`, configurável | starts pseudoaleatórios adicionais |
| resgate | seed | `1000003 + 1009*combo_id + beta_id` | gerador local determinístico |
| resgate | raio | `ALPHA*U**(1/3)` | amostra uniforme em volume 3D |
| saída CNBI | pós-processamento | desligado no núcleo | candidatos brutos sempre preservados |
| duplicatas opcionais | tolerância | padrão `1e-5`, configurável | resolução de quantização de X |
| dominância opcional | tolerância | padrão `1e-10`, configurável; zero reproduz notebook 04 | banda de comparação Pareto |

Não se corrigiu nem generalizou qualquer literal. O `rtol` implícito de `np.isclose` foi mantido porque especificá-lo agora mudaria a definição original.
