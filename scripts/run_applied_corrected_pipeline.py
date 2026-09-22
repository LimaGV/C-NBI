"""Executa EAs corrigidos e, depois, a comparação aplicada atualizada."""

from pathlib import Path
import shutil
import sys

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
EA_NOTEBOOK = ROOT / "notebooks" / "12_cenario_aplicado_EAs_orcamento_igual_corrigido.ipynb"
COMPARISON_NOTEBOOK = ROOT / "notebooks" / "11_comparacao_fronteiras_8D_corrigida.ipynb"
APPLIED_RESULTS = ROOT / "results" / "applied"
OLD_COMPARISON = APPLIED_RESULTS / "comparison_8d_corrected"


def execute(path: Path) -> None:
    print(f"EXECUTANDO {path.name}", flush=True)
    nb = nbformat.read(path, as_version=4)
    NotebookClient(
        nb,
        timeout=None,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
    ).execute()
    nbformat.write(nb, path)
    print(f"CONCLUÍDO {path.name}", flush=True)


def remove_previous_comparison() -> None:
    target = OLD_COMPARISON.resolve()
    expected = (APPLIED_RESULTS / "comparison_8d_corrected").resolve()
    if target != expected or target.parent != APPLIED_RESULTS.resolve():
        raise RuntimeError(f"Destino de remoção inesperado: {target}")
    if target.exists():
        shutil.rmtree(target)
    print(f"RESULTADOS ANTERIORES REMOVIDOS: {target}", flush=True)


def main() -> int:
    execute(EA_NOTEBOOK)
    remove_previous_comparison()
    execute(COMPARISON_NOTEBOOK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
