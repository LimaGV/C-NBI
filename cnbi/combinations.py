"""Extração conservadora do notebook 03. Ver TRACEABILITY.md e aviso MIT."""


import numpy as np
from itertools import product


def simplex_weights(k, delta):
    """Malha simplex original: product(range(p+1), repeat=k), soma p, dividida por p=round(1/delta). Retorna pesos na ordem lexicográfica original. Usar deltas normativos; a função original não valida divisibilidade."""
    p = round(1 / delta)
    return np.array([q for q in product(range(p + 1), repeat=k) if sum(q) == p], float) / p


def _nearest_weight_order(weights):
    """Ordena pesos por vizinho mais próximo a partir do índice zero; empate pelo índice. Retorna pares (índice original, beta). Entrada não vazia, sem aleatoriedade ou tolerância explícita."""
    weights = np.asarray(weights, float)
    remaining = list(range(len(weights)))
    order = [remaining.pop(0)]
    while remaining:
        last = weights[order[-1]]
        pick = min(remaining, key=lambda i: (float(np.linalg.norm(weights[i] - last)), i))
        remaining.remove(pick)
        order.append(pick)
    return [(i, weights[i]) for i in order]
