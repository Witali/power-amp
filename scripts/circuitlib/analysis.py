from __future__ import annotations

import math
from pathlib import Path


def read_rows(path: Path) -> list[list[float]]:
    rows: list[list[float]] = []
    for line_text in path.read_text(encoding="utf-8").splitlines():
        line_text = line_text.strip()
        if line_text:
            rows.append([float(part) for part in line_text.split()])
    return rows


def read_operating_point(path: Path) -> dict[str, float]:
    values: dict[str, float] = {}
    for line_text in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" not in line_text:
            continue
        key, value = line_text.split("=", 1)
        try:
            values[key.strip().lower()] = float(value.split()[0])
        except (IndexError, ValueError):
            continue
    return values


def rms(values: list[float]) -> float:
    return math.sqrt(sum(v * v for v in values) / len(values))


def harmonic_thd(times: list[float], values: list[float], freq: float, harmonics: int = 5) -> tuple[float, float]:
    mean = sum(values) / len(values)
    centered = [v - mean for v in values]
    amps: list[float] = []
    for n in range(1, harmonics + 1):
        s = 0.0
        c = 0.0
        for t, v in zip(times, centered):
            angle = 2.0 * math.pi * n * freq * t
            s += v * math.sin(angle)
            c += v * math.cos(angle)
        peak = 2.0 * math.sqrt(s * s + c * c) / len(centered)
        amps.append(peak / math.sqrt(2.0))
    fundamental = amps[0]
    if fundamental <= 1e-12:
        return 0.0, 0.0
    thd = math.sqrt(sum(a * a for a in amps[1:])) / fundamental * 100.0
    return thd, fundamental


def waveform_y_limit(max_abs: float, occupancy: float = 0.70) -> float:
    if max_abs <= 0:
        return 1.0
    return ceiling_125(max_abs / occupancy)


def ceiling_125(value: float) -> float:
    if value <= 0:
        return 1.0
    decade = 10 ** math.floor(math.log10(value))
    for step in [1.0, 2.0, 5.0, 10.0]:
        limit = step * decade
        if limit >= value:
            return limit
    return 10.0 * decade


def nearest_125_scale(value: float) -> float:
    if value <= 0:
        return 1.0
    decade = 10 ** math.floor(math.log10(value))
    candidates = [
        step * (10 ** exponent)
        for exponent in range(math.floor(math.log10(value)) - 1, math.floor(math.log10(value)) + 2)
        for step in [1.0, 2.0, 5.0]
    ]
    candidates.append(10.0 * decade)
    return min(candidates, key=lambda candidate: abs(math.log10(candidate / value)))


def scale_label(scale: float) -> str:
    if scale >= 10 or abs(scale - round(scale)) < 0.05:
        return f"{scale:.0f}"
    if scale >= 1:
        return f"{scale:.1f}".rstrip("0").rstrip(".")
    return f"{scale:.2g}"
