from __future__ import annotations

import csv
import math
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve()
RESULT = SCRIPT.parents[1]
ROOT = SCRIPT.parents[3]
DATA = RESULT / "data"
BOOTSTRAP_DATA = DATA / "bootstrap"
PLOTS = RESULT / "plots"
SCHEMATIC = RESULT / "schematic"
NETLISTS = RESULT / "netlists"
NGSPICE = ROOT / "local_tools" / "ngspice" / "Spice64" / "bin" / "ngspice_con.exe"
RLOAD = 8.0
INPUT_SWING_SERIES_MVPP = (1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0)
VIN_SWING_MVPP = 2.0
if VIN_SWING_MVPP not in INPUT_SWING_SERIES_MVPP:
    raise ValueError("VIN_SWING_MVPP must be selected from the 1-2-5 input swing series")
VIN_PEAK = VIN_SWING_MVPP / 2000.0
C2_VALUE_UF = 4700.0
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
        for name, points, color in series:
            coords = " ".join(
                f"{self.sx(x, xmin, xmax):.2f},{self.sy(y, ymin, ymax):.2f}"
                for x, y in points
                if xmin <= x <= xmax and ymin <= y <= ymax
            )
            body.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round"/>')

        legend_w = max(190, max(len(name) for name, _, _ in series) * 7 + 74)
        legend_h = 18 + 26 * len(series)
        lx = self.width - self.right - legend_w - 16
        ly0 = 78
        body.append(
            f'<rect x="{lx - 12:g}" y="{ly0 - 16:g}" width="{legend_w:g}" height="{legend_h:g}" '
            'rx="4" ry="4" fill="#fff" fill-opacity="0.82" stroke="#111" stroke-width="1"/>'
        )
        for index, (name, _, color) in enumerate(series):
            ly = ly0 + 26 * index
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

def write_readme(sweep_rows: list[dict[str, float]], square_rows: list[dict[str, float]]) -> None:
    at_1k = min(sweep_rows, key=lambda row: abs(row["frequency_hz"] - 1000))
    square_1k = min(square_rows, key=lambda row: abs(row["frequency_hz"] - 1000))
    square_10k = min(square_rows, key=lambda row: abs(row["frequency_hz"] - 10000))
    transient = read_rows(BOOTSTRAP_DATA / "transient_1khz.csv")
    sine_vin = [row[3] for row in transient]
    sine_amp_out = [row[7] for row in transient]
    sine_load = [row[9] for row in transient]
    sine_headroom = min(min(sine_amp_out), 12.0 - max(sine_amp_out))
    op = read_operating_point(BOOTSTRAP_DATA / "ngspice.log")
    op_b_in = op.get("v(b_in)", float("nan"))
    op_e_vt1 = op.get("v(e_vt1)", float("nan"))
    op_drive = op.get("v(drive)", float("nan"))
    op_b_top = op.get("v(b_top)", float("nan"))
    op_out = op.get("v(out)", float("nan"))
    op_load = op.get("v(load)", float("nan"))
    op_q2_ma = abs(op.get("@q2[ic]", float("nan"))) * 1000.0
    op_q3_ma = abs(op.get("@q3[ic]", float("nan"))) * 1000.0
    op_supply_ma = abs(op.get("i(vcc)", float("nan"))) * 1000.0
    text_body = f"""# 003 RadioStorage shema-1804-6 Bootstrap Reconstruction

This folder contains a local reconstruction of the amplifier schematic from:

`https://radiostorage.net/uploads/Image/schemes/18/shema-1804-6.png`

Only the voltage-addition/bootstrap variant is kept here. The earlier no-bootstrap reconstruction was removed from the published schematic, plots, netlists, and main result data because this variant is now the working design.

## Recognized Circuit

- `VT1`: KT3102A NPN common-emitter voltage amplifier, `Bf = 100`.
- `VT2`: KT817A NPN upper emitter follower, `Bf = 50`.
- `VT3`: KT816A PNP lower emitter follower, `Bf = 50`.
- `VD1`, `VD2`: KD521A bias diodes between output transistor bases.
- `R1A`, `R1B`: split upper bias resistor, 560 ohm and 1.8 kOhm, with bootstrap drive applied to their junction.
- `R2`: recognized as 6.2 kOhm in the image, then retuned to the common E24 value 47 kOhm for use with `R3 = 10 kOhm` and `R4 = 100 ohm`; connected from the output emitter node to the VT1 base in this model.
- `R3`: 10 kOhm VT1 base return.
- `R4`: 100 ohm VT1 emitter degeneration resistor.
- `C1`: 1000 uF supply decoupling.
- `C2`: {C2_VALUE_UF:g} uF output coupling capacitor for this recalculated run.
- `C3`: 10 uF input coupling capacitor.
- `C4`: {CBOOT_VALUE_UF:g} uF bootstrap capacitor from the output emitter node to the `R1A`/`R1B` junction.
- `B1`: speaker load, modeled as the requested 8 ohm load.

Passive parts use common value series: E24 for resistors and common electrolytic capacitor values for `C1`, `C2`, `C3`, and `C4`.

## ngspice Check

The bootstrap model converged in ngspice. After adding `R4 = 100 ohm` in the VT1 emitter circuit, `R1A`, `R1B`, and `R2` were retuned for `R3 = 10 kOhm`, about half supply at `out`, and about 10 mA through the output stage.

Operating point from `data/bootstrap/ngspice.log`:

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

For a {VIN_SWING_MVPP:g} mVpp sine input, selected from the 1-2-5 input swing series:

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

Square-wave transient runs use the same {VIN_SWING_MVPP:g} mVpp input and show the load voltage after 60 ms of settling.

- 1 kHz: load swing about `{square_1k["load_pp_v"]:.3f} Vpp`.
- 10 kHz: load swing about `{square_10k["load_pp_v"]:.3f} Vpp`.

## Files

- `source/shema-1804-6.png`: original downloaded image.
- `schematic/reconstructed_amplifier_bootstrap.svg/png`: redrawn bootstrap/voltage-addition schematic using transistor symbols.
- `netlists/radiostorage_amp_bootstrap.cir`: main ngspice netlist.
- `data/bootstrap/ac_response.csv`: AC gain/phase data from ngspice.
- `data/bootstrap/transient_1khz.csv`: 1 kHz transient data from ngspice.
- `data/bootstrap/frequency_sweep.csv`: frequency sweep with power and THD estimates.
- `data/bootstrap/square/*.csv`: 1 kHz and 10 kHz square-wave transient data.
- `plots/bootstrap_*.svg/png`: generated plots for the voltage-addition variant.
"""
    write_text_lf(RESULT / "README.md", text_body)


def main() -> None:
    SCHEMATIC.mkdir(parents=True, exist_ok=True)
    write_text_lf(SCHEMATIC / "reconstructed_amplifier_bootstrap.svg", bootstrap_schematic_svg())


if __name__ == "__main__":
    main()
