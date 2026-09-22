"""Executa, em ordem, os notebooks da referência 8D.

A metodologia permanece integralmente nos notebooks. Este script apenas os
executa e permite que a consolidação comece depois das seis execuções.
"""

from pathlib import Path
import sys

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = (
    ROOT / "notebooks" / "09_referencia_8D_NSGAIII_MOEAD_checkpoint.ipynb",
    ROOT / "notebooks" / "10_consolidacao_referencia_8D.ipynb",
)


def execute(path: Path) -> None:
    print(f"EXECUTANDO {path.name}", flush=True)
    notebook = nbformat.read(path, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=None,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
    )
    client.execute()
    nbformat.write(notebook, path)
    print(f"CONCLUÍDO {path.name}", flush=True)


def main() -> int:
    for path in NOTEBOOKS:
        execute(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
