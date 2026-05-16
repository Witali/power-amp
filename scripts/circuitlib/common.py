from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
NGSPICE = PROJECT_ROOT / "local_tools" / "ngspice" / "Spice64" / "bin" / "ngspice_con.exe"

INPUT_SWING_SERIES_MVPP = (
    1.0,
    2.0,
    5.0,
    10.0,
    20.0,
    50.0,
    100.0,
    200.0,
    500.0,
    1000.0,
    2000.0,
    5000.0,
    10000.0,
    20000.0,
    50000.0,
)


def input_peak_from_swing_mvpp(swing_mvpp: float) -> float:
    if swing_mvpp not in INPUT_SWING_SERIES_MVPP:
        raise ValueError("Input swing must be selected from the 1-2-5 mVpp series")
    return swing_mvpp / 2000.0


def write_text_lf(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")


def normalize_text_file(path: Path) -> None:
    if path.exists():
        text = path.read_text(encoding="utf-8", errors="replace")
        write_text_lf(path, "\n".join(line.rstrip() for line in text.splitlines()))
