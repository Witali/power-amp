from __future__ import annotations

import csv
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "results" / "002_ngspice_rc_lowpass"
DATA = RESULT / "data"
PLOTS = RESULT / "plots"
SCHEMATIC = RESULT / "schematic"
SOURCE = RESULT / "source"


def read_table(path: Path) -> list[list[float]]:
    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append([float(part) for part in line.split()])
    return rows


def esc(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def text(x: float, y: float, body: object, size: int = 14, weight: int = 400, anchor: str = "start") -> str:
    return (
        f'<text x="{x:g}" y="{y:g}" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="#111">{esc(body)}</text>'
    )


def line(x1: float, y1: float, x2: float, y2: float, klass: str = "wire") -> str:
    return f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" class="{klass}"/>'


def poly(points: list[tuple[float, float]], klass: str = "wire") -> str:
    return '<polyline points="' + " ".join(f"{x:g},{y:g}" for x, y in points) + f'" class="{klass}"/>'


def base_svg(width: int, height: int, body: list[str]) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            "<defs>",
            "<style>",
            ".wire{stroke:#111;stroke-width:2.4;fill:none;stroke-linecap:round;stroke-linejoin:round}",
            ".thin{stroke:#9aa4b2;stroke-width:1.2;fill:none}",
            ".axis{stroke:#111;stroke-width:1.4;fill:none}",
            ".blue{stroke:#1665d8;stroke-width:3;fill:none;stroke-linecap:round;stroke-linejoin:round}",
            ".green{stroke:#13795b;stroke-width:3;fill:none;stroke-linecap:round;stroke-linejoin:round}",
            "</style>",
            "</defs>",
            '<rect width="100%" height="100%" fill="#fff"/>',
            *body,
            "</svg>",
        ]
    ) + "\n"


def schematic_svg() -> str:
    body = [
        text(42, 42, "RC Low-Pass Filter - ngspice Smoke Test", 24, 700),
        text(42, 70, "R1 = 1k, C1 = 100n, Rload = 100k, Vin = 1 V sine / AC 1", 14),
        '<circle cx="150" cy="250" r="42" class="wire"/>',
        line(150, 160, 150, 208),
        line(150, 292, 150, 360),
        text(104, 252, "Vin", 15, 700),
        text(139, 237, "+", 18, 700),
        text(142, 274, "-", 18, 700),
        line(150, 160, 288, 160),
        poly([(288, 160), (300, 160), (308, 147), (320, 173), (332, 147), (344, 173), (356, 147), (368, 173), (376, 160), (402, 160)]),
        text(320, 133, "R1 1k", 14, 700, "middle"),
        line(402, 160, 548, 160),
        '<circle cx="548" cy="160" r="4" fill="#111"/>',
        text(560, 154, "OUT", 15, 700),
        line(548, 160, 548, 224),
        line(526, 224, 570, 224),
        line(526, 248, 570, 248),
        line(548, 248, 548, 360),
        text(578, 242, "C1 100n", 14),
        line(660, 160, 660, 220),
        poly([(660, 220), (660, 232), (647, 240), (673, 252), (647, 264), (673, 276), (660, 284), (660, 320)]),
        line(660, 320, 660, 360),
        text(678, 266, "Rload 100k", 14),
        line(548, 160, 660, 160),
        line(150, 360, 660, 360),
        line(400, 360, 400, 392),
        line(372, 392, 428, 392),
        line(382, 406, 418, 406),
        line(392, 420, 408, 420),
        text(686, 362, "0", 14, 700),
    ]
    return base_svg(900, 500, body)


class Plot:
    def __init__(self, width: int, height: int, title: str, x_label: str, y_label: str, x_log: bool = False):
        self.width = width
        self.height = height
        self.title = title
        self.x_label = x_label
        self.y_label = y_label
        self.x_log = x_log
        self.left = 72
        self.right = 28
        self.top = 58
        self.bottom = 60

    def sx(self, x: float, xmin: float, xmax: float) -> float:
        if self.x_log:
            x, xmin, xmax = math.log10(x), math.log10(xmin), math.log10(xmax)
        return self.left + (x - xmin) / (xmax - xmin) * (self.width - self.left - self.right)

    def sy(self, y: float, ymin: float, ymax: float) -> float:
        return self.height - self.bottom - (y - ymin) / (ymax - ymin) * (self.height - self.top - self.bottom)

    def render(
        self,
        series: list[tuple[str, list[tuple[float, float]], str]],
        path: Path,
        xmin: float,
        xmax: float,
        ymin: float,
        ymax: float,
        x_ticks: list[float],
        y_ticks: list[float],
    ) -> None:
        body = [
            text(self.left, 34, self.title, 22, 700),
            f'<rect x="{self.left}" y="{self.top}" width="{self.width - self.left - self.right}" height="{self.height - self.top - self.bottom}" fill="#fff" stroke="#111" stroke-width="1.4"/>',
        ]
        for tick in x_ticks:
            x = self.sx(tick, xmin, xmax)
            body.append(line(x, self.top, x, self.height - self.bottom, "thin"))
            body.append(text(x, self.height - self.bottom + 22, f"{tick:g}", 12, 400, "middle"))
        for tick in y_ticks:
            y = self.sy(tick, ymin, ymax)
            body.append(line(self.left, y, self.width - self.right, y, "thin"))
            body.append(text(self.left - 10, y + 4, f"{tick:g}", 12, 400, "end"))
        for name, points, color in series:
            coords = " ".join(f"{self.sx(x, xmin, xmax):.2f},{self.sy(y, ymin, ymax):.2f}" for x, y in points)
            body.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round"/>')
            lx = self.width - 220
            ly = 82 + 24 * series.index((name, points, color))
            body.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 34}" y2="{ly}" stroke="{color}" stroke-width="3"/>')
            body.append(text(lx + 44, ly + 4, name, 13))
        body.append(text(self.width / 2, self.height - 18, self.x_label, 14, 400, "middle"))
        body.append(
            f'<text x="22" y="{self.height / 2:g}" font-family="Arial, Helvetica, sans-serif" font-size="14" '
            f'text-anchor="middle" fill="#111" transform="rotate(-90 22 {self.height / 2:g})">{esc(self.y_label)}</text>'
        )
        path.write_text(base_svg(self.width, self.height, body), encoding="utf-8")


def write_assets() -> None:
    for d in [SCHEMATIC, PLOTS, SOURCE]:
        d.mkdir(parents=True, exist_ok=True)

    (SCHEMATIC / "rc_lowpass.svg").write_text(schematic_svg(), encoding="utf-8")

    ac = read_table(DATA / "ac_response.csv")
    ac_gain = [(row[0], row[3]) for row in ac]
    ac_phase = [(row[0], row[4]) for row in ac]
    Plot(920, 500, "ngspice AC analysis: RC low-pass", "Frequency, Hz", "Gain dB / phase deg", True).render(
        [("gain, dB", ac_gain, "#1665d8"), ("phase, deg", ac_phase, "#b54708")],
        PLOTS / "ac_gain_phase.svg",
        10,
        1_000_000,
        -65,
        5,
        [10, 100, 1_000, 10_000, 100_000, 1_000_000],
        [-60, -40, -20, 0],
    )

    tran = read_table(DATA / "transient.csv")
    trans_in = [(row[0] * 1000.0, row[2]) for row in tran]
    trans_out = [(row[0] * 1000.0, row[3]) for row in tran]
    Plot(920, 500, "ngspice transient analysis: 1 kHz sine", "Time, ms", "Voltage, V").render(
        [("vin", trans_in, "#1665d8"), ("vout", trans_out, "#13795b")],
        PLOTS / "transient.svg",
        0,
        5,
        -1.2,
        1.2,
        [0, 1, 2, 3, 4, 5],
        [-1, -0.5, 0, 0.5, 1],
    )

    cutoff = 1.0 / (2.0 * math.pi * 1000.0 * 100e-9)
    readme = f"""# 002 ngspice RC Low-Pass

This result verifies that the project can use a real open-source SPICE backend.

Simulator:

- ngspice-46 console binary, installed locally under `local_tools/ngspice`.
- Runner: `tools/run_ngspice.ps1`.

Circuit:

- `Vin`: DC 0, AC 1, transient sine 1 V peak at 1 kHz
- `R1`: 1 kOhm
- `C1`: 100 nF
- `Rload`: 100 kOhm
- Ideal cutoff without load interaction: {cutoff:.1f} Hz

Files:

- `schematic/rc_lowpass.svg`
- `schematic/rc_lowpass.png`
- `plots/ac_gain_phase.svg`
- `plots/ac_gain_phase.png`
- `plots/transient.svg`
- `plots/transient.png`
- `data/ngspice.log`
- `data/ac_response.csv`
- `data/transient.csv`

Run again:

```powershell
.\\tools\\run_ngspice.ps1 -Netlist .\\spice_examples\\001_rc_lowpass\\rc_lowpass.cir -OutputDir .\\results\\002_ngspice_rc_lowpass\\data
python .\\spice_examples\\001_rc_lowpass\\generate_assets.py
.\\tools\\render_svg_png.ps1 -InputSvg .\\results\\002_ngspice_rc_lowpass\\schematic\\rc_lowpass.svg -OutputPng .\\results\\002_ngspice_rc_lowpass\\schematic\\rc_lowpass.png -Scale 2
.\\tools\\render_svg_png.ps1 -InputSvg .\\results\\002_ngspice_rc_lowpass\\plots\\ac_gain_phase.svg -OutputPng .\\results\\002_ngspice_rc_lowpass\\plots\\ac_gain_phase.png -Scale 2
.\\tools\\render_svg_png.ps1 -InputSvg .\\results\\002_ngspice_rc_lowpass\\plots\\transient.svg -OutputPng .\\results\\002_ngspice_rc_lowpass\\plots\\transient.png -Scale 2
```
"""
    (RESULT / "README.md").write_text(readme, encoding="utf-8")
    target = SOURCE / "generate_assets.py"
    target.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")


if __name__ == "__main__":
    write_assets()
    print(RESULT)
