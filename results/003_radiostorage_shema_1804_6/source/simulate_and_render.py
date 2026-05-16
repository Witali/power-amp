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
R2_VALUE = 47000.0
R3_VALUE = 10000.0
RE_VT1_VALUE = 100.0
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


def write_text_lf(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")


def normalize_text_file(path: Path) -> None:
    if path.exists():
        write_text_lf(path, path.read_text(encoding="utf-8", errors="replace"))


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


def rect(x: float, y: float, width: float, height: float, klass: str = "wire") -> str:
    return f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" class="{klass}"/>'


def resistor_h(x1: float, y: float, x2: float, label: str) -> list[str]:
    w = x2 - x1
    body_w = min(76.0, max(48.0, w * 0.56))
    left = x1 + (w - body_w) / 2.0
    right = left + body_w
    body_h = 28.0
    return [
        line(x1, y, left, y),
        rect(left, y - body_h / 2.0, body_w, body_h),
        line(right, y, x2, y),
        text((x1 + x2) / 2, y - 26, label, 14, 700, "middle"),
    ]


def resistor_v(x: float, y1: float, y2: float, label: str, side: str = "right") -> list[str]:
    h = y2 - y1
    body_h = min(76.0, max(36.0, h * 0.62))
    top = y1 + (h - body_h) / 2.0
    bottom = top + body_h
    body_w = 28.0
    dx = 24 if side == "right" else -24
    anchor = "start" if side == "right" else "end"
    return [
        line(x, y1, x, top),
        rect(x - body_w / 2.0, top, body_w, body_h),
        line(x, bottom, x, y2),
        text(x + dx, (y1 + y2) / 2 + 5, label, 14, 700, anchor),
    ]


def capacitor_v(x: float, y1: float, y2: float, label: str, side: str = "right", positive: str | None = None) -> list[str]:
    mid = (y1 + y2) / 2
    dx = 28 if side == "right" else -28
    anchor = "start" if side == "right" else "end"
    parts = [
        line(x, y1, x, mid - 14),
        line(x - 24, mid - 14, x + 24, mid - 14),
        line(x - 24, mid + 14, x + 24, mid + 14),
        line(x, mid + 14, x, y2),
        text(x + dx, mid + 5, label, 14, 700, anchor),
    ]
    if positive == "top":
        parts.append(text(x - 34, mid - 30, "+", 18, 700, "middle"))
    elif positive == "bottom":
        parts.append(text(x - 34, mid + 40, "+", 18, 700, "middle"))
    return parts


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


def speaker_v(x: float, y1: float, y2: float, label: str) -> list[str]:
    top = y1 + 34
    bottom = y1 + 110
    return [
        line(x, y1, x, top),
        rect(x - 18, top, 36, bottom - top),
        poly([(x + 18, top + 8), (x + 76, top - 16), (x + 76, bottom + 16), (x + 18, bottom - 8)]),
        line(x, bottom, x, y2),
        text(x + 40, bottom + 46, label, 14, 700, "middle"),
    ]


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
        text(cx - 44, cy + 82, label, 14, 700, "middle"),
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
        text(cx - 44, cy + 82, label, 14, 700, "middle"),
    ]


def schematic_svg() -> str:
    body: list[str] = [
        text(42, 42, "Reconstructed shema-1804-6 BJT audio amplifier", 22, 700),
        text(42, 68, "GOST/ESKD-style UGO; standard passive values; load = 8 ohm", 13),
        line(300, 98, 965, 98),
        poly([(965, 90), (982, 98), (965, 106)], "wire"),
        text(1000, 104, "+12 V", 18, 700),
        '<circle cx="300" cy="98" r="5" class="node"/>',
        '<circle cx="460" cy="98" r="5" class="node"/>',
        '<circle cx="730" cy="98" r="5" class="node"/>',
        *capacitor_v(300, 98, 220, "C1 1000u", "left", "top"),
        *ground(300, 220),
        *resistor_v(460, 98, 190, "R1 2.4k"),
        line(460, 190, 460, 218),
        *diode_v(460, 218, 310, "VD1 KD521A"),
        *diode_v(460, 310, 402, "VD2 KD521A"),
        '<circle cx="460" cy="190" r="5" class="node"/>',

        *npn(700, 240, "VT2 KT817A"),
        line(730, 195, 730, 98),
        line(460, 190, 620, 190),
        line(620, 190, 620, 240),
        line(620, 240, 646, 240),
        line(730, 285, 730, 455),
        '<circle cx="730" cy="360" r="5" class="node"/>',
        '<circle cx="730" cy="430" r="5" class="node"/>',
        line(730, 360, 820, 360),

        *pnp(700, 500, "VT3 KT816A"),
        line(730, 545, 730, 610),
        *ground(730, 610),

        *capacitor_h(820, 360, 965, f"C2 {C2_VALUE_UF:g}u", "left"),
        line(965, 360, 1018, 360),
        *speaker_v(1018, 360, 540, "B1 8 ohm"),
        *ground(1018, 540),
        text(972, 334, "speaker", 14, 700),

        text(42, 532, "Input", 16, 700),
        line(42, 540, 96, 540),
        *capacitor_h(96, 540, 252, "C3 10u", "right"),
        line(252, 540, 306, 540),
        '<circle cx="306" cy="540" r="5" class="node"/>',
        *resistor_v(306, 540, 670, "R3 10k", "left"),
        *ground(306, 670),

        *npn(486, 540, "VT1 KT3102A"),
        line(306, 540, 432, 540),
        line(460, 402, 516, 402),
        line(516, 402, 516, 495),
        '<circle cx="516" cy="450" r="5" class="node"/>',
        line(516, 450, 620, 450),
        line(620, 450, 620, 500),
        line(620, 500, 646, 500),
        line(516, 585, 516, 610),
        *resistor_v(516, 610, 700, "R4 100", "right"),
        *ground(516, 700),

        *resistor_h(250, 430, 430, "R2 47k"),
        line(250, 430, 250, 500),
        line(250, 500, 306, 500),
        line(306, 500, 306, 540),
        line(430, 430, 430, 380),
        line(430, 380, 600, 380),
        line(600, 380, 600, 430),
        line(600, 430, 730, 430),
    ]
    return base_svg(1160, 760, body)


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
        *capacitor_v(300, 98, 220, "C1 1000u", "left", "top"),
        *ground(300, 220),

        *resistor_v(460, 98, 155, "R1A 560", "left"),
        '<circle cx="460" cy="155" r="5" class="node"/>',
        *resistor_v(460, 155, 218, "R1B 1.8k", "left"),
        '<circle cx="460" cy="218" r="5" class="node"/>',
        *diode_v(460, 218, 310, "VD1 KD521A"),
        *diode_v(460, 310, 402, "VD2 KD521A"),

        *capacitor_h(460, 155, 610, f"C4 {CBOOT_VALUE_UF:g}u", "left"),
        line(610, 155, 790, 155),
        line(790, 155, 790, 360),

        *npn(700, 240, "VT2 KT817A"),
        line(730, 195, 730, 98),
        line(460, 218, 620, 218),
        line(620, 218, 620, 240),
        line(620, 240, 646, 240),
        line(730, 285, 730, 455),
        '<circle cx="730" cy="360" r="5" class="node"/>',
        '<circle cx="730" cy="430" r="5" class="node"/>',
        '<circle cx="790" cy="360" r="5" class="node"/>',
        line(730, 360, 820, 360),

        *pnp(700, 500, "VT3 KT816A"),
        line(730, 545, 730, 610),
        *ground(730, 610),

        text(838, 390, "OUT", 13, 700),
        *capacitor_h(820, 360, 965, f"C2 {C2_VALUE_UF:g}u", "left"),
        line(965, 360, 1018, 360),
        *speaker_v(1018, 360, 540, "B1 8 ohm"),
        *ground(1018, 540),
        text(972, 334, "speaker", 14, 700),

        text(42, 532, "Input", 16, 700),
        line(42, 540, 96, 540),
        *capacitor_h(96, 540, 252, "C3 10u", "right"),
        line(252, 540, 306, 540),
        '<circle cx="306" cy="540" r="5" class="node"/>',
        *resistor_v(306, 540, 670, "R3 10k", "left"),
        *ground(306, 670),

        *npn(486, 540, "VT1 KT3102A"),
        line(306, 540, 432, 540),
        line(460, 402, 516, 402),
        line(516, 402, 516, 495),
        '<circle cx="516" cy="450" r="5" class="node"/>',
        line(516, 450, 620, 450),
        line(620, 450, 620, 500),
        line(620, 500, 646, 500),
        line(516, 585, 516, 610),
        *resistor_v(516, 610, 700, "R4 100", "right"),
        *ground(516, 700),

        *resistor_h(250, 430, 430, "R2 47k"),
        line(250, 430, 250, 500),
        line(250, 500, 306, 500),
        line(306, 500, 306, 540),
        line(430, 430, 430, 380),
        line(430, 380, 600, 380),
        line(600, 380, 600, 430),
        line(600, 430, 730, 430),
    ]
    return base_svg(1160, 760, body)


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
        write_text_lf(path, base_svg(self.width, self.height, body))


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
    normalize_text_file(log)
    if result.returncode != 0:
        tail = log.read_text(encoding="utf-8", errors="replace")[-4000:] if log.exists() else result.stdout
        raise RuntimeError(f"ngspice failed for {netlist}:\n{tail}")


def main_netlist() -> str:
    return f"""* Reconstructed RadioStorage shema-1804-6 single-supply BJT audio amplifier
* Original image: https://radiostorage.net/uploads/Image/schemes/18/shema-1804-6.png
* Load changed from the image's 4 ohm speaker to user's requested 8 ohm speaker.
* This tuned model uses Bf=100 for the input transistor and Bf=50 for the
* output transistors. R1/R2/R3/R4 are tuned for about 10 mA output-stage idle
* current and for the output emitter node to sit near half supply.

.options abstol=1n reltol=0.003 itl1=500 itl4=500
.temp 27

VCC vcc 0 12
VIN vin 0 DC 0 AC 1 SIN(0 {VIN_PEAK:g} 1k)

* Input coupling capacitor
C3 vin b_in 10u
R3 b_in 0 {R3_VALUE:g}

* DC feedback bias and voltage-amplifier transistor
R2 out b_in {R2_VALUE:g}
Q1 drive b_in e_vt1 KT3102A
R4 e_vt1 0 {RE_VT1_VALUE:g}

* Bias chain and complementary emitter follower
R1 vcc b_top {R1_VALUE:g}
D1 b_top d_mid KD521A
D2 d_mid drive KD521A
Q2 vcc b_top out KT817A
Q3 0 drive out KT816A

* Output coupling capacitor and speaker
C2 out load {C2_VALUE_UF:g}u
RLOAD load 0 8
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
op
print v(b_in) v(e_vt1) v(drive) v(b_top) v(out) v(load)
print i(vcc)
print @q1[ic] @q2[ic] @q3[ic]
ac dec 80 5 200k
wrdata ac_response.csv frequency vdb(load) vp(load)
tran 5u 60m 40m
wrdata transient_1khz.csv time v(vin) v(b_in) v(out) v(load)
quit
.endc

.end
"""


def sweep_netlist(freq: float, vin_peak: float, out_csv: str) -> str:
    return f"""* Transient sweep for reconstructed shema-1804-6 amplifier
.options abstol=1n reltol=0.003 itl1=500 itl4=500
.temp 27

VCC vcc 0 12
VIN vin 0 DC 0 SIN(0 {vin_peak:.8g} {freq:.8g})
C3 vin b_in 10u
R3 b_in 0 {R3_VALUE:g}
R2 out b_in {R2_VALUE:g}
Q1 drive b_in e_vt1 KT3102A
R4 e_vt1 0 {RE_VT1_VALUE:g}
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
C3 vin b_in 10u
R3 b_in 0 {R3_VALUE:g}
R2 out b_in {R2_VALUE:g}
Q1 drive b_in e_vt1 KT3102A
R4 e_vt1 0 {RE_VT1_VALUE:g}
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


def waveform_y_limit(max_abs: float, occupancy: float = 0.70) -> float:
    if max_abs <= 0:
        return 1.0
    target = max_abs / occupancy
    decade = 10 ** math.floor(math.log10(target))
    for step in [1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.5, 10.0]:
        limit = step * decade
        if limit >= target:
            return limit
    return 10.0 * decade


def scale_label(scale: float) -> str:
    if scale >= 10 or abs(scale - round(scale)) < 0.05:
        return f"{scale:.0f}"
    if scale >= 1:
        return f"{scale:.1f}".rstrip("0").rstrip(".")
    return f"{scale:.2g}"


def run_frequency_sweep() -> list[dict[str, float]]:
    SWEEP.mkdir(parents=True, exist_ok=True)
    freqs = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
    rows: list[dict[str, float]] = []
    for freq in freqs:
        tag = f"{int(freq):05d}hz"
        netlist = SWEEP / f"sweep_{tag}.cir"
        csv_path = SWEEP / f"sweep_{tag}.csv"
        log = SWEEP / f"sweep_{tag}.log"
        write_text_lf(netlist, sweep_netlist(freq, VIN_PEAK, csv_path.name))
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
        write_text_lf(netlist, square_netlist(freq, VIN_PEAK, csv_path.name))
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
    vin_raw = [row[3] for row in rows]
    load_max_abs = max(abs(v) for v in load)
    vin_max_abs = max(abs(v) for v in vin_raw)
    vin_scale = load_max_abs / vin_max_abs if vin_max_abs > 0 else 1.0
    vin = [value * vin_scale for value in vin_raw]
    max_abs = max(load_max_abs, max(abs(v) for v in vin))
    ymax = waveform_y_limit(max_abs)
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
        [("load output", points, "#1665d8"), (f"input x{scale_label(vin_scale)}", input_points, "#b54708")],
        PLOTS / f"square_response_{tag}.svg",
        0,
        duration_ms,
        -ymax,
        ymax,
        x_ticks,
        y_ticks,
    )


def render_sine_plot(csv_path: Path, output_svg: Path, title: str) -> None:
    rows = read_rows(csv_path)
    t0 = rows[0][0]
    duration_ms = 4.0
    time_ms = [(row[0] - t0) * 1000.0 for row in rows]
    vin_raw_mv = [row[3] * 1000.0 for row in rows]
    amp_out = [row[7] for row in rows]
    load = [row[9] for row in rows]
    amp_out_mean = sum(amp_out) / len(amp_out)
    load_mean = sum(load) / len(load)
    amp_out_mv = [(value - amp_out_mean) * 1000.0 for value in amp_out]
    load_mv = [(value - load_mean) * 1000.0 for value in load]
    output_max_abs = max(max(abs(value) for value in load_mv), max(abs(value) for value in amp_out_mv))
    vin_max_abs = max(abs(value) for value in vin_raw_mv)
    vin_scale = output_max_abs / vin_max_abs if vin_max_abs > 0 else 1.0
    vin_mv = [value * vin_scale for value in vin_raw_mv]
    visible_values = [
        value
        for t, values in zip(time_ms, zip(load_mv, amp_out_mv, vin_mv))
        if 0 <= t <= duration_ms
        for value in values
    ]
    max_abs = max(abs(value) for value in visible_values)
    ymax = waveform_y_limit(max_abs)
    y_ticks = [-ymax, -ymax / 2.0, 0, ymax / 2.0, ymax]
    Plot(
        920,
        520,
        title,
        "Time after 40 ms settling, ms",
        "AC voltage, mV",
    ).render(
        [
            ("amp out AC", list(zip(time_ms, amp_out_mv)), "#13795b"),
            ("load output", list(zip(time_ms, load_mv)), "#1665d8"),
            (f"input x{scale_label(vin_scale)}", list(zip(time_ms, vin_mv)), "#b54708"),
        ],
        output_svg,
        0,
        duration_ms,
        -ymax,
        ymax,
        [0, 1, 2, 3, 4],
        y_ticks,
    )


def render_outputs(sweep_rows: list[dict[str, float]], square_rows: list[dict[str, float]]) -> None:
    for folder in [SCHEMATIC, PLOTS]:
        folder.mkdir(parents=True, exist_ok=True)
    write_text_lf(SCHEMATIC / "reconstructed_amplifier.svg", schematic_svg())
    write_text_lf(SCHEMATIC / "reconstructed_amplifier_bootstrap.svg", bootstrap_schematic_svg())

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
    render_sine_plot(
        DATA / "transient_1khz.csv",
        PLOTS / "sine_response_1khz.svg",
        f"Sine-wave response, 1 kHz, Vin = {2 * VIN_PEAK * 1000:.1f} mVpp",
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
    op_e_vt1 = op.get("v(e_vt1)", float("nan"))
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
- `R2`: recognized as 6.2 kOhm in the image, then retuned to the common E24 value 47 kOhm for use with `R3 = 10 kOhm` and `R4 = 100 ohm`; connected from the output emitter node to the VT1 base in this model.
- `R3`: 10 kOhm VT1 base return.
- `R4`: 100 ohm VT1 emitter degeneration resistor.
- `C1`: 1000 uF supply decoupling.
- `C2`: {C2_VALUE_UF:g} uF output coupling capacitor for this recalculated run.
- `C3`: 10 uF input coupling capacitor.
- `B1`: speaker load, modeled as the requested 8 ohm load.

Passive parts use common value series: E24 for resistors and common electrolytic capacitor values for `C1`, `C2`, and `C3`.

## ngspice Check

The reconstructed model converged in ngspice. After adding `R4 = 100 ohm` in the VT1 emitter circuit, `R1` and `R2` were retuned for `R3 = 10 kOhm`, about half supply at `out`, and about 10 mA through the output stage.

Operating point from `data/ngspice.log`:

- `V(b_in)`: about {op_b_in:.3f} V
- `V(e_vt1)`: about {op_e_vt1:.3f} V
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
- `plots/sine_response_1khz.svg/png`: 1 kHz sine-wave transient plot.
- `plots/bootstrap_sine_response_1khz.svg/png`: 1 kHz sine-wave transient plot for the voltage-addition variant.
- `plots/*.svg/png`: generated plots.
"""
    write_text_lf(RESULT / "README.md", text_body)


def main() -> None:
    for folder in [DATA, PLOTS, SCHEMATIC, NETLISTS]:
        folder.mkdir(parents=True, exist_ok=True)
    write_text_lf(BASE_NETLIST, main_netlist())
    run_ngspice(BASE_NETLIST, DATA / "ngspice.log", DATA)
    sweep_rows = run_frequency_sweep()
    square_rows = run_square_responses()
    render_outputs(sweep_rows, square_rows)
    write_readme(sweep_rows, square_rows)


if __name__ == "__main__":
    main()
