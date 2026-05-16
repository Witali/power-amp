from __future__ import annotations

import subprocess
from pathlib import Path

from .common import NGSPICE, normalize_text_file


def run_ngspice(netlist: Path, log: Path, cwd: Path) -> None:
    if not NGSPICE.exists():
        raise SystemExit(f"ngspice not found: {NGSPICE}")
    result = subprocess.run(
        [str(NGSPICE), "-b", "-o", str(log), str(netlist)],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    normalize_text_file(log)
    if result.returncode != 0:
        tail = log.read_text(encoding="utf-8", errors="replace")[-4000:] if log.exists() else result.stdout
        raise RuntimeError(f"ngspice failed for {netlist}:\n{tail}")

