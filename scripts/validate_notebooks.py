"""Static validation for every versioned notebook."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
ABSOLUTE = re.compile(r"(?:[A-Za-z]:[\\/](?:Users|Documents)|/home/|/Users/)", re.I)
errors: list[str] = []

for path in sorted((ROOT / "notebooks").rglob("*.ipynb")):
    try:
        nb = nbformat.read(path, as_version=4)
        nbformat.validate(nb)
    except Exception as exc:
        errors.append(f"{path}: formato inválido: {exc}")
        continue
    for i, cell in enumerate(nb.cells):
        if cell.cell_type == "code":
            if cell.get("outputs"):
                errors.append(f"{path}: célula {i} contém output")
            if cell.get("execution_count") is not None:
                errors.append(f"{path}: célula {i} contém execution_count")
        if ABSOLUTE.search(cell.source):
            errors.append(f"{path}: célula {i} contém caminho pessoal/absoluto")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print("Validação estática OK.")
