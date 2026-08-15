"""Remove outputs, execution counts and personal absolute paths from notebooks."""
from __future__ import annotations

import re
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
PERSONAL = re.compile(r"[A-Za-z]:\\Users\\[^\\\"']+(?:\\[^\"'\n\r]*)?")


def sanitize(path: Path) -> None:
    nb = nbformat.read(path, as_version=4)
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
        cell.source = PERSONAL.sub("<CAMINHO_LOCAL_REMOVIDO>", cell.source)
    nbformat.write(nb, path)


if __name__ == "__main__":
    for notebook in sorted((ROOT / "notebooks").rglob("*.ipynb")):
        sanitize(notebook)
    print("Notebooks sanitizados.")
