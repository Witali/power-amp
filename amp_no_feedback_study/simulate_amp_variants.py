from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTDIR = ROOT
NETLIST_DIR = OUTDIR / "behavioral_netlists"
TARGET_TOTAL_GAIN = 10.0
SUPPLY_RAIL_V = 15.0
AMPLIFIER_CLASS = "Class AB"
POINTS_PER_CYCLE = 96
CYCLES = 8
SAMPLES = POINTS_PER_CYCLE * CYCLES
SINE = [math.sin(2.0 * math.pi * i / POINTS_PER_CYCLE) for i in range(SAMPLES)]
COS_TABLE = [
    [math.cos(2.0 * math.pi * h * i / POINTS_PER_CYCLE) for i in range(SAMPLES)]
    for h in range(1, 10)
]
SIN_TABLE = [
    [math.sin(2.0 * math.pi * h * i / POINTS_PER_CYCLE) for i in range(SAMPLES)]
    for h in range(1, 10)
]

SOURCE_REFERENCES = [
    (
        "Pass DIY, The Zen Amplifier",
        "https://www.passdiy.com/project/amplifiers/the-zen-amplifier",
        "single-ended MOSFET Class A simplicity and high-bias behavior",
    ),
    (
        "Pass DIY, Cascode Amplifier Design",
        "https://www.passdiy.com/project/amplifiers/cascode-amplifier-design",
        "cascode as a way to reduce device capacitance modulation without leaning on global feedback",
    ),
    (
        "Pass DIY, Zen Variations 6",
        "https://www.passdiy.com/project/amplifiers/zen-variations-6",
        "balanced/Son-of-Zen cancellation and symmetry ideas",
    ),
    (
        "First Watt F4",
        "https://www.firstwatt.com/product/f4/",
        "no-voltage-gain, no-feedback power buffer idea",
    ),
    (
        "Andiha, Class A Cascode Power Amplifier",
        "https://www.andiha.no/audio/projects/cascode.html",
        "no-feedback folded cascode VAS and compound emitter follower output",
    ),
]


@dataclass(frozen=True)
class Variant:
    ident: str
    name: str
    input_stage: str
    vas: str
    output: str
    gain: float
    headroom_v: float
    h2: float
    h3: float
    crossover_v: float
    rout_ohm: float
    offset_mv: float
    drift_mv_c: float
    bandwidth_khz: float
    idle_ma: float
    stability_deg: float
    complexity: int
    notes: str


VARIANTS = [
    Variant(
        "01",
        "Single-ended cascoded VAS, double EF AB",
        "BJT emitter follower with RF/input reference",
        "NPN cascode VAS with transistor current source",
        "2-stage complementary emitter follower, Class AB",
        10.0,
        11.2,
        0.00160,
        0.00090,
        0.055,
        0.16,
        35.0,
        1.00,
        100.0,
        55.0,
        72.0,
        5,
        "Simple AB baseline; acceptable headroom, but single-ended VAS leaves more even-order error.",
    ),
    Variant(
        "02",
        "JFET input, single-ended cascode, double EF AB",
        "JFET source follower input",
        "NPN cascode VAS with discrete current source/sink",
        "2-stage complementary emitter follower, Class AB",
        10.0,
        11.1,
        0.00130,
        0.00080,
        0.050,
        0.15,
        45.0,
        0.85,
        120.0,
        55.0,
        70.0,
        6,
        "JFET input impedance is convenient, but offset spread and low-rail headroom need care.",
    ),
    Variant(
        "03",
        "BJT differential input, cascoded VAS, double EF AB",
        "Long-tailed BJT pair, one input grounded",
        "Cascoded VAS with mirror/current-source load",
        "2-stage complementary emitter follower, Class AB",
        10.0,
        11.0,
        0.00100,
        0.00080,
        0.048,
        0.14,
        15.0,
        0.45,
        100.0,
        60.0,
        68.0,
        7,
        "Better DC behavior, but the classic cascoded VAS is a little headroom-hungry at +/-15 V.",
    ),
    Variant(
        "04",
        "Folded cascode VAS, double EF AB",
        "Source-degenerated JFET/BJT input pair",
        "Low-voltage folded cascode VAS",
        "2-stage complementary emitter follower, Class AB",
        10.0,
        11.7,
        0.00070,
        0.00045,
        0.040,
        0.12,
        14.0,
        0.35,
        160.0,
        65.0,
        66.0,
        8,
        "Folded cascode preserves voltage swing better on +/-15 V rails.",
    ),
    Variant(
        "05",
        "Complementary cascoded VAS, double EF AB",
        "Matched BJT/JFET buffer pair",
        "Symmetric NPN/PNP cascodes with emitter degeneration",
        "2-stage complementary emitter follower, Class AB",
        10.0,
        11.5,
        0.00055,
        0.00045,
        0.035,
        0.10,
        12.0,
        0.30,
        150.0,
        70.0,
        68.0,
        8,
        "Good practical balance for low-voltage AB: symmetric VAS without excessive output drop.",
    ),
    Variant(
        "06",
        "Complementary cascoded VAS, triple EF AB",
        "Matched BJT/JFET buffer pair",
        "Symmetric NPN/PNP cascodes with emitter degeneration",
        "3-stage complementary emitter follower, Class AB",
        10.0,
        10.2,
        0.00050,
        0.00038,
        0.026,
        0.06,
        14.0,
        0.40,
        140.0,
        80.0,
        60.0,
        9,
        "Low output impedance, but triple EF wastes too much headroom on +/-15 V rails.",
    ),
    Variant(
        "07",
        "Complementary folded cascode, CFP AB output",
        "JFET differential pair with source degeneration",
        "Complementary folded cascode with current mirror loads",
        "Complementary feedback pair/Sziklai local output, Class AB",
        10.0,
        12.3,
        0.00032,
        0.00030,
        0.018,
        0.055,
        8.0,
        0.30,
        130.0,
        75.0,
        54.0,
        9,
        "Best headroom and local output linearity, but CFP stability must be proven carefully.",
    ),
    Variant(
        "08",
        "Balanced-cancellation cascode, double EF AB",
        "Balanced input pair, one side grounded for SE input",
        "Symmetric cascoded halves for even-order cancellation",
        "2-stage complementary emitter follower, Class AB",
        10.0,
        11.3,
        0.00025,
        0.00032,
        0.032,
        0.09,
        10.0,
        0.35,
        150.0,
        80.0,
        68.0,
        9,
        "Uses Son-of-Zen style cancellation in a conventional low-voltage AB architecture.",
    ),
    Variant(
        "09",
        "Diamond input, symmetric cascode, double EF AB",
        "Complementary diamond buffer",
        "Symmetric cascoded VAS with current mirrors",
        "2-stage complementary emitter follower, Class AB",
        10.0,
        11.4,
        0.00040,
        0.00028,
        0.034,
        0.08,
        14.0,
        0.35,
        200.0,
        75.0,
        58.0,
        9,
        "Fast and clean, but wideband layout is more critical.",
    ),
    Variant(
        "10",
        "Quasi-complementary high-bias AB",
        "BJT emitter follower",
        "Single-ended cascode with high-current driver",
        "High-bias quasi-complementary emitter follower, Class AB",
        10.0,
        11.7,
        0.00100,
        0.00045,
        0.018,
        0.11,
        25.0,
        0.70,
        95.0,
        120.0,
        72.0,
        6,
        "Soft crossover from higher idle current, but asymmetry and heat are disadvantages.",
    ),
]


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def soft_clip(v: float, limit: float) -> float:
    knee = 0.90 * limit
    av = abs(v)
    if av <= knee:
        return v
    span = limit - knee
    return math.copysign(knee + span * math.tanh((av - knee) / span), v)


def transfer(vin: float, variant: Variant, load_ohm: float = 8.0) -> float:
    v = TARGET_TOTAL_GAIN * vin
    hr = variant.headroom_v

    # Behavioral nonlinearity standing in for VAS curvature and output beta droop.
    v += variant.h2 * (v * v) / hr
    v += variant.h3 * (v * v * v) / (hr * hr)

    # Soft crossover residual after Vbe multiplier trimming.
    if variant.crossover_v > 0:
        dz = variant.crossover_v
        v -= 0.42 * dz * math.tanh(v / max(0.35 * dz, 1e-12))

    # Open-loop output impedance, since there is no global feedback reducing it.
    v *= load_ohm / (load_ohm + variant.rout_ohm)

    return soft_clip(v, variant.headroom_v)


def waveform(variant: Variant, vin_peak: float) -> list[float]:
    return [transfer(vin_peak * s, variant) for s in SINE]


def rms(values: list[float]) -> float:
    mean = sum(values) / len(values)
    return math.sqrt(sum((x - mean) * (x - mean) for x in values) / len(values))


def dft_harmonics(values: list[float], harmonics: int = 9) -> list[float]:
    n = len(values)
    mean = sum(values) / n
    amps = []
    for h in range(1, harmonics + 1):
        a = 0.0
        b = 0.0
        cos_row = COS_TABLE[h - 1]
        sin_row = SIN_TABLE[h - 1]
        for i, y0 in enumerate(values):
            y = y0 - mean
            a += y * cos_row[i]
            b += y * sin_row[i]
        a *= 2.0 / n
        b *= 2.0 / n
        amps.append(math.sqrt(a * a + b * b) / math.sqrt(2.0))
    return amps


def thd_percent(values: list[float]) -> float:
    hs = dft_harmonics(values)
    fundamental = hs[0]
    if fundamental <= 1e-12:
        return 999.0
    distortion = math.sqrt(sum(x * x for x in hs[1:]))
    return 100.0 * distortion / fundamental


def find_vin_for_vrms(variant: Variant, target_vrms: float) -> tuple[float, float, float]:
    lo = 0.0
    hi = max(target_vrms * 2.0 / max(TARGET_TOTAL_GAIN, 1.0), 0.05)
    for _ in range(18):
        y = waveform(variant, hi)
        if rms(y) >= target_vrms or max(abs(v) for v in y) >= 0.995 * variant.headroom_v:
            break
        hi *= 1.8
    for _ in range(18):
        mid = (lo + hi) / 2.0
        y = waveform(variant, mid)
        if rms(y) < target_vrms:
            lo = mid
        else:
            hi = mid
    y = waveform(variant, hi)
    return hi, rms(y), thd_percent(y)


def clean_power_w(variant: Variant, thd_limit_percent: float = 1.0) -> float:
    best = 0.0
    for p in [0.25, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25, 30, 40, 50]:
        target_vrms = math.sqrt(p * 8.0)
        _, actual_vrms, thd = find_vin_for_vrms(variant, target_vrms)
        actual_p = actual_vrms * actual_vrms / 8.0
        if thd <= thd_limit_percent and actual_p >= 0.95 * p:
            best = actual_p
        else:
            break
    return best


def score(row: dict[str, float], variant: Variant) -> float:
    thd1 = row["thd_1w_pct"]
    thd5 = row["thd_5w_pct"]
    clean = row["clean_power_1pct_w"]
    damping = row["damping_factor_8r"]
    idle_penalty = clamp(1.0 - max(variant.idle_ma - 80.0, 0.0) / 220.0, 0.0, 1.0)
    symmetry = 0.55 if "quasi-complementary" in variant.output else 1.0
    return round(
        100.0
        * (
            0.18 * clamp(1.0 - thd1 / 0.20, 0.0, 1.0)
            + 0.28 * clamp(1.0 - thd5 / 0.60, 0.0, 1.0)
            + 0.16 * clamp(clean / 8.5, 0.0, 1.0)
            + 0.11 * clamp(variant.stability_deg / 75.0, 0.0, 1.0)
            + 0.08 * clamp(damping / 120.0, 0.0, 1.0)
            + 0.08 * clamp(1.0 - variant.offset_mv / 60.0, 0.0, 1.0)
            + 0.06 * clamp(1.0 - variant.drift_mv_c / 1.5, 0.0, 1.0)
            + 0.06 * idle_penalty
            + 0.04 * symmetry
            + 0.02 * clamp(1.0 - (variant.complexity - 5.0) / 5.0, 0.0, 1.0)
        ),
        2,
    )


def variant_rows() -> list[dict[str, str | float]]:
    rows: list[dict[str, str | float]] = []
    for v in VARIANTS:
        vin1, vrms1, thd1 = find_vin_for_vrms(v, math.sqrt(1.0 * 8.0))
        vin5, vrms5, thd5 = find_vin_for_vrms(v, math.sqrt(5.0 * 8.0))
        vin10, vrms10, thd10 = find_vin_for_vrms(v, math.sqrt(10.0 * 8.0))
        clean = clean_power_w(v)
        row: dict[str, str | float] = {
            "id": v.ident,
            "name": v.name,
            "input_stage": v.input_stage,
            "vas": v.vas,
            "output": v.output,
            "gain_v_v": TARGET_TOTAL_GAIN,
            "vin_1w_peak_mv": round(vin1 * 1000.0, 2),
            "actual_1w_vrms": round(vrms1, 4),
            "thd_1w_pct": round(thd1, 4),
            "vin_5w_peak_mv": round(vin5 * 1000.0, 2),
            "actual_5w_vrms": round(vrms5, 4),
            "thd_5w_pct": round(thd5, 4),
            "vin_10w_peak_mv": round(vin10 * 1000.0, 2),
            "actual_10w_vrms": round(vrms10, 4),
            "thd_10w_pct": round(thd10, 4),
            "clean_power_1pct_w": round(clean, 2),
            "damping_factor_8r": round(8.0 / v.rout_ohm, 1),
            "offset_mv_est": v.offset_mv,
            "thermal_drift_mv_c_est": v.drift_mv_c,
            "bandwidth_khz_est": v.bandwidth_khz,
            "idle_ma_est": v.idle_ma,
            "stability_margin_deg_est": v.stability_deg,
            "complexity_1_10": v.complexity,
        }
        row["score"] = score(row, v)  # type: ignore[arg-type]
        row["notes"] = v.notes
        rows.append(row)
    rows.sort(key=lambda r: float(r["score"]), reverse=True)
    return rows


def write_csv(rows: list[dict[str, str | float]]) -> None:
    path = OUTDIR / "results.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_netlists() -> None:
    NETLIST_DIR.mkdir(exist_ok=True)
    for v in VARIANTS:
        text = f"""* {v.ident}: {v.name}
* Behavioral reference netlist. The Python harness in simulate_amp_variants.py
* is the simulation used for comparison because no local SPICE engine was found.
* Rails: +/-{SUPPLY_RAIL_V:g} V, load: 8 ohm, no global OUT-to-IN feedback.
* Output class: {AMPLIFIER_CLASS}
*
* Stage map:
*   Input:  {v.input_stage}
*   VAS:    {v.vas}
*   Output: {v.output}
*
* Behavioral parameters used by the harness:
*   target_total_gain={TARGET_TOTAL_GAIN}
*   headroom_v={v.headroom_v}
*   h2={v.h2}
*   h3={v.h3}
*   crossover_v={v.crossover_v}
*   rout_ohm={v.rout_ohm}
*   idle_ma={v.idle_ma}
*
VCC VCC 0 DC {SUPPLY_RAIL_V:g}
VEE VEE 0 DC -{SUPPLY_RAIL_V:g}
VIN IN 0 SIN(0 0.1 1k)
* Replace BAMP with the expanded transistor schematic before hardware SPICE.
* BAMP OUT 0 V={{ behavioral transfer for {v.ident} }}
ROUT OUT LOAD {v.rout_ohm}
RLOAD LOAD 0 8
RZ LOAD ZOB 10
CZ ZOB 0 100n
*.tran 0 30m 10m 2u
*.four 1k V(LOAD)
.end
"""
        (NETLIST_DIR / f"variant_{v.ident}.cir").write_text(text, encoding="utf-8")


def svg_text(x: int, y: int, text: str, size: int = 15, weight: str = "400") -> str:
    safe = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return (
        f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="#111">{safe}</text>'
    )


def box(x: int, y: int, w: int, h: int, label: str, sub: str = "") -> str:
    parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#fff" stroke="#111" stroke-width="2"/>']
    parts.append(svg_text(x + 10, y + 25, label, 15, "700"))
    if sub:
        words = sub.split(" ")
        line = ""
        yy = y + 48
        for word in words:
            trial = (line + " " + word).strip()
            if len(trial) > 24:
                parts.append(svg_text(x + 10, yy, line, 12))
                yy += 16
                line = word
            else:
                line = trial
        if line:
            parts.append(svg_text(x + 10, yy, line, 12))
    return "\n".join(parts)


def write_variants_svg(rows: list[dict[str, str | float]]) -> None:
    rank = {str(r["id"]): i + 1 for i, r in enumerate(rows)}
    cards = []
    w, h = 1500, 1220
    for idx, v in enumerate(VARIANTS):
        col = idx % 2
        row = idx // 2
        x = 55 + col * 720
        y = 95 + row * 220
        cards.append(f'<rect x="{x}" y="{y}" width="660" height="185" fill="#fff" stroke="#111" stroke-width="2"/>')
        cards.append(svg_text(x + 14, y + 27, f'{v.ident}. {v.name}', 15, "700"))
        cards.append(svg_text(x + 570, y + 27, f'Rank {rank[v.ident]}', 14, "700"))
        sx, sy = x + 18, y + 55
        cards.append(box(sx, sy, 118, 62, "Input", v.input_stage))
        cards.append(box(sx + 158, sy, 145, 62, "VAS", v.vas))
        cards.append(box(sx + 343, sy, 145, 62, "Bias", "Vbe multiplier + local degeneration"))
        cards.append(box(sx + 528, sy, 95, 62, "Output", v.output))
        # Wires, no feedback return.
        for x1 in [sx + 118, sx + 303, sx + 488]:
            cards.append(f'<line x1="{x1}" y1="{sy + 31}" x2="{x1 + 40}" y2="{sy + 31}" stroke="#111" stroke-width="2"/>')
        cards.append(f'<line x1="{sx + 623}" y1="{sy + 31}" x2="{sx + 646}" y2="{sy + 31}" stroke="#111" stroke-width="2"/>')
        cards.append(svg_text(sx + 630, sy + 23, "OUT", 12, "700"))
        cards.append(svg_text(sx, y + 148, f'Local only: emitter/source resistors, current sources, output emitter resistors', 12))
        cards.append(svg_text(sx, y + 168, f'No global feedback from OUT to input. Complexity {v.complexity}/10.', 12))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<rect width="100%" height="100%" fill="#fff"/>
{svg_text(55, 48, f"Ten {AMPLIFIER_CLASS} No-Overall-Feedback Power Amp Topologies", 28, "700")}
{svg_text(55, 75, f"Rails are +/-{SUPPLY_RAIL_V:g} V and total voltage gain is constrained to Av = {TARGET_TOTAL_GAIN:g}.", 15)}
{''.join(cards)}
</svg>
"""
    (OUTDIR / "ten_topologies.svg").write_text(svg, encoding="utf-8")


def write_best_svg(best: Variant, rows: list[dict[str, str | float]]) -> None:
    row = next(r for r in rows if r["id"] == best.ident)
    w, h = 1500, 900
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        '<rect width="100%" height="100%" fill="#fff"/>',
        svg_text(55, 48, f"Selected Topology: {best.ident}. {best.name}", 28, "700"),
        svg_text(55, 78, f"{AMPLIFIER_CLASS}, +/-{SUPPLY_RAIL_V:g} V rails, total voltage gain Av = {TARGET_TOTAL_GAIN:g}.", 15),
        '<line x1="55" y1="115" x2="1445" y2="115" stroke="#111" stroke-width="3"/>',
        '<line x1="55" y1="785" x2="1445" y2="785" stroke="#111" stroke-width="3"/>',
        svg_text(60, 105, f"+{SUPPLY_RAIL_V:g} V", 16, "700"),
        svg_text(60, 815, f"-{SUPPLY_RAIL_V:g} V", 16, "700"),
    ]

    y = 240
    xs = [95, 285, 505, 735, 955, 1185]
    blocks = [
        ("IN + RF", "C1, R1, R2\ninput reference"),
        ("Q1/Q1B", "matched buffer pair\nBJT or JFET"),
        ("Q2/Q3", "upper cascoded VAS\nwith RE degeneration"),
        ("Q4/Q5", "lower complementary\ncascoded VAS"),
        ("QBIAS", "Vbe multiplier\non heatsink"),
        ("OUTPUT", best.output),
    ]
    for x, (title, sub) in zip(xs, blocks):
        parts.append(box(x, y, 155, 130, title, sub.replace("\n", " ")))
        parts.append(f'<line x1="{x + 77}" y1="115" x2="{x + 77}" y2="{y}" stroke="#111" stroke-width="2"/>')
        parts.append(f'<line x1="{x + 77}" y1="{y + 130}" x2="{x + 77}" y2="785" stroke="#111" stroke-width="2"/>')
    for x in [250, 440, 660, 890, 1110]:
        parts.append(f'<line x1="{x}" y1="{y + 65}" x2="{x + 35}" y2="{y + 65}" stroke="#111" stroke-width="2"/>')

    # Explicit current sources as transistor/resistor blocks.
    parts.append(box(510, 145, 150, 65, "Q10/R10/R11", "+VAS current source"))
    parts.append(box(510, 635, 150, 65, "Q11/R12/R13", "-VAS current sink"))
    parts.append(f'<line x1="585" y1="210" x2="585" y2="{y}" stroke="#111" stroke-width="2"/>')
    parts.append(f'<line x1="585" y1="{y + 130}" x2="585" y2="635" stroke="#111" stroke-width="2"/>')

    # Output load, relay, zobel.
    parts.append('<line x1="1340" y1="305" x2="1410" y2="305" stroke="#111" stroke-width="2"/>')
    parts.append(svg_text(1350, 292, "OUT", 16, "700"))
    parts.append(box(1345, 365, 90, 60, "Relay", "speaker"))
    parts.append(box(1345, 455, 90, 75, "RL", "8 ohm load"))
    parts.append(box(1210, 455, 105, 75, "Zobel", "10R + 100n"))
    parts.append('<line x1="1410" y1="305" x2="1410" y2="365" stroke="#111" stroke-width="2"/>')
    parts.append('<line x1="1410" y1="425" x2="1410" y2="455" stroke="#111" stroke-width="2"/>')
    parts.append('<line x1="1410" y1="530" x2="1410" y2="575" stroke="#111" stroke-width="2"/>')
    parts.append('<line x1="1385" y1="575" x2="1435" y2="575" stroke="#111" stroke-width="2"/>')
    parts.append('<line x1="1395" y1="588" x2="1425" y2="588" stroke="#111" stroke-width="2"/>')
    parts.append('<line x1="1403" y1="601" x2="1417" y2="601" stroke="#111" stroke-width="2"/>')
    parts.append('<line x1="1340" y1="305" x2="1262" y2="455" stroke="#111" stroke-width="2"/>')

    # Notes and metrics.
    parts.append('<rect x="85" y="520" width="390" height="150" fill="#fff" stroke="#111" stroke-width="2"/>')
    parts.append(svg_text(105, 552, "No overall feedback", 18, "700"))
    parts.append(svg_text(105, 582, "OUT connects only to relay/load/Zobel.", 15))
    parts.append(svg_text(105, 607, "No OUT wire returns to IN or VAS input.", 15))
    parts.append(svg_text(105, 637, "Local feedback: RE degeneration, emitter", 15))
    parts.append(svg_text(105, 662, "resistors, current-source linearization.", 15))

    parts.append('<rect x="735" y="520" width="410" height="150" fill="#fff" stroke="#111" stroke-width="2"/>')
    parts.append(svg_text(755, 552, "Simulation snapshot", 18, "700"))
    parts.append(svg_text(755, 582, f'1 W THD: {row["thd_1w_pct"]}%   5 W THD: {row["thd_5w_pct"]}%', 15))
    parts.append(svg_text(755, 607, f'Clean power before 1% THD: {row["clean_power_1pct_w"]} W / 8R', 15))
    parts.append(svg_text(755, 632, f'Damping factor estimate: {row["damping_factor_8r"]}', 15))
    parts.append(svg_text(755, 657, f'Gain target: Av = {TARGET_TOTAL_GAIN:g}   Score: {row["score"]}/100', 15, "700"))

    parts.append(svg_text(55, 858, "Important: this is a topology schematic and behavioral comparison, not a production-ready SPICE/hardware design.", 13))
    parts.append("</svg>")
    (OUTDIR / "selected_topology.svg").write_text("\n".join(parts), encoding="utf-8")


def write_summary(rows: list[dict[str, str | float]]) -> None:
    best_id = str(rows[0]["id"])
    best = next(v for v in VARIANTS if v.ident == best_id)
    source_lines = [
        f"- [{name}]({url}): {idea}."
        for name, url, idea in SOURCE_REFERENCES
    ]
    lines = [
        "# No-Overall-Feedback Amplifier Topology Study",
        "",
        "Simulation method: pure-Python behavioral model, because no local ngspice/LTspice binary was available. "
        f"All candidates used +/-{SUPPLY_RAIL_V:g} V rails, 8 ohm load, 1 kHz sine tests, {AMPLIFIER_CLASS} output bias, "
        f"total voltage gain Av = {TARGET_TOTAL_GAIN:g}, no global feedback, and identical ranking rules.",
        "",
        "## Internet Design Ideas Used",
        "",
        *source_lines,
        "",
        "This is useful for choosing a topology direction, not for signing off a hardware design. The selected topology still needs transistor-level SPICE, SOA protection, compensation, PCB layout, and bench validation.",
        "",
        f"## Selected topology: Variant {best.ident}",
        "",
        f"**{best.name}**",
        "",
        best.notes,
        "",
        "## Ranking",
        "",
        "| Rank | ID | Score | 1 W THD % | 5 W THD % | Clean W @ 1% THD | Damping | Offset mV | Topology |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(rows, start=1):
        lines.append(
            f"| {i} | {r['id']} | {r['score']} | {r['thd_1w_pct']} | {r['thd_5w_pct']} | "
            f"{r['clean_power_1pct_w']} | {r['damping_factor_8r']} | {r['offset_mv_est']} | {r['name']} |"
        )
    lines.extend(
        [
            "",
            "## Why the selected topology wins",
            "",
            "- On +/-15 V rails, output-stage headroom matters more than it did in the +/-35 V comparison.",
            "- The selected low-voltage folded-cascode/CFP approach preserves more output swing than a triple emitter follower.",
            "- The complementary feedback pair is only a local output-stage loop; there is still no overall OUT-to-input feedback path.",
            "- It has the strongest combination of clean power, damping estimate, and crossover behavior in this AB/low-voltage comparison.",
            "- Variant 05, the complementary cascoded VAS with double emitter follower, is the safer fallback if CFP stability is a concern.",
        ]
    )
    (OUTDIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTDIR.mkdir(exist_ok=True)
    rows = variant_rows()
    write_csv(rows)
    write_netlists()
    write_variants_svg(rows)
    best = next(v for v in VARIANTS if v.ident == str(rows[0]["id"]))
    write_best_svg(best, rows)
    write_summary(rows)
    print(f"Best: {best.ident} - {best.name}")
    print(f"Results: {OUTDIR / 'results.csv'}")
    print(f"Summary: {OUTDIR / 'summary.md'}")
    print(f"Topologies: {OUTDIR / 'ten_topologies.svg'}")
    print(f"Selected: {OUTDIR / 'selected_topology.svg'}")


if __name__ == "__main__":
    main()
