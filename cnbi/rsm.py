"""Extração conservadora do notebook 03. Ver TRACEABILITY.md e aviso MIT."""


import numpy as np


def z(x):
    """Vetor RSM de três fatores, dez termos na ordem original. Entrada x (3,); saída (10,). Sem tolerância ou iteração. Ver TRACEABILITY.md."""
    (x1, x2, x3) = np.asarray(x, float)
    return np.array([1, x1, x2, x3, x1 * x1, x2 * x2, x3 * x3, x1 * x2, x1 * x3, x2 * x3])


def dz(x):
    """Jacobiana analítica dos dez termos RSM. Entrada x (3,); saída (10,3). Mesma ordem de z; sem tolerância ou iteração."""
    (x1, x2, x3) = np.asarray(x, float)
    return np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [2 * x1, 0, 0], [0, 2 * x2, 0], [0, 0, 2 * x3], [x2, x1, 0], [x3, 0, x1], [0, x3, x2]])
