"""Create a clean source archive exclusively from versioned Git files."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)
output = DIST / "CNBI-Synthetic-Benchmarks-source.zip"
subprocess.run(
    ["git", "archive", "--format=zip", f"--output={output}", "HEAD"],
    cwd=ROOT,
    check=True,
)
print(output)
