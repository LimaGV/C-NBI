"""Execute the scientific notebooks sequentially in SMOKE or PILOT mode."""
from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import threading
from pathlib import Path

import nbformat
import psutil
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
ORDER = [
    "01_geracao_cenarios_sinteticos.ipynb",
    "03_pipeline_CNBI_comparacoes.ipynb",
    "02_calibracao_NSGAIII_MOEAD.ipynb",
    "04_analise_resultados.ipynb",
]


def execute_with_resource_monitor(path: Path, root_pid: int) -> int:
    """Execute one notebook while sampling this runner and all descendants."""
    stop = threading.Event()
    peak = 0

    def sample() -> None:
        nonlocal peak
        root = psutil.Process(root_pid)
        while not stop.wait(0.25):
            processes = [root]
            try:
                processes.extend(root.children(recursive=True))
            except psutil.Error:
                pass
            rss = 0
            for process in processes:
                try:
                    rss += process.memory_info().rss
                except psutil.Error:
                    pass
            peak = max(peak, rss)

    monitor = threading.Thread(target=sample, daemon=True)
    monitor.start()
    try:
        nb = nbformat.read(path, as_version=4)
        NotebookClient(
            nb,
            timeout=7200,
            kernel_name="python3",
            resources={"metadata": {"path": str(ROOT)}},
        ).execute()
    finally:
        stop.set()
        monitor.join(timeout=2)
    return peak


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["SMOKE", "PILOT"], default="SMOKE")
    args = parser.parse_args()
    if args.mode == "FULL":
        raise RuntimeError("FULL requer confirmação explícita e não é aceito por este executor.")
    os.environ["CNBI_MODE"] = args.mode
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[key] = "1"
    peak_rss = 0
    for name in ORDER:
        path = ROOT / "notebooks" / name
        if name == "04_analise_resultados.ipynb":
            os.environ["CNBI_PEAK_RSS_BYTES"] = str(peak_rss)
        peak_rss = max(peak_rss, execute_with_resource_monitor(path, os.getpid()))
        print(f"OK: {name}", flush=True)
    if args.mode == "PILOT":
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_run.py"), "--mode", "PILOT"],
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    main()
