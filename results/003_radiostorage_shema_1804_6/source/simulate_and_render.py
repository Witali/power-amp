from __future__ import annotations

import csv
import math
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve()
RESULT = SCRIPT.parents[1]
ROOT = SCRIPT.parents[3]
DATA = RESULT / "data"
PLOTS = RESULT / "plots"
SCHEMATIC = RESULT / "schematic"
NETLISTS = RESULT / "netlists"
SWEEP = DATA / "sweep"
SQUARE = DATA / "square"
NGSPICE = ROOT / "local_tools" / "ngspice" / "Spice64" / "bin" / "ngspice_con.exe"
BASE_NETLIST = NETLISTS / "radiostorage_amp_reconstructed.cir"
RLOAD = 8.0
VIN_PEAK = 0.001
C2_VALUE_UF = 4700.0
R1_VALUE = 2400.0
R2_VALUE = 6800.0
R3_VALUE = 10000.0
R1A_BOOT_VALUE = 560.0
R1B_BOOT_VALUE = 1800.0
CBOOT_VALUE_UF = 470.0


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


def poly(points: list[tuple[float, float]], klass: str = "wire", fill: str = "none") -> str:
    pts = " ".join(f"{x:g},{y:g}" for x, y in points)
    return f'<polyline points="{pts}" class="{klass}" fill="{fill}"/>'


def circle(cx: float, cy: float, r: float, klass: str = "wire") -> str:
    return f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" class="{klass}"/>'


def base_svg(width: int, height: int, body: list[str]) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            "<defs>",
            "<style>",
            ".wire{stroke:#111;stroke-width:2.6;fill:none;stroke-linecap:round;stroke-linejoin:round}",
            ".thin{stroke:#a7b0bd;stroke-width:1.2;fill:none;stroke-linecap:round;stroke-linejoin:round}",
            ".axis{stroke:#111;stroke-width:1.4;fill:none}",
            ".blue{stroke:#1665d8;stroke-width:3;fill:none;stroke-linecap:round;stroke-linejoin:round}",
            ".green{stroke:#13795b;stroke-width:3;fill:none;stroke-linecap:round;stroke-linejoin:round}",
            ".orange{stroke:#b54708;stroke-width:3;fill:none;stroke-linecap:round;stroke-linejoin:round}",
            ".node{fill:#111;stroke:none}",
            "</style>",
            "</defs>",
            '<rect width="100%" height="100%" fill="#fff"/>',
            *body,
            "</svg>",
        ]
    ) + "\n"


def resistor_h(x1: float, y: float, x2: float, label: str) -> list[str]:
    w = x2 - x1
    pts = [
        (x1, y),
        (x1 + w * 0.12, y),
        (x1 + w * 0.20, y - 14),
        (x1 + w * 0.32, y + 14),
        (x1 + w * 0.44, y - 14),
        (x1 + w * 0.56, y + 14),
        (x1 + w * 0.68, y - 14),
        (x1 + w * 0.80, y + 14),
        (x1 + w * 0.88, y),
        (x2, y),
    ]
    return [poly(pts), text((x1 + x2) / 2, y - 26, label, 14, 700, "middle")]


def resistor_v(x: float, y1: float, y2: float, label: str, side: str = "right") -> list[str]:
    h = y2 - y1
    pts = [
        (x, y1),
        (x, y1 + h * 0.12),
        (x - 14, y1 + h * 0.20),
        (x + 14, y1 + h * 0.32),
        (x - 14, y1 + h * 0.44),
        (x + 14, y1 + h * 0.56),
        (x - 14, y1 + h * 0.68),
        (x + 14, y1 + h * 0.80),
        (x, y1 + h * 0.88),
        (x, y2),
    ]
    dx = 24 if side == "right" else -24
    anchor = "start" if side == "right" else "end"
    return [poly(pts), text(x + dx, (y1 + y2) / 2 + 5, label, 14, 700, anchor)]


def capacitor_v(x: float, y1: float, y2: float, label: str, side: str = "right") -> list[str]:
    mid = (y1 + y2) / 2
    dx = 28 if side == "right" else -28
    anchor = "start" if side == "right" else "end"
    return [
        line(x, y1, x, mid - 14),
        line(x - 24, mid - 14, x + 24, mid - 14),
        line(x - 24, mid + 14, x + 24, mid + 14),
        line(x, mid + 14, x, y2),
        text(x + dx, mid + 5, label, 14, 700, anchor),
    ]


def capacitor_h(x1: float, y: float, x2: float, label: str, positive: str | None = None) -> list[str]:
    mid = (x1 + x2) / 2
    parts = [
        line(x1, y, mid - 14, y),
        line(mid - 14, y - 24, mid - 14, y + 24),
        line(mid + 14, y - 24, mid + 14, y + 24),
        line(mid + 14, y, x2, y),
        text(mid, y - 34, label, 14, 700, "middle"),
    ]
    if positive == "left":
        parts.append(text(mid - 30, y - 17, "+", 18, 700, "middle"))
    elif positive == "right":
        parts.append(text(mid + 30, y - 17, "+", 18, 700, "middle"))
    return parts


def diode_v(x: float, y1: float, y2: float, label: str) -> list[str]:
    mid = (y1 + y2) / 2
    return [
        line(x, y1, x, mid - 24),
        poly([(x - 22, mid - 24), (x + 22, mid - 24), (x, mid + 8), (x - 22, mid - 24)], "wire"),
        line(x - 22, mid + 14, x + 22, mid + 14),
        line(x, mid + 14, x, y2),
        text(x + 34, mid + 4, label, 14, 700),
    ]


def ground(x: float, y: float) -> list[str]:
    return [line(x, y, x, y + 14), line(x - 26, y + 14, x + 26, y + 14), line(x - 17, y + 27, x + 17, y + 27), line(x - 8, y + 40, x + 8, y + 40)]


def arrowhead(
    start: tuple[float, float],
    end: tuple[float, float],
    direction: str,
    fraction: float,
    length: float = 15,
    half_width: float = 5.5,
) -> str:
    sx, sy = start
    ex, ey = end
    vx = ex - sx
    vy = ey - sy
    mag = math.hypot(vx, vy)
    ux = vx / mag
    uy = vy / mag
    nx = -uy
    ny = ux
    tip = (sx + vx * fraction, sy + vy * fraction)
    if direction == "out":
        base = (tip[0] - ux * length, tip[1] - uy * length)
    else:
        base = (tip[0] + ux * length, tip[1] + uy * length)
    p1 = (base[0] + nx * half_width, base[1] + ny * half_width)
    p2 = (base[0] - nx * half_width, base[1] - ny * half_width)
    pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in [tip, p1, p2])
    return f'<polygon points="{pts}" fill="#111" stroke="none"/>'


def npn(cx: float, cy: float, label: str) -> list[str]:
    base_top = (cx - 16, cy - 24)
    base_bottom = (cx - 16, cy + 24)
    top = (cx + 30, cy - 45)
    bottom = (cx + 30, cy + 45)
    return [
        circle(cx, cy, 54),
        line(cx - 54, cy, cx - 16, cy),
        line(cx - 16, cy - 34, cx - 16, cy + 34),
        line(base_top[0], base_top[1], top[0], top[1]),
        line(base_bottom[0], base_bottom[1], bottom[0], bottom[1]),
        arrowhead(base_bottom, bottom, "out", 0.70),
        text(cx, cy + 82, label, 14, 700, "middle"),
    ]


def pnp(cx: float, cy: float, label: str) -> list[str]:
    base_top = (cx - 16, cy - 24)
    base_bottom = (cx - 16, cy + 24)
    top = (cx + 30, cy - 45)
    bottom = (cx + 30, cy + 45)
    return [
        circle(cx, cy, 54),
        line(cx - 54, cy, cx - 16, cy),
        line(cx - 16, cy - 34, cx - 16, cy + 34),
        line(base_top[0], base_top[1], top[0], top[1]),
        line(base_bottom[0], base_bottom[1], bottom[0], bottom[1]),
        arrowhead(base_top, top, "in", 0.42),
        text(cx, cy + 82, label, 14, 700, "middle"),
    ]


def schematic_svg() -> str:
    body: list[str] = [
        text(42, 42, "Reconstructed shema-1804-6 BJT audio amplifier", 22, 700),
        text(42, 68, "Layout redrawn close to the original; standard passive values; load = 8 ohm", 13),
        line(300, 98, 965, 98),
        poly([(965, 90), (982, 98), (965, 106)], "wire"),
        text(1000, 104, "+12 V", 18, 700),
        '<circle cx="300" cy="98" r="5" class="node"/>',
        '<circle cx="460" cy="98" r="5" class="node"/>',
        '<circle cx="730" cy="98" r="5" class="node"/>',
        *capacitor_v(300, 98, 220, "C1 1000u", "left"),
        text(272, 130, "+", 18, 700, "end"),
        *ground(300, 220),
        *resistor_v(460, 98, 190, "R1 2.4k"),
        line(460, 190, 460, 218),
        *diode_v(460, 218, 310, "VD1 KD521A"),
        *diode_v(460, 310, 402, "VD2 KD521A"),
        '<circle cx="460" cy="190" r="5" class="node"/>',
        '<circle cx="460" cy="402" r="5" class="node"/>',

        *npn(700, 240, "VT2 KT817A"),
        line(730, 195, 730, 98),
        line(460, 190, 646, 240),
        line(730, 285, 820, 360),

        *pnp(700, 500, "VT3 KT816A"),
        line(460, 402, 610, 402),
        line(610, 402, 646, 500),
        line(730, 455, 820, 360),
        line(730, 545, 730, 610),
        *ground(730, 610),

        '<circle cx="820" cy="360" r="5" class="node"/>',
        *capacitor_h(820, 360, 965, f"C2 {C2_VALUE_UF:g}u", "left"),
        line(965, 360, 1018, 360),
        *resistor_v(1018, 360, 540, "B1 8 ohm"),
        *ground(1018, 540),
        text(972, 334, "speaker", 14, 700),

        text(42, 482, "Input", 16, 700),
        line(42, 490, 96, 490),
        '<circle cx="96" cy="490" r="5" class="node"/>',
        *resistor_v(96, 490, 595, "R4 470k", "right"),
        *ground(96, 595),
        *capacitor_h(96, 490, 252, "C3 10u +"),
        line(252, 490, 306, 490),
        '<circle cx="306" cy="490" r="5" class="node"/>',
        *resistor_v(306, 490, 610, "R3 10k", "left"),
        *ground(306, 610),

        *npn(486, 490, "VT1 KT3102A"),
        line(306, 490, 432, 490),
        line(516, 445, 516, 402),
        line(516, 402, 460, 402),
        line(516, 535, 516, 620),
        *ground(516, 620),

        *resistor_h(306, 360, 430, "R2 6.8k"),
        line(306, 360, 306, 490),
        '<path d="M430 360 V424 H600 Q620 398 640 424 H820 V360" class="wire"/>',
    ]
    return base_svg(1100, 680, body)


def bootstrap_schematic_svg() -> str:
    body: list[str] = [
        text(42, 42, "Reconstructed shema-1804-6 BJT audio amplifier, bootstrap variant", 22, 700),
        text(42, 68, "Upper bias feed split; C4 adds output swing to the upper transistor bias node", 13),
        line(300, 98, 965, 98),
        poly([(965, 90), (982, 98), (965, 106)], "wire"),
        text(1000, 104, "+12 V", 18, 700),
        '<circle cx="300" cy="98" r="5" class="node"/>',
        '<circle cx="460" cy="98" r="5" class="node"/>',
        '<circle cx="730" cy="98" r="5" class="node"/>',
        *capacitor_v(300, 98, 220, "C1 1000u", "left"),
        text(272, 130, "+", 18, 700, "end"),
        *ground(300, 220),

        *resistor_v(460, 98, 155, "R1A 560", "left"),
        '<circle cx="460" cy="155" r="5" class="node"/>',
        *resistor_v(460, 155, 218, "R1B 1.8k", "left"),
        '<circle cx="460" cy="218" r="5" class="node"/>',
        *diode_v(460, 218, 310, "VD1 KD521A"),
        *diode_v(460, 310, 402, "VD2 KD521A"),
        '<circle cx="460" cy="402" r="5" class="node"/>',

        *capacitor_h(460, 155, 610, f"C4 {CBOOT_VALUE_UF:g}u", "left"),
        line(610, 155, 900, 155),
        line(900, 155, 900, 300),
        line(900, 300, 820, 300),
        line(820, 300, 820, 360),
        text(742, 146, "bootstrap", 13, 700, "middle"),

        *npn(700, 240, "VT2 KT817A"),
        line(730, 195, 730, 98),
        line(460, 218, 646, 240),
        line(730, 285, 820, 360),

        *pnp(700, 500, "VT3 KT816A"),
        line(460, 402, 610, 402),
        line(610, 402, 646, 500),
        line(730, 455, 820, 360),
        line(730, 545, 730, 610),
        *ground(730, 610),

        '<circle cx="820" cy="360" r="5" class="node"/>',
        *capacitor_h(820, 360, 965, f"C2 {C2_VALUE_UF:g}u", "left"),
        line(965, 360, 1018, 360),
        *resistor_v(1018, 360, 540, "B1 8 ohm"),
        *ground(1018, 540),
        text(972, 334, "speaker", 14, 700),

        text(42, 482, "Input", 16, 700),
        line(42, 490, 96, 490),
        '<circle cx="96" cy="490" r="5" class="node"/>',
        *resistor_v(96, 490, 595, "R4 470k", "right"),
        *ground(96, 595),
        *capacitor_h(96, 490, 252, "C3 10u +"),
        line(252, 490, 306, 490),
        '<circle cx="306" cy="490" r="5" class="node"/>',
        *resistor_v(306, 490, 610, "R3 10k", "left"),
        *ground(306, 610),

        *npn(486, 490, "VT1 KT3102A"),
        line(306, 490, 432, 490),
        line(516, 445, 516, 402),
        line(516, 402, 460, 402),
        line(516, 535, 516, 620),
        *ground(516, 620),

        *resistor_h(306, 360, 430, "R2 6.8k"),
        line(306, 360, 306, 490),
        '<path d="M430 360 V424 H600 Q620 398 640 424 H820 V360" class="wire"/>',
    ]
    return base_svg(1100, 680, body)


class Plot:
    def __init__(self, width: int, height: int, title: str, x_label: str, y_label: str, x_log: bool = False):
        self.width = width
        self.height = height
        self.title = title
        self.x_label = x_label
        self.y_label = y_label
        self.x_log = x_log
        self.left = 76
        self.right = 32
        self.top = 60
        self.bottom = 64

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
            text(self.left, 36, self.title, 22, 700),
            f'<rect x="{self.left}" y="{self.top}" width="{self.width - self.left - self.right}" height="{self.height - self.top - self.bottom}" fill="#fff" stroke="#111" stroke-width="1.4"/>',
        ]
        for tick in x_ticks:
            x = self.sx(tick, xmin, xmax)
            body.append(line(x, self.top, x, self.height - self.bottom, "thin"))
            label = f"{tick:g}" if tick < 1000 else f"{tick/1000:g}k"
            body.append(text(x, self.height - self.bottom + 23, label, 12, 400, "middle"))
        for tick in y_ticks:
            y = self.sy(tick, ymin, ymax)
            body.append(line(self.left, y, self.width - self.right, y, "thin"))
            body.append(text(self.left - 10, y + 4, f"{tick:g}", 12, 400, "end"))
        for index, (name, points, color) in enumerate(series):
            coords = " ".join(
                f"{self.sx(x, xmin, xmax):.2f},{self.sy(y, ymin, ymax):.2f}"
                for x, y in points
                if xmin <= x <= xmax and ymin <= y <= ymax
            )
            body.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round"/>')
            lx = self.width - 260
            ly = 88 + 26 * index
            body.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 36}" y2="{ly}" stroke="{color}" stroke-width="3"/>')
            body.append(text(lx + 46, ly + 5, name, 13))
        body.append(text(self.width / 2, self.height - 18, self.x_label, 14, 400, "middle"))
        body.append(
            f'<text x="22" y="{self.height / 2:g}" font-family="Arial, Helvetica, sans-serif" font-size="14" '
            f'text-anchor="middle" fill="#111" transform="rotate(-90 22 {self.height / 2:g})">{esc(self.y_label)}</text>'
        )
        path.write_text(base_svg(self.width, self.height, body), encoding="utf-8")


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
    if result.returncode != 0:
        tail = log.read_text(encoding="utf-8", errors="replace")[-4000:] if log.exists() else result.stdout
        raise RuntimeError(f"ngspice failed for {netlist}:\n{tail}")


def sweep_netlist(freq: float, vin_peak: float, out_csv: str) -> str:
    return f"""* Transient sweep for reconstructed shema-1804-6 amplifier
.options abstol=1n reltol=0.003 itl1=500 itl4=500
.temp 27

VCC vcc 0 12
VIN vin 0 DC 0 SIN(0 {vin_peak:.8g} {freq:.8g})
R4 vin 0 470k
C3 vin b_in 10u
R3 b_in 0 {R3_VALUE:g}
R2 out b_in {R2_VALUE:g}
Q1 drive b_in 0 KT3102A
R1 vcc b_top {R1_VALUE:g}
D1 b_top d_mid KD521A
D2 d_mid drive KD521A
Q2 vcc b_top out KT817A
Q3 0 drive out KT816A
C2 out load {C2_VALUE_UF:g}u
RLOAD load 0 {RLOAD:g}
C1 vcc 0 1000u

.model KD521A D(Is=2.5n Rs=1.8 N=1.85 Cjo=2p M=0.33 Bv=75 Ibv=5u Tt=4n)
.model KT3102A NPN(Is=2e-14 Bf=100 Br=6 Vaf=100 Var=20 Ikf=0.12 Ikr=0.02
+ Rc=1 Re=0.35 Rb=60 Cje=9p Cjc=4p Tf=0.4n Tr=35n)
.model KT817A NPN(Is=9e-14 Bf=50 Br=5 Vaf=70 Var=15 Ikf=3.0 Ikr=0.4
+ Rc=0.12 Re=0.06 Rb=2.5 Cje=140p Cjc=80p Tf=0.45u Tr=6u)
.model KT816A PNP(Is=1.1e-13 Bf=50 Br=5 Vaf=60 Var=15 Ikf=2.5 Ikr=0.35
+ Rc=0.14 Re=0.07 Rb=2.8 Cje=160p Cjc=90p Tf=0.55u Tr=7u)

.control
set noaskquit
tran {1.0 / (freq * 256.0):.10g} {24.0 / freq:.10g} {12.0 / freq:.10g} {1.0 / (freq * 256.0):.10g}
wrdata {out_csv} time v(load) v(vin)
quit
.endc
.end
"""


def square_netlist(freq: float, vin_peak: float, out_csv: str) -> str:
    period = 1.0 / freq
    rise = min(1e-6, period / 100.0)
    step = period / 512.0
    settle = 0.060
    cycles = 4.0
    stop = settle + cycles * period
    return f"""* Square-wave response for reconstructed shema-1804-6 amplifier
.options abstol=1n reltol=0.003 itl1=500 itl4=500
.temp 27

VCC vcc 0 12
VIN vin 0 DC 0 PULSE({-vin_peak:.8g} {vin_peak:.8g} 0 {rise:.8g} {rise:.8g} {period / 2.0:.8g} {period:.8g})
R4 vin 0 470k
C3 vin b_in 10u
R3 b_in 0 {R3_VALUE:g}
R2 out b_in {R2_VALUE:g}
Q1 drive b_in 0 KT3102A
R1 vcc b_top {R1_VALUE:g}
D1 b_top d_mid KD521A
D2 d_mid drive KD521A
Q2 vcc b_top out KT817A
Q3 0 drive out KT816A
C2 out load {C2_VALUE_UF:g}u
RLOAD load 0 {RLOAD:g}
C1 vcc 0 1000u

.model KD521A D(Is=2.5n Rs=1.8 N=1.85 Cjo=2p M=0.33 Bv=75 Ibv=5u Tt=4n)
.model KT3102A NPN(Is=2e-14 Bf=100 Br=6 Vaf=100 Var=20 Ikf=0.12 Ikr=0.02
+ Rc=1 Re=0.35 Rb=60 Cje=9p Cjc=4p Tf=0.4n Tr=35n)
.model KT817A NPN(Is=9e-14 Bf=50 Br=5 Vaf=70 Var=15 Ikf=3.0 Ikr=0.4
+ Rc=0.12 Re=0.06 Rb=2.5 Cje=140p Cjc=80p Tf=0.45u Tr=6u)
.model KT816A PNP(Is=1.1e-13 Bf=50 Br=5 Vaf=60 Var=15 Ikf=2.5 Ikr=0.35
+ Rc=0.14 Re=0.07 Rb=2.8 Cje=160p Cjc=90p Tf=0.55u Tr=7u)

.control
set noaskquit
tran {step:.10g} {stop:.10g} {settle:.10g} {step:.10g}
wrdata {out_csv} time v(vin) v(load) v(out)
quit
.endc
.end
"""


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


def run_frequency_sweep() -> list[dict[str, float]]:
    SWEEP.mkdir(parents=True, exist_ok=True)
    freqs = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
    rows: list[dict[str, float]] = []
    for freq in freqs:
        tag = f"{int(freq):05d}hz"
        netlist = SWEEP / f"sweep_{tag}.cir"
        csv_path = SWEEP / f"sweep_{tag}.csv"
        log = SWEEP / f"sweep_{tag}.log"
        netlist.write_text(sweep_netlist(freq, VIN_PEAK, csv_path.name), encoding="utf-8")
        run_ngspice(netlist, log, SWEEP)
        data = read_rows(csv_path)
        times = [row[0] for row in data]
        load = [row[3] for row in data]
        vin = [row[5] for row in data]
        load_rms = rms([v - sum(load) / len(load) for v in load])
        vin_rms = rms(vin)
        thd, fundamental_rms = harmonic_thd(times, load, freq)
        rows.append(
            {
                "frequency_hz": float(freq),
                "vin_rms_v": vin_rms,
                "vout_rms_v": load_rms,
                "fundamental_rms_v": fundamental_rms,
                "gain_v_v": load_rms / vin_rms if vin_rms else 0.0,
                "power_w": load_rms * load_rms / RLOAD,
                "thd_percent": thd,
            }
        )
    out = DATA / "frequency_sweep.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def run_square_responses() -> list[dict[str, float]]:
    SQUARE.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, float]] = []
    for freq in [1000.0, 10000.0]:
        tag = "1khz" if freq == 1000.0 else "10khz"
        netlist = SQUARE / f"square_response_{tag}.cir"
        csv_path = SQUARE / f"square_response_{tag}.csv"
        log = SQUARE / f"square_response_{tag}.log"
        netlist.write_text(square_netlist(freq, VIN_PEAK, csv_path.name), encoding="utf-8")
        run_ngspice(netlist, log, SQUARE)
        rows = read_rows(csv_path)
        vin = [row[3] for row in rows]
        load = [row[5] for row in rows]
        amp_out = [row[7] for row in rows]
        summary.append(
            {
                "frequency_hz": freq,
                "vin_pp_v": max(vin) - min(vin),
                "load_pp_v": max(load) - min(load),
                "load_min_v": min(load),
                "load_max_v": max(load),
                "amp_out_pp_v": max(amp_out) - min(amp_out),
            }
        )
    out = DATA / "square_response_summary.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)
    return summary


def render_square_plot(freq: float) -> None:
    tag = "1khz" if freq == 1000.0 else "10khz"
    rows = read_rows(SQUARE / f"square_response_{tag}.csv")
    t0 = rows[0][0]
    time_ms = [(row[0] - t0) * 1000.0 for row in rows]
    vin_scaled = [(row[0] - t0) * 1000.0 for row in rows]
    load = [row[5] for row in rows]
    vin = [row[3] * 50.0 for row in rows]
    max_abs = max(max(abs(v) for v in load), max(abs(v) for v in vin))
    ymax = max(0.25, math.ceil(max_abs * 12.0) / 10.0)
    duration_ms = 4.0 / freq * 1000.0
    if freq == 1000.0:
        x_ticks = [0, 1, 2, 3, 4]
    else:
        x_ticks = [0, 0.1, 0.2, 0.3, 0.4]
    y_ticks = [-ymax, -ymax / 2.0, 0, ymax / 2.0, ymax]
    points = list(zip(time_ms, load))
    input_points = list(zip(vin_scaled, vin))
    Plot(
        920,
        520,
        f"Square-wave response, {freq / 1000:g} kHz, Vin = {2 * VIN_PEAK * 1000:.1f} mVpp",
        "Time after 60 ms settling, ms",
        "Voltage, V",
    ).render(
        [("load output", points, "#1665d8"), ("input x50", input_points, "#b54708")],
        PLOTS / f"square_response_{tag}.svg",
        0,
        duration_ms,
        -ymax,
        ymax,
        x_ticks,
        y_ticks,
    )


def render_outputs(sweep_rows: list[dict[str, float]], square_rows: list[dict[str, float]]) -> None:
    for folder in [SCHEMATIC, PLOTS]:
        folder.mkdir(parents=True, exist_ok=True)
    (SCHEMATIC / "reconstructed_amplifier.svg").write_text(schematic_svg(), encoding="utf-8")
    (SCHEMATIC / "reconstructed_amplifier_bootstrap.svg").write_text(bootstrap_schematic_svg(), encoding="utf-8")

    ac = read_rows(DATA / "ac_response.csv")
    gain_points = [(row[0], row[4]) for row in ac]
    phase_points = [(row[0], row[6]) for row in ac]
    Plot(920, 520, "AC gain and phase, load = 8 ohm", "Frequency, Hz", "Gain dB / phase deg", True).render(
        [("gain, dB", gain_points, "#1665d8"), ("phase, deg", phase_points, "#b54708")],
        PLOTS / "gain_vs_frequency.svg",
        5,
        200000,
        -20,
        45,
        [10, 100, 1000, 10000, 100000],
        [-20, 0, 20, 40],
    )

    thd_points = [(row["frequency_hz"], row["thd_percent"]) for row in sweep_rows]
    max_thd = max(row["thd_percent"] for row in sweep_rows)
    thd_ymax = max(1.0, math.ceil(max_thd * 1.25))
    Plot(920, 520, f"THD vs frequency, Vin = {VIN_PEAK * 1000:.0f} mV peak", "Frequency, Hz", "THD, %", True).render(
        [("THD", thd_points, "#13795b")],
        PLOTS / "thd_vs_frequency.svg",
        20,
        20000,
        0,
        thd_ymax,
        [20, 50, 100, 1000, 10000, 20000],
        [0, thd_ymax / 4, thd_ymax / 2, thd_ymax * 3 / 4, thd_ymax],
    )

    power_points = [(row["frequency_hz"], row["power_w"] * 1000.0) for row in sweep_rows]
    max_power = max(y for _, y in power_points)
    power_ymax = max(10.0, math.ceil(max_power * 1.25 / 10.0) * 10.0)
    Plot(920, 520, f"Output power vs frequency, Vin = {VIN_PEAK * 1000:.0f} mV peak", "Frequency, Hz", "Power, mW into 8 ohm", True).render(
        [("Pout", power_points, "#1665d8")],
        PLOTS / "output_power_vs_frequency.svg",
        20,
        20000,
        0,
        power_ymax,
        [20, 50, 100, 1000, 10000, 20000],
        [0, power_ymax / 4, power_ymax / 2, power_ymax * 3 / 4, power_ymax],
    )
    for row in square_rows:
        render_square_plot(row["frequency_hz"])


def write_readme(sweep_rows: list[dict[str, float]], square_rows: list[dict[str, float]]) -> None:
    at_1k = min(sweep_rows, key=lambda row: abs(row["frequency_hz"] - 1000))
    square_1k = min(square_rows, key=lambda row: abs(row["frequency_hz"] - 1000))
    square_10k = min(square_rows, key=lambda row: abs(row["frequency_hz"] - 10000))
    transient = read_rows(DATA / "transient_1khz.csv")
    sine_vin = [row[3] for row in transient]
    sine_amp_out = [row[7] for row in transient]
    sine_load = [row[9] for row in transient]
    sine_headroom = min(min(sine_amp_out), 12.0 - max(sine_amp_out))
    op = read_operating_point(DATA / "ngspice.log")
    op_b_in = op.get("v(b_in)", float("nan"))
    op_drive = op.get("v(drive)", float("nan"))
    op_b_top = op.get("v(b_top)", float("nan"))
    op_out = op.get("v(out)", float("nan"))
    op_load = op.get("v(load)", float("nan"))
    op_q2_ma = abs(op.get("@q2[ic]", float("nan"))) * 1000.0
    op_q3_ma = abs(op.get("@q3[ic]", float("nan"))) * 1000.0
    op_supply_ma = abs(op.get("i(vcc)", float("nan"))) * 1000.0
    text_body = f"""# 003 RadioStorage shema-1804-6 Reconstruction

This folder contains a local reconstruction of the amplifier schematic from:

`https://radiostorage.net/uploads/Image/schemes/18/shema-1804-6.png`

## Recognized Circuit

- `VT1`: KT3102A NPN common-emitter voltage amplifier, `Bf = 100`.
- `VT2`: KT817A NPN upper emitter follower, `Bf = 50`.
- `VT3`: KT816A PNP lower emitter follower, `Bf = 50`.
- `VD1`, `VD2`: KD521A bias diodes between output transistor bases.
- `R1`: recognized as 180 ohm in the image, then tuned to the common E24 value 2.4 kOhm in this model.
- `R2`: recognized as 6.2 kOhm in the image, then tuned to the common E24 value 6.8 kOhm and connected from the output emitter node to the VT1 base in this model.
- `R3`: 10 kOhm VT1 base return.
- `R4`: recognized as the input potentiometer/load, modeled as 470 kOhm.
- `C1`: 1000 uF supply decoupling.
- `C2`: {C2_VALUE_UF:g} uF output coupling capacitor for this recalculated run.
- `C3`: 10 uF input coupling capacitor.
- `B1`: speaker load, modeled as the requested 8 ohm load.

Passive parts use common value series: E24 for resistors and common electrolytic capacitor values for `C1`, `C2`, and `C3`.

## ngspice Check

The reconstructed model converged in ngspice. After moving `R2` from the upper bias/drive node to the output emitter node, this is a feedback-bias experiment rather than the earlier half-supply/10 mA tuning. The bias should be retuned if the target remains about half supply at `out` and about 10 mA through the output stage.

Operating point from `data/ngspice.log`:

- `V(b_in)`: about {op_b_in:.3f} V
- `V(drive)`: about {op_drive:.3f} V
- `V(b_top)`: about {op_b_top:.3f} V
- `V(out)`: about {op_out:.3f} V before output capacitor
- `V(load)`: about {op_load:.3f} V DC after output capacitor
- VT2 collector current: about {op_q2_ma:.2f} mA
- VT3 collector current: about {op_q3_ma:.2f} mA
- Total supply current in this simplified transistor model: about {op_supply_ma:.2f} mA

This no-emitter-resistor diode-biased output stage remains thermally sensitive; the current is very dependent on transistor and diode models.

## Key 1 kHz Result

For a {VIN_PEAK * 1000:.1f} mV peak sine input:

- Output power at 1 kHz into 8 ohm: `{at_1k["power_w"] * 1000:.4f} mW`
- Load RMS voltage at 1 kHz: `{at_1k["vout_rms_v"]:.3f} V`
- THD estimate at 1 kHz, harmonics 2-5 from ngspice transient data: `{at_1k["thd_percent"]:.3f} %`

## Non-Clipping Check

The selected transient input level is intentionally small so the simulated output does not clip.

- Sine input swing: `{max(sine_vin) - min(sine_vin):.4f} Vpp`.
- Output node before C2: `{min(sine_amp_out):.4f}..{max(sine_amp_out):.4f} V`.
- Rail headroom at that node: at least `{sine_headroom:.4f} V`.
- Speaker/load swing after C2: `{max(sine_load) - min(sine_load):.4f} Vpp`.

## Square-Wave Response

Square-wave transient runs use a {2 * VIN_PEAK * 1000:.1f} mVpp input and show the load voltage after 60 ms of settling.

- 1 kHz: load swing about `{square_1k["load_pp_v"]:.3f} Vpp`.
- 10 kHz: load swing about `{square_10k["load_pp_v"]:.3f} Vpp`.

## Files

- `source/shema-1804-6.png`: original downloaded image.
- `schematic/reconstructed_amplifier.svg/png`: redrawn schematic using transistor symbols.
- `schematic/reconstructed_amplifier_bootstrap.svg/png`: bootstrap/voltage-addition variant with split upper bias resistor and C4.
- `netlists/radiostorage_amp_reconstructed.cir`: main ngspice netlist.
- `data/ac_response.csv`: AC gain/phase data from ngspice.
- `data/transient_1khz.csv`: 1 kHz transient data from ngspice.
- `data/frequency_sweep.csv`: frequency sweep with power and THD estimates.
- `data/square/*.csv`: 1 kHz and 10 kHz square-wave transient data.
- `plots/*.svg/png`: generated plots.
"""
    (RESULT / "README.md").write_text(text_body, encoding="utf-8")


def main() -> None:
    for folder in [DATA, PLOTS, SCHEMATIC, NETLISTS]:
        folder.mkdir(parents=True, exist_ok=True)
    run_ngspice(BASE_NETLIST, DATA / "ngspice.log", DATA)
    sweep_rows = run_frequency_sweep()
    square_rows = run_square_responses()
    render_outputs(sweep_rows, square_rows)
    write_readme(sweep_rows, square_rows)


if __name__ == "__main__":
    main()
