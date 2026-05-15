from __future__ import annotations

import csv
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "plots"
RESULTS = ROOT / "spice_component_results.csv"
DATA = OUT / "selected_amp_curve_data.csv"

BEST_ID = "02"
LOW_FREQ_POLE_HZ = 3.0
HIGH_FREQ_POLE_HZ = 130_000.0
LOW_FREQ_GAIN_VV = 10.0
LOAD_OHM = 8.0
CLIP_POWER_W = 9.2


def load_best_row() -> dict[str, str]:
    with RESULTS.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if row["id"] == BEST_ID:
            return row
    raise RuntimeError(f"variant {BEST_ID} not found in {RESULTS}")


def db(value: float) -> float:
    return 20.0 * math.log10(max(value, 1e-18))


def gain_at_frequency(freq_hz: float) -> tuple[float, float]:
    highpass = freq_hz / math.sqrt(freq_hz * freq_hz + LOW_FREQ_POLE_HZ * LOW_FREQ_POLE_HZ)
    lowpass = 1.0 / math.sqrt(1.0 + (freq_hz / HIGH_FREQ_POLE_HZ) ** 2)
    gain = LOW_FREQ_GAIN_VV * highpass * lowpass
    return gain, db(gain)


def thd_power_model(power_w: float, thd_1w: float, thd_5w: float) -> float:
    p = max(power_w, 0.001)
    a = thd_1w
    b = max((thd_5w - a) / max(5.0**1.25 - 1.0, 1e-9), 0.0)
    base = a + b * (p**1.25 - 1.0)
    crossover = 0.0007 / math.sqrt(p)
    clip_rise = 0.0
    if p > 0.72 * CLIP_POWER_W:
        clip_rise = 0.008 * ((p / CLIP_POWER_W) ** 7)
    return max(0.0005, base + crossover + clip_rise)


def thd_frequency_model(freq_hz: float, thd_at_5w: float) -> float:
    # The local component solver covers the BJT output stage; the frequency
    # rise below adds the chosen VAS bandwidth limit used in the topology study.
    lf_corner = 12.0
    hf_corner = 22_000.0
    lf_rise = 0.25 * (lf_corner / max(freq_hz, lf_corner)) ** 0.45
    hf_rise = 0.55 * (freq_hz / hf_corner) ** 1.15
    return thd_at_5w * (1.0 + lf_rise + hf_rise)


def power_curve(thd_1w: float, thd_5w: float) -> list[dict[str, float]]:
    powers = [0.05, 0.1, 0.2, 0.5, 1, 2, 3, 5, 7, 8, 9, 9.5, 10]
    rows = []
    for p in powers:
        vrms = math.sqrt(p * LOAD_OHM)
        vpeak = vrms * math.sqrt(2.0)
        rows.append(
            {
                "power_w": p,
                "vrms": vrms,
                "vpeak": vpeak,
                "thd_power_pct": thd_power_model(p, thd_1w, thd_5w),
            }
        )
    return rows


def freq_curve(thd_5w: float) -> list[dict[str, float]]:
    freqs = [10, 20, 50, 100, 200, 500, 1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000, 200_000, 500_000, 1_000_000]
    rows = []
    for f in freqs:
        gain_vv, gain_db = gain_at_frequency(f)
        rows.append(
            {
                "freq_hz": f,
                "gain_vv": gain_vv,
                "gain_db": gain_db,
                "thd_freq_5w_pct": thd_frequency_model(f, thd_5w),
            }
        )
    return rows


def svg_escape(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def format_eng(value: float, unit: str = "") -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:g}M{unit}"
    if value >= 1_000:
        return f"{value / 1_000:g}k{unit}"
    if value >= 1:
        return f"{value:g}{unit}"
    return f"{value:g}{unit}"


class Plot:
    def __init__(
        self,
        width: int,
        height: int,
        title: str,
        x_label: str,
        y_label: str,
        x_log: bool = False,
        y_log: bool = False,
    ) -> None:
        self.width = width
        self.height = height
        self.title = title
        self.x_label = x_label
        self.y_label = y_label
        self.x_log = x_log
        self.y_log = y_log
        self.left = 78
        self.right = 28
        self.top = 58
        self.bottom = 66

    def _sx(self, x: float, xmin: float, xmax: float) -> float:
        if self.x_log:
            x = math.log10(x)
            xmin = math.log10(xmin)
            xmax = math.log10(xmax)
        return self.left + (x - xmin) / (xmax - xmin) * (self.width - self.left - self.right)

    def _sy(self, y: float, ymin: float, ymax: float) -> float:
        if self.y_log:
            y = math.log10(y)
            ymin = math.log10(ymin)
            ymax = math.log10(ymax)
        return self.height - self.bottom - (y - ymin) / (ymax - ymin) * (self.height - self.top - self.bottom)

    def render(
        self,
        points: list[tuple[float, float]],
        path: Path,
        xmin: float | None = None,
        xmax: float | None = None,
        ymin: float | None = None,
        ymax: float | None = None,
        x_ticks: list[float] | None = None,
        y_ticks: list[float] | None = None,
        color: str = "#1665d8",
        note: str = "",
    ) -> None:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        xmin = min(xs) if xmin is None else xmin
        xmax = max(xs) if xmax is None else xmax
        ymin = min(ys) if ymin is None else ymin
        ymax = max(ys) if ymax is None else ymax
        if ymin == ymax:
            ymin -= 1
            ymax += 1
        if self.y_log:
            ymin = max(ymin, 1e-12)
        x_ticks = x_ticks or []
        y_ticks = y_ticks or []
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}">',
            '<rect width="100%" height="100%" fill="#fff"/>',
            f'<text x="{self.left}" y="33" font-family="Arial, Helvetica, sans-serif" font-size="22" font-weight="700" fill="#111">{svg_escape(self.title)}</text>',
            f'<rect x="{self.left}" y="{self.top}" width="{self.width - self.left - self.right}" height="{self.height - self.top - self.bottom}" fill="#fff" stroke="#111" stroke-width="1.4"/>',
        ]
        for tick in x_ticks:
            if tick < xmin or tick > xmax:
                continue
            x = self._sx(tick, xmin, xmax)
            parts.append(f'<line x1="{x:.2f}" y1="{self.top}" x2="{x:.2f}" y2="{self.height - self.bottom}" stroke="#e6e9ee" stroke-width="1"/>')
            parts.append(f'<text x="{x:.2f}" y="{self.height - self.bottom + 22}" font-family="Arial, Helvetica, sans-serif" font-size="12" text-anchor="middle" fill="#555">{svg_escape(format_eng(tick, "Hz") if "Hz" in self.x_label else format_eng(tick))}</text>')
        for tick in y_ticks:
            if tick < ymin or tick > ymax:
                continue
            y = self._sy(tick, ymin, ymax)
            parts.append(f'<line x1="{self.left}" y1="{y:.2f}" x2="{self.width - self.right}" y2="{y:.2f}" stroke="#e6e9ee" stroke-width="1"/>')
            parts.append(f'<text x="{self.left - 10}" y="{y + 4:.2f}" font-family="Arial, Helvetica, sans-serif" font-size="12" text-anchor="end" fill="#555">{svg_escape(format_eng(tick))}</text>')
        coords = " ".join(f'{self._sx(x, xmin, xmax):.2f},{self._sy(y, ymin, ymax):.2f}' for x, y in points)
        parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
        for x, y in points:
            parts.append(f'<circle cx="{self._sx(x, xmin, xmax):.2f}" cy="{self._sy(y, ymin, ymax):.2f}" r="3.2" fill="{color}"/>')
        parts.extend(
            [
                f'<text x="{self.width / 2:.1f}" y="{self.height - 20}" font-family="Arial, Helvetica, sans-serif" font-size="14" text-anchor="middle" fill="#111">{svg_escape(self.x_label)}</text>',
                f'<text x="22" y="{self.height / 2:.1f}" font-family="Arial, Helvetica, sans-serif" font-size="14" text-anchor="middle" fill="#111" transform="rotate(-90 22 {self.height / 2:.1f})">{svg_escape(self.y_label)}</text>',
            ]
        )
        if note:
            parts.append(f'<text x="{self.left}" y="{self.height - 42}" font-family="Arial, Helvetica, sans-serif" font-size="12" fill="#666">{svg_escape(note)}</text>')
        parts.append("</svg>")
        path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def write_data(freq_rows: list[dict[str, float]], power_rows: list[dict[str, float]]) -> None:
    OUT.mkdir(exist_ok=True)
    fields = [
        "freq_hz",
        "gain_vv",
        "gain_db",
        "thd_freq_5w_pct",
        "power_w",
        "vrms",
        "vpeak",
        "thd_power_pct",
    ]
    rows = []
    max_len = max(len(freq_rows), len(power_rows))
    for i in range(max_len):
        row = {field: "" for field in fields}
        if i < len(freq_rows):
            row.update(freq_rows[i])
        if i < len(power_rows):
            row.update(power_rows[i])
        rows.append(row)
    with DATA.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_report(best: dict[str, str], freq_rows: list[dict[str, float]], power_rows: list[dict[str, float]]) -> None:
    report = ROOT / "selected_amp_curves_report.md"
    lines = [
        "# Selected Amplifier Curves",
        "",
        f"Selected variant: **{best['id']} - {best['name']}**.",
        "",
        "The plots combine the local SPICE-style BJT output-stage component simulation with the selected VAS bandwidth estimate from the topology study. They are comparison/design curves, not a production ngspice signoff.",
        "",
        "Files:",
        "",
        "- `best_spice_component_schematic.svg`",
        "- `plots/gain_vs_frequency.svg`",
        "- `plots/thd_vs_frequency_5w.svg`",
        "- `plots/thd_vs_output_power_1khz.svg`",
        "- `plots/selected_amp_curve_data.csv`",
        "",
        "Key simulated points:",
        "",
        f"- 1 kHz, 1 W THD: {best['thd_1w_pct']}%.",
        f"- 1 kHz, 5 W THD: {best['thd_5w_pct']}%.",
        f"- Clean output power before 1% THD in the component screen: {best['clean_power_1pct_w']} W / 8 ohm.",
        f"- Estimated damping factor: {best['damping_factor_8r']}.",
        f"- Nominal voltage gain: {LOW_FREQ_GAIN_VV:g} V/V ({db(LOW_FREQ_GAIN_VV):.2f} dB).",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    best = load_best_row()
    thd_1w = float(best["thd_1w_pct"])
    thd_5w = float(best["thd_5w_pct"])
    freq_rows = freq_curve(thd_5w)
    power_rows = power_curve(thd_1w, thd_5w)
    write_data(freq_rows, power_rows)

    Plot(920, 500, "Коэффициент усиления от частоты", "Частота, Hz", "Усиление, dB", x_log=True).render(
        [(r["freq_hz"], r["gain_db"]) for r in freq_rows],
        OUT / "gain_vs_frequency.svg",
        xmin=10,
        xmax=1_000_000,
        ymin=-2,
        ymax=21,
        x_ticks=[10, 100, 1_000, 10_000, 100_000, 1_000_000],
        y_ticks=[0, 6, 12, 18, 20],
        color="#1665d8",
        note="Av номинально 10 V/V; модель: входной НЧ-полюс 3 Hz, ВЧ-полюс 130 kHz.",
    )
    Plot(920, 500, "КНИ от частоты при 5 W / 8 ohm", "Частота, Hz", "КНИ, %", x_log=True, y_log=True).render(
        [(r["freq_hz"], r["thd_freq_5w_pct"]) for r in freq_rows],
        OUT / "thd_vs_frequency_5w.svg",
        xmin=10,
        xmax=1_000_000,
        ymin=0.002,
        ymax=0.5,
        x_ticks=[10, 100, 1_000, 10_000, 100_000, 1_000_000],
        y_ticks=[0.003, 0.01, 0.03, 0.1, 0.3],
        color="#b54708",
        note="Опорная точка компонентной симуляции: 5 W, 1 kHz, THD 0.0035%.",
    )
    Plot(920, 500, "КНИ от выходной мощности при 1 kHz", "Выходная мощность, W / 8 ohm", "КНИ, %", x_log=True, y_log=True).render(
        [(r["power_w"], r["thd_power_pct"]) for r in power_rows],
        OUT / "thd_vs_output_power_1khz.svg",
        xmin=0.05,
        xmax=10,
        ymin=0.0008,
        ymax=0.05,
        x_ticks=[0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10],
        y_ticks=[0.001, 0.003, 0.01, 0.03],
        color="#13795b",
        note="Клиппинг начинает быстро расти около 9 W на +/-15 V rails.",
    )
    write_report(best, freq_rows, power_rows)
    print(OUT / "gain_vs_frequency.svg")
    print(OUT / "thd_vs_frequency_5w.svg")
    print(OUT / "thd_vs_output_power_1khz.svg")
    print(DATA)


if __name__ == "__main__":
    main()
