"""Execute the scientific notebooks sequentially in audited campaign modes."""
from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import threading
import time
import json
import csv
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


def execute_with_resource_monitor(path: Path, root_pid: int) -> tuple[int, float]:
    """Execute one notebook while sampling this runner and all descendants."""
    stop = threading.Event()
    peak = 0
    child_cpu_by_pid: dict[int, float] = {}

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
                    if process.pid != root_pid:
                        cpu = process.cpu_times()
                        child_cpu_by_pid[process.pid] = max(
                            child_cpu_by_pid.get(process.pid, 0.0), cpu.user + cpu.system
                        )
                except psutil.Error:
                    pass
            peak = max(peak, rss)

    monitor = threading.Thread(target=sample, daemon=True)
    monitor.start()
    try:
        nb = nbformat.read(path, as_version=4)
        NotebookClient(
            nb,
            timeout=None if os.environ.get("CNBI_MODE") == "FULL" else 7200,
            kernel_name="python3",
            resources={"metadata": {"path": str(ROOT)}},
        ).execute()
    finally:
        stop.set()
        monitor.join(timeout=2)
    return peak, sum(child_cpu_by_pid.values())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=["SCENARIO_AUDIT", "SMOKE", "PILOT", "FULL"], default="SMOKE"
    )
    parser.add_argument("--confirm-full", action="store_true")
    args = parser.parse_args()
    if args.mode == "FULL" and not args.confirm_full:
        raise RuntimeError("FULL requer --confirm-full após autorização explícita do usuário.")
    os.environ["CNBI_MODE"] = args.mode
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[key] = "1"
    peak_rss = 0
    descendant_cpu_seconds = 0.0
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    order = ORDER[:1] if args.mode == "SCENARIO_AUDIT" else ORDER
    for name in order:
        path = ROOT / "notebooks" / name
        if name == "04_analise_resultados.ipynb":
            os.environ["CNBI_PEAK_RSS_BYTES"] = str(peak_rss)
        notebook_peak, notebook_child_cpu = execute_with_resource_monitor(path, os.getpid())
        peak_rss = max(peak_rss, notebook_peak)
        descendant_cpu_seconds += notebook_child_cpu
        print(f"OK: {name}", flush=True)
        import gc
        gc.collect()
    if args.mode == "PILOT":
        tables = ROOT / "results" / "tables"
        tables.mkdir(parents=True, exist_ok=True)
        with (tables / "pilot_method_runs.csv").open(encoding="utf-8", newline="") as stream:
            method_rows = list(csv.DictReader(stream))
        with (ROOT / "results" / "tuning" / "tuning_all_results.csv").open(encoding="utf-8", newline="") as stream:
            tuning_rows = list(csv.DictReader(stream))
        reused = sum(str(row.get("checkpoint_reused", "false")).lower() == "true" for row in method_rows + tuning_rows)
        disk_bytes = sum(p.stat().st_size for base in (ROOT / "data", ROOT / "results") for p in base.rglob("*") if p.is_file() and "backups" not in p.parts)
        resource = {
            "schema_version": 2,
            "mode": args.mode,
            "end_to_end_wall_seconds": time.perf_counter() - started_wall,
            "runner_cpu_seconds": time.process_time() - started_cpu,
            "descendant_cpu_seconds": descendant_cpu_seconds,
            "total_cpu_seconds": time.process_time() - started_cpu + descendant_cpu_seconds,
            "method_wall_seconds_sum": sum(float(row.get("wall_seconds") or 0) for row in method_rows),
            "method_cpu_seconds_sum": sum(float(row.get("cpu_seconds") or 0) for row in method_rows),
            "peak_rss_bytes": peak_rss,
            "disk_bytes": disk_bytes,
            "cache_used": False,
            "checkpoints_reused": reused,
            "includes": ["scenario_generation", "deterministic_methods", "tuning", "evolutionary_runs", "notebook_04", "filtering", "equalization", "statistics", "runner_and_descendants"],
        }
        (tables / "pilot_end_to_end_resources.json").write_text(json.dumps(resource, indent=2), encoding="utf-8")
    if args.mode in {"PILOT", "FULL"}:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_run.py"), "--mode", args.mode],
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    main()
