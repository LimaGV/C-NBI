# Política de avaliações

O CNBI e o VRF-NBI terminam todo o procedimento definido pelo método, sem teto
de avaliações. O total efetivamente usado continua sendo contado e gravado nos
resultados.

NSGA-III e MOEA/D têm limite porque poderiam continuar produzindo gerações sem
um ponto natural de parada. Por padrão, cada execução recebe o maior valor entre:

- 50.000 avaliações; e
- 400 gerações completas da maior população testada na calibração, que usa
  quatro divisões (`400 × C(M+3,4)`).

A regra se baseia na calibração FULL anterior, cujo caso mais pesado usou cerca
de 338 gerações. A margem de 400 gerações evita reduzir esse esforço quando o
número de objetivos aumenta e fornece o mesmo teto aos dois EAs para um mesmo
valor de M. O limite pode ser substituído por `--ea-budget`
em análises de sensibilidade, mas uma campanha final deve usar uma única regra
predefinida.
