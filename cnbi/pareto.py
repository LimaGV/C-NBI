"""Filtro de dominância exata usado pelo notebook 04.

Esta função é infraestrutura de saída. O núcleo :func:`cnbi.core.cnbi` continua
retornando todos os candidatos, inclusive estados de falha identificados.
"""
import numpy as np


def nondominated(F, tol=0.0):
    """Retorna máscara não dominada para minimização e tolerância configurável.

    Com ``tol=0`` reproduz o notebook 04. Para ``tol>0``, aplica a regra da
    v0: outro ponto deve ser até ``tol`` pior em todas as coordenadas e mais
    de ``tol`` melhor em pelo menos uma. Pontos iguais não se dominam.
    """
    F=np.asarray(F,float); keep=np.ones(len(F),bool)
    for i in range(len(F)):
        if keep[i]: keep[i]=not np.any(np.all(F<=F[i]+tol,axis=1)&np.any(F<F[i]-tol,axis=1))
    return keep


def postprocess_frontier(
    X,
    F,
    *,
    remove_duplicates=True,
    remove_dominated=True,
    duplicate_tolerance=1e-5,
    dominance_tolerance=1e-10,
):
    """Filtra decisões e objetivos já avaliados sem modificar as entradas.

    ``F`` pode conter previsões RSM ou avaliações reais; o chamador determina
    qual fronteira está calculando. Duplicatas são agrupadas pela quantização
    de cada coordenada de X na resolução ``duplicate_tolerance``. Em cada
    grupo, permanece a menor soma de F, com índice original como desempate.

    Retorna dicionário com ``X``, ``F``, ``indices`` relativos à entrada e
    contagens de cada etapa. A função nunca é chamada automaticamente por
    :func:`cnbi.core.cnbi`.
    """
    X = np.asarray(X, float)
    F = np.asarray(F, float)
    if X.ndim != 2 or F.ndim != 2 or len(X) != len(F):
        raise ValueError('X e F precisam ser matrizes com o mesmo número de linhas')
    indices = np.arange(len(X))
    after_duplicates = len(indices)
    if remove_duplicates and len(indices):
        if duplicate_tolerance < 0:
            raise ValueError('duplicate_tolerance precisa ser não negativa')
        keys = X.copy() if duplicate_tolerance == 0 else np.round(X / duplicate_tolerance)
        order = np.lexsort((indices, F.sum(axis=1)))
        seen = set()
        chosen = []
        for position in order:
            key = tuple(keys[position])
            if key not in seen:
                seen.add(key)
                chosen.append(int(position))
        indices = np.asarray(sorted(chosen), dtype=int)
        after_duplicates = len(indices)
    if remove_dominated and len(indices):
        if dominance_tolerance < 0:
            raise ValueError('dominance_tolerance precisa ser não negativa')
        indices = indices[nondominated(F[indices], tol=dominance_tolerance)]
    return {
        'X': X[indices].copy(),
        'F': F[indices].copy(),
        'indices': indices,
        'input_count': len(X),
        'after_duplicates': after_duplicates,
        'output_count': len(indices),
        'remove_duplicates': bool(remove_duplicates),
        'remove_dominated': bool(remove_dominated),
        'duplicate_tolerance': float(duplicate_tolerance),
        'dominance_tolerance': float(dominance_tolerance),
    }
