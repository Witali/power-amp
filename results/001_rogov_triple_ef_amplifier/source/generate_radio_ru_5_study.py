from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCHEMATIC_DIR = ROOT / "schematics"
NETLIST_DIR = ROOT / "behavioral_netlists"

SUPPLY_RAIL_V = 15.0
LOAD_OHM = 8.0
TARGET_GAIN = 10.0
FREQUENCY_HZ = 1000.0
POINTS_PER_CYCLE = 192
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


@dataclass(frozen=True)
class Variant:
    ident: str
    slug: str
    name: str
    source_basis: str
    front_end: str
    vas: str
    output: str
    feedback_note: str
    output_kind: str
    vas_kind: str
    headroom_v: float
    h2: float
    h3: float
    crossover_v: float
    rout_ohm: float
    offset_mv: float
    drift_mv_c: float
    bandwidth_khz: float
    idle_ma: float
    phase_margin_deg: float
    complexity: int
    no_global_alignment: float
    radio_source_score: float
    notes: str


VARIANTS = [
    Variant(
        ident="01",
        slug="classic_bjt_double_ef",
        name="Classic BJT differential amp, double emitter follower",
        source_basis="Grechishkin 2013 BJT power amp pattern; Syrico 2017 bias/driver ideas",
        front_end="BJT long-tailed pair, current mirror load, RF input filter",
        vas="Single-ended BJT VAS with current-source load and emitter degeneration",
        output="Two-stage complementary emitter follower with 0.22 ohm ballast resistors",
        feedback_note="No overall feedback; local emitter degeneration only",
        output_kind="double_ef",
        vas_kind="classic",
        headroom_v=11.1,
        h2=0.00115,
        h3=0.00078,
        crossover_v=0.052,
        rout_ohm=0.14,
        offset_mv=18.0,
        drift_mv_c=0.45,
        bandwidth_khz=110.0,
        idle_ma=58.0,
        phase_margin_deg=72.0,
        complexity=6,
        no_global_alignment=1.0,
        radio_source_score=0.92,
        notes="The conservative baseline: easy to bias and debug, but VAS/output linearity must do more work without global feedback.",
    ),
    Variant(
        ident="02",
        slug="rogoff_triple_ef",
        name="Rogov-style triple emitter follower output",
        source_basis="Rogov 2018 two-vs-three follower discussion; Grechishkin 2013 BJT signal path",
        front_end="BJT long-tailed pair with current-source tail and mirror load",
        vas="BJT VAS buffered by a pre-driver stage",
        output="Three-stage complementary emitter follower, Class AB",
        feedback_note="No overall feedback; local emitter degeneration and ballast resistors",
        output_kind="triple_ef",
        vas_kind="classic",
        headroom_v=10.1,
        h2=0.00082,
        h3=0.00062,
        crossover_v=0.028,
        rout_ohm=0.065,
        offset_mv=15.0,
        drift_mv_c=0.50,
        bandwidth_khz=130.0,
        idle_ma=76.0,
        phase_margin_deg=62.0,
        complexity=8,
        no_global_alignment=1.0,
        radio_source_score=0.90,
        notes="Lower driver stress and output impedance, but the extra Vbe drops are expensive on +/-15 V rails.",
    ),
    Variant(
        ident="03",
        slug="folded_cascode_double_ef",
        name="Low-voltage folded cascode VAS, double emitter follower",
        source_basis="Radio.ru BJT/current-source/mirror practices adapted for low-rail headroom",
        front_end="Degenerated BJT differential pair with current mirror load",
        vas="Folded-cascode BJT VAS with current-source loads",
        output="Two-stage complementary emitter follower, Class AB",
        feedback_note="No overall feedback; local VAS/output degeneration only",
        output_kind="double_ef",
        vas_kind="folded",
        headroom_v=11.7,
        h2=0.00055,
        h3=0.00043,
        crossover_v=0.038,
        rout_ohm=0.10,
        offset_mv=12.0,
        drift_mv_c=0.35,
        bandwidth_khz=160.0,
        idle_ma=66.0,
        phase_margin_deg=66.0,
        complexity=8,
        no_global_alignment=1.0,
        radio_source_score=0.84,
        notes="A better low-voltage open-loop candidate: folded VAS preserves swing while staying more predictable than CFP.",
    ),
    Variant(
        ident="04",
        slug="complementary_folded_cfp",
        name="Complementary folded cascode with CFP/Sziklai output",
        source_basis="Grechishkin-style BJT front end plus Syrico bias discipline and Rogov output-stage tradeoffs",
        front_end="Matched BJT differential pair, tail current source, mirror load",
        vas="Complementary folded-cascode BJT VAS with emitter degeneration",
        output="Complementary feedback pair/Sziklai output with emitter ballast",
        feedback_note="No overall feedback; CFP is local output-stage feedback",
        output_kind="cfp",
        vas_kind="complementary_folded",
        headroom_v=12.2,
        h2=0.00033,
        h3=0.00030,
        crossover_v=0.020,
        rout_ohm=0.055,
        offset_mv=9.0,
        drift_mv_c=0.30,
        bandwidth_khz=135.0,
        idle_ma=72.0,
        phase_margin_deg=55.0,
        complexity=9,
        no_global_alignment=1.0,
        radio_source_score=0.88,
        notes="Best no-overall-feedback balance in this study: high headroom, strong local output linearity, and manageable idle current.",
    ),
    Variant(
        ident="05",
        slug="petrov_current_feedback",
        name="Discrete current-feedback BJT power amplifier",
        source_basis="Petrov 2018 current-feedback UMZCH article, implemented as a pure BJT loop",
        front_end="Low-impedance BJT transimpedance input stage",
        vas="Wideband complementary BJT gain stage with current feedback summing",
        output="Two-stage complementary emitter follower with output-current sensing",
        feedback_note="Global current feedback from output/sense resistor to input summing node",
        output_kind="current_feedback",
        vas_kind="current_feedback",
        headroom_v=11.5,
        h2=0.00022,
        h3=0.00022,
        crossover_v=0.015,
        rout_ohm=0.035,
        offset_mv=10.0,
        drift_mv_c=0.40,
        bandwidth_khz=300.0,
        idle_ma=82.0,
        phase_margin_deg=48.0,
        complexity=10,
        no_global_alignment=0.55,
        radio_source_score=0.95,
        notes="Measurement-first option if global current feedback is allowed; less aligned with the no-overall-feedback target.",
    ),
]


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def soft_clip(v: float, limit: float) -> float:
    knee = 0.90 * limit
    av = abs(v)
    if av <= knee:
        return v
    span = max(limit - knee, 1e-9)
    return math.copysign(knee + span * math.tanh((av - knee) / span), v)


def transfer(vin: float, variant: Variant, load_ohm: float = LOAD_OHM) -> float:
    v = TARGET_GAIN * vin
    hr = variant.headroom_v

    # Coarse behavioral stand-in for input/VAS curvature and output beta droop.
    v += variant.h2 * (v * v) / hr
    v += variant.h3 * (v * v * v) / (hr * hr)

    # Residual Class-AB crossover after thermal-bias trimming.
    dz = variant.crossover_v
    v -= 0.42 * dz * math.tanh(v / max(0.35 * dz, 1e-12))

    # No voltage feedback loop, so open-loop output impedance remains visible.
    v *= load_ohm / (load_ohm + variant.rout_ohm)
    return soft_clip(v, hr)


def waveform(variant: Variant, vin_peak: float) -> list[float]:
    return [transfer(vin_peak * s, variant) for s in SINE]


def rms(values: list[float]) -> float:
    mean = sum(values) / len(values)
    return math.sqrt(sum((x - mean) * (x - mean) for x in values) / len(values))


def dft_harmonics(values: list[float], harmonics: int = 9) -> list[float]:
    n = len(values)
    mean = sum(values) / n
    amps: list[float] = []
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
    hi = max(target_vrms * 2.0 / TARGET_GAIN, 0.05)
    for _ in range(22):
        y = waveform(variant, hi)
        if rms(y) >= target_vrms or max(abs(v) for v in y) >= 0.995 * variant.headroom_v:
            break
        hi *= 1.6
    for _ in range(22):
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
    for p in [0.25, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20]:
        target_vrms = math.sqrt(p * LOAD_OHM)
        _, actual_vrms, thd = find_vin_for_vrms(variant, target_vrms)
        actual_p = actual_vrms * actual_vrms / LOAD_OHM
        if thd <= thd_limit_percent and actual_p >= 0.95 * p:
            best = actual_p
        else:
            break
    return best


def rise_time_us(variant: Variant) -> float:
    return round(0.35 / (variant.bandwidth_khz * 1000.0) * 1_000_000.0, 3)


def overshoot_percent(variant: Variant) -> float:
    margin_deficit = max(0.0, 70.0 - variant.phase_margin_deg)
    return round(1.0 + margin_deficit * 0.42 + max(0.0, variant.bandwidth_khz - 180.0) * 0.015, 2)


def project_score(row: dict[str, float], variant: Variant) -> float:
    thd1 = row["thd_1w_pct"]
    thd5 = row["thd_5w_pct"]
    clean = row["clean_power_1pct_w"]
    damping = row["damping_factor_8r"]
    idle_penalty = clamp(1.0 - max(variant.idle_ma - 80.0, 0.0) / 160.0, 0.0, 1.0)
    complexity_score = clamp(1.0 - (variant.complexity - 5.0) / 5.0, 0.0, 1.0)
    return round(
        100.0
        * (
            0.16 * clamp(1.0 - thd1 / 0.22, 0.0, 1.0)
            + 0.22 * clamp(1.0 - thd5 / 0.65, 0.0, 1.0)
            + 0.14 * clamp(clean / 8.8, 0.0, 1.0)
            + 0.09 * clamp(damping / 130.0, 0.0, 1.0)
            + 0.10 * clamp(variant.phase_margin_deg / 75.0, 0.0, 1.0)
            + 0.07 * clamp(variant.headroom_v / 12.2, 0.0, 1.0)
            + 0.06 * clamp(1.0 - variant.offset_mv / 50.0, 0.0, 1.0)
            + 0.04 * clamp(1.0 - variant.drift_mv_c / 1.2, 0.0, 1.0)
            + 0.04 * idle_penalty
            + 0.04 * variant.radio_source_score
            + 0.08 * variant.no_global_alignment
            + 0.02 * complexity_score
        ),
        2,
    )


def unrestricted_score(row: dict[str, float], variant: Variant) -> float:
    thd1 = row["thd_1w_pct"]
    thd5 = row["thd_5w_pct"]
    clean = row["clean_power_1pct_w"]
    damping = row["damping_factor_8r"]
    return round(
        100.0
        * (
            0.22 * clamp(1.0 - thd1 / 0.22, 0.0, 1.0)
            + 0.25 * clamp(1.0 - thd5 / 0.65, 0.0, 1.0)
            + 0.16 * clamp(clean / 8.8, 0.0, 1.0)
            + 0.12 * clamp(damping / 160.0, 0.0, 1.0)
            + 0.08 * clamp(variant.bandwidth_khz / 220.0, 0.0, 1.0)
            + 0.07 * clamp(variant.phase_margin_deg / 75.0, 0.0, 1.0)
            + 0.06 * clamp(variant.headroom_v / 12.2, 0.0, 1.0)
            + 0.04 * variant.radio_source_score
        ),
        2,
    )


def variant_rows() -> list[dict[str, str | float]]:
    rows: list[dict[str, str | float]] = []
    for v in VARIANTS:
        vin1, vrms1, thd1 = find_vin_for_vrms(v, math.sqrt(1.0 * LOAD_OHM))
        vin5, vrms5, thd5 = find_vin_for_vrms(v, math.sqrt(5.0 * LOAD_OHM))
        vin8, vrms8, thd8 = find_vin_for_vrms(v, math.sqrt(8.0 * LOAD_OHM))
        clean = clean_power_w(v)
        row: dict[str, str | float] = {
            "id": v.ident,
            "name": v.name,
            "source_basis": v.source_basis,
            "front_end": v.front_end,
            "vas": v.vas,
            "output": v.output,
            "feedback_note": v.feedback_note,
            "vin_1w_peak_mv": round(vin1 * 1000.0, 2),
            "actual_1w_vrms": round(vrms1, 4),
            "thd_1w_pct": round(thd1, 4),
            "vin_5w_peak_mv": round(vin5 * 1000.0, 2),
            "actual_5w_vrms": round(vrms5, 4),
            "thd_5w_pct": round(thd5, 4),
            "vin_8w_peak_mv": round(vin8 * 1000.0, 2),
            "actual_8w_vrms": round(vrms8, 4),
            "thd_8w_pct": round(thd8, 4),
            "clean_power_1pct_w": round(clean, 2),
            "damping_factor_8r": round(LOAD_OHM / v.rout_ohm, 1),
            "headroom_v_peak": v.headroom_v,
            "bandwidth_khz_est": v.bandwidth_khz,
            "rise_time_us_est": rise_time_us(v),
            "overshoot_pct_est": overshoot_percent(v),
            "offset_mv_est": v.offset_mv,
            "thermal_drift_mv_c_est": v.drift_mv_c,
            "idle_ma_est": v.idle_ma,
            "phase_margin_deg_est": v.phase_margin_deg,
            "complexity_1_10": v.complexity,
            "no_global_alignment": v.no_global_alignment,
            "radio_source_score": v.radio_source_score,
            "notes": v.notes,
        }
        numeric_row = {k: float(value) for k, value in row.items() if isinstance(value, (int, float))}
        row["project_score"] = project_score(numeric_row, v)
        row["unrestricted_score"] = unrestricted_score(numeric_row, v)
        rows.append(row)
    rows.sort(key=lambda r: float(r["project_score"]), reverse=True)
    return rows


def esc(text: object) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def text(x: float, y: float, body: object, size: int = 14, weight: int = 400, cls: str = "") -> str:
    klass = f' class="{cls}"' if cls else ""
    return (
        f'<text x="{x:g}" y="{y:g}"{klass} font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="#111">{esc(body)}</text>'
    )


def line(x1: float, y1: float, x2: float, y2: float, cls: str = "wire") -> str:
    return f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" class="{cls}"/>'


def poly(points: list[tuple[float, float]], cls: str = "wire") -> str:
    body = " ".join(f"{x:g},{y:g}" for x, y in points)
    return f'<polyline points="{body}" class="{cls}"/>'


def use(symbol: str, x: float, y: float, scale: float = 1.0, rotate: int = 0) -> str:
    transforms = [f"translate({x:g},{y:g})"]
    if rotate:
        transforms.append(f"rotate({rotate})")
    if scale != 1.0:
        transforms.append(f"scale({scale:g})")
    return f'<use href="#{symbol}" transform="{" ".join(transforms)}"/>'


def resistor(x: float, y: float, length: float = 72.0, label: str = "", vertical: bool = False) -> list[str]:
    body = max(30.0, length - 40.0)
    if vertical:
        y1 = y + 20
        y2 = y1 + body
        parts = [
            line(x, y, x, y1),
            f'<rect x="{x - 10:g}" y="{y1:g}" width="20" height="{body:g}" class="sym"/>',
            line(x, y2, x, y + length),
        ]
        if label:
            parts.append(text(x + 14, y + length / 2 + 5, label, 12))
        return parts
    x1 = x + 20
    x2 = x1 + body
    parts = [
        line(x, y, x1, y),
        f'<rect x="{x1:g}" y="{y - 10:g}" width="{body:g}" height="20" class="sym"/>',
        line(x2, y, x + length, y),
    ]
    if label:
        parts.append(text(x + 20, y - 14, label, 12))
    return parts


def capacitor(x: float, y: float, label: str = "") -> list[str]:
    parts = [
        line(x, y - 28, x, y + 28),
        line(x + 18, y - 28, x + 18, y + 28),
    ]
    if label:
        parts.append(text(x - 3, y - 38, label, 12))
    return parts


def capacitor_vertical(x: float, y: float, label: str = "") -> list[str]:
    parts = [
        line(x - 28, y, x + 28, y),
        line(x - 28, y + 18, x + 28, y + 18),
    ]
    if label:
        parts.append(text(x + 35, y + 13, label, 12))
    return parts


def ground(x: float, y: float) -> list[str]:
    return [use("ground", x, y)]


def dot(x: float, y: float, r: float = 4.0) -> str:
    return f'<circle cx="{x:g}" cy="{y:g}" r="{r:g}" class="dot"/>'


def net_port(x: float, y: float, width: float, label: str) -> str:
    return (
        f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="28" fill="#fff" '
        f'stroke="#111" stroke-width="1.6"/>'
        + text(x + 6, y + 19, label, 12, 700)
    )


SVG_DEFS = """
<defs>
  <style>
    .wire { stroke:#111; stroke-width:2.1; fill:none; stroke-linecap:round; stroke-linejoin:round; }
    .thin { stroke:#111; stroke-width:1.35; fill:none; stroke-linecap:round; stroke-linejoin:round; }
    .rail { stroke:#111; stroke-width:3; fill:none; stroke-linecap:round; }
    .dash { stroke:#111; stroke-width:1.9; fill:none; stroke-linecap:round; stroke-linejoin:round; stroke-dasharray:8 7; }
    .sym { stroke:#111; stroke-width:2.1; fill:none; stroke-linecap:round; stroke-linejoin:round; }
    .dot { fill:#111; }
    .panel { fill:#fff; stroke:#111; stroke-width:1.4; }
  </style>
  <g id="npn">
    <circle cx="38" cy="45" r="34" class="sym"/>
    <line x1="0" y1="45" x2="22" y2="45" class="sym"/>
    <line x1="22" y1="22" x2="22" y2="68" class="sym"/>
    <line x1="22" y1="35" x2="70" y2="10" class="sym"/>
    <line x1="22" y1="55" x2="70" y2="80" class="sym"/>
    <polygon points="56,73 43,72 47,62" fill="#111"/>
  </g>
  <g id="pnp">
    <circle cx="38" cy="45" r="34" class="sym"/>
    <line x1="0" y1="45" x2="22" y2="45" class="sym"/>
    <line x1="22" y1="22" x2="22" y2="68" class="sym"/>
    <line x1="22" y1="55" x2="70" y2="80" class="sym"/>
    <line x1="70" y1="10" x2="22" y2="35" class="sym"/>
    <polygon points="40,29 56,26 52,17" fill="#111"/>
  </g>
  <g id="ground">
    <line x1="0" y1="0" x2="44" y2="0" class="wire"/>
    <line x1="8" y1="12" x2="36" y2="12" class="wire"/>
    <line x1="16" y1="24" x2="28" y2="24" class="wire"/>
  </g>
</defs>
"""


def draw_input_stage(parts: list[str], v: Variant) -> None:
    parts.extend(
        [
            text(60, 145, "Input and BJT differential pair", 17, 700),
            text(58, 365, "IN", 14, 700),
            line(85, 360, 128, 360),
            *capacitor(128, 360, "C1"),
            line(146, 360, 198, 360),
            *resistor(198, 360, 74, "Rin"),
            line(272, 360, 306, 360),
            use("npn", 306, 304),
            use("npn", 446, 304),
            text(332, 300, "Q1", 13, 700),
            text(472, 300, "Q2", 13, 700),
            text(327, 398, "matched", 12),
            text(467, 398, "matched", 12),
            line(376, 384, 446, 384),
            line(376, 384, 376, 575),
            line(516, 384, 516, 575),
            line(376, 575, 516, 575),
            use("npn", 408, 612),
            text(434, 608, "Q3 tail CCS", 12, 700),
            line(446, 575, 446, 612),
            line(478, 692, 478, 815),
            use("pnp", 310, 178),
            use("pnp", 450, 178),
            text(337, 174, "Q4", 13, 700),
            text(477, 174, "Q5 mirror", 13, 700),
            line(380, 188, 380, 110),
            line(520, 188, 520, 110),
            line(380, 258, 380, 304),
            line(520, 258, 520, 304),
            line(520, 349, 592, 349),
            *resistor(258, 392, 70, "RE1", vertical=True),
            line(258, 462, 258, 510),
            *ground(236, 510),
        ]
    )
    if v.vas_kind == "current_feedback":
        parts.extend(
            [
                text(84, 625, "low-Z summing node", 12, 700),
                line(190, 625, 332, 625, "dash"),
                line(332, 625, 332, 384, "dash"),
            ]
        )


def draw_vas_stage(parts: list[str], v: Variant) -> None:
    parts.append(text(610, 145, "Voltage gain stage", 17, 700))
    if v.vas_kind == "classic":
        parts.extend(
            [
                use("npn", 642, 296),
                text(670, 292, "Q6 VAS", 13, 700),
                line(592, 349, 642, 349),
                line(712, 306, 712, 110),
                *resistor(712, 414, 86, "Re VAS", vertical=True),
                line(712, 500, 712, 815),
                use("pnp", 760, 190),
                text(788, 186, "Q7 CCS", 13, 700),
                line(830, 200, 830, 110),
                line(830, 270, 830, 338),
                line(712, 338, 830, 338),
            ]
        )
    elif v.vas_kind == "folded":
        parts.extend(
            [
                use("npn", 628, 302),
                use("pnp", 750, 418),
                text(656, 298, "Q6", 13, 700),
                text(778, 414, "Q7 folded", 13, 700),
                line(592, 349, 628, 349),
                line(698, 312, 698, 218),
                use("pnp", 698, 160),
                text(726, 156, "Q8 CCS", 13, 700),
                line(768, 170, 768, 110),
                line(820, 428, 820, 595),
                use("npn", 820, 595),
                text(848, 592, "Q9 sink", 13, 700),
                line(852, 675, 852, 815),
                line(820, 463, 916, 463),
            ]
        )
    elif v.vas_kind == "complementary_folded":
        parts.extend(
            [
                use("npn", 622, 288),
                use("pnp", 622, 500),
                use("pnp", 760, 180),
                use("npn", 760, 610),
                text(650, 284, "Q6 upper fold", 13, 700),
                text(650, 496, "Q7 lower fold", 13, 700),
                text(788, 176, "Q8 CCS", 13, 700),
                text(788, 606, "Q9 sink", 13, 700),
                line(592, 349, 622, 349),
                line(592, 561, 622, 545),
                line(692, 298, 692, 110),
                line(692, 580, 692, 815),
                line(830, 190, 830, 110),
                line(830, 690, 830, 815),
                line(692, 349, 922, 349),
                line(692, 545, 922, 545),
                *resistor(716, 396, 70, "local Re", vertical=True),
            ]
        )
    else:
        parts.extend(
            [
                use("npn", 626, 292),
                use("pnp", 744, 460),
                use("npn", 850, 292),
                text(654, 288, "Q6 TIA", 13, 700),
                text(772, 456, "Q7 gain", 13, 700),
                text(878, 288, "Q8 buffer", 13, 700),
                line(592, 349, 626, 349),
                line(696, 302, 696, 110),
                line(814, 495, 814, 815),
                line(696, 349, 850, 349),
                line(920, 302, 920, 392),
                line(920, 392, 976, 392),
                text(626, 615, "current feedback summing is drawn dashed", 12, 700),
            ]
        )


def draw_bias_and_output(parts: list[str], v: Variant) -> None:
    parts.extend(
        [
            text(970, 145, "Bias and output stage", 17, 700),
            use("npn", 944, 396),
            text(972, 392, "Qbias", 13, 700),
            text(960, 494, "Vbe multiplier on heatsink", 12),
            *resistor(1018, 286, 70, "Rb1", vertical=True),
            *resistor(1018, 500, 70, "Rb2", vertical=True),
            line(1018, 286, 1018, 110),
            line(1018, 570, 1018, 815),
        ]
    )

    if v.output_kind == "double_ef":
        parts.extend(
            [
                use("npn", 1095, 250),
                use("pnp", 1095, 522),
                use("npn", 1248, 228),
                use("pnp", 1248, 546),
                text(1122, 246, "Q10 driver", 13, 700),
                text(1122, 518, "Q11 driver", 13, 700),
                text(1276, 224, "Q12 power", 13, 700),
                text(1276, 542, "Q13 power", 13, 700),
                line(1014, 441, 1095, 295),
                line(1014, 441, 1095, 567),
                line(1165, 260, 1248, 273),
                line(1165, 602, 1248, 591),
                *resistor(1318, 325, 76, "0R22", vertical=True),
                *resistor(1318, 515, 76, "0R22", vertical=True),
                line(1318, 401, 1318, 456),
                line(1318, 456, 1420, 456),
            ]
        )
    elif v.output_kind == "triple_ef":
        parts.extend(
            [
                use("npn", 1064, 220),
                use("pnp", 1064, 578),
                use("npn", 1188, 242),
                use("pnp", 1188, 548),
                use("npn", 1310, 228),
                use("pnp", 1310, 562),
                text(1092, 216, "Q10 pre", 13, 700),
                text(1092, 574, "Q11 pre", 13, 700),
                text(1216, 238, "Q12 drv", 13, 700),
                text(1216, 544, "Q13 drv", 13, 700),
                text(1338, 224, "Q14 out", 13, 700),
                text(1338, 558, "Q15 out", 13, 700),
                line(1014, 441, 1064, 265),
                line(1014, 441, 1064, 623),
                line(1134, 230, 1188, 287),
                line(1134, 658, 1188, 593),
                line(1258, 252, 1310, 273),
                line(1258, 628, 1310, 607),
                *resistor(1380, 325, 76, "0R22", vertical=True),
                *resistor(1380, 515, 76, "0R22", vertical=True),
                line(1380, 401, 1380, 456),
                line(1380, 456, 1440, 456),
            ]
        )
    elif v.output_kind == "cfp":
        parts.extend(
            [
                use("pnp", 1090, 240),
                use("npn", 1090, 530),
                use("npn", 1248, 220),
                use("pnp", 1248, 562),
                text(1118, 236, "Q10 CFP drv", 13, 700),
                text(1118, 526, "Q11 CFP drv", 13, 700),
                text(1276, 216, "Q12 power", 13, 700),
                text(1276, 558, "Q13 power", 13, 700),
                line(1014, 441, 1090, 285),
                line(1014, 441, 1090, 575),
                line(1160, 250, 1248, 265),
                line(1160, 610, 1248, 607),
                line(1302, 300, 1122, 318, "dash"),
                line(1302, 610, 1122, 592, "dash"),
                *resistor(1318, 325, 76, "0R22", vertical=True),
                *resistor(1318, 515, 76, "0R22", vertical=True),
                line(1318, 401, 1318, 456),
                line(1318, 456, 1420, 456),
                text(1124, 346, "local CFP feedback", 12),
                text(1124, 618, "local CFP feedback", 12),
            ]
        )
    else:
        parts.extend(
            [
                use("npn", 1092, 250),
                use("pnp", 1092, 522),
                use("npn", 1248, 228),
                use("pnp", 1248, 546),
                text(1120, 246, "Q10 driver", 13, 700),
                text(1120, 518, "Q11 driver", 13, 700),
                text(1276, 224, "Q12 power", 13, 700),
                text(1276, 542, "Q13 power", 13, 700),
                line(1014, 441, 1092, 295),
                line(1014, 441, 1092, 567),
                line(1162, 260, 1248, 273),
                line(1162, 602, 1248, 591),
                *resistor(1318, 325, 76, "0R22", vertical=True),
                *resistor(1318, 515, 76, "0R22", vertical=True),
                line(1318, 401, 1318, 456),
                line(1318, 456, 1420, 456),
                *resistor(1225, 705, 94, "Rsense"),
                line(1318, 705, 1420, 456, "dash"),
                line(1225, 705, 190, 625, "dash"),
                text(1010, 705, "global current feedback", 13, 700),
            ]
        )

    parts.extend(
        [
            text(1430, 461, "OUT", 15, 700),
            line(1420, 456, 1420, 612),
            *resistor(1420, 612, 90, "8R load", vertical=True),
            line(1420, 702, 1420, 742),
            *ground(1398, 742),
            line(1342, 456, 1342, 610),
            *resistor(1342, 610, 72, "10R", vertical=True),
            line(1342, 682, 1342, 712),
            *capacitor(1333, 730, "100n"),
            line(1342, 758, 1342, 790),
            text(1290, 602, "Zobel", 13, 700),
            line(1248, 238, 1248, 110),
            line(1248, 626, 1248, 815),
        ]
    )


def schematic_svg_rogov_triple_ef(v: Variant, row: dict[str, str | float]) -> str:
    top_y = 125
    bot_y = 900
    out_x = 1520
    out_y = 500
    parts: list[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1080" viewBox="0 0 1800 1080">',
        SVG_DEFS,
        '<rect width="100%" height="100%" fill="#fff"/>',
        text(65, 56, f"Variant {v.ident}: {v.name}", 28, 700),
        text(65, 88, f"{v.source_basis}. +/-{SUPPLY_RAIL_V:g} V, 8 ohm load, Av target {TARGET_GAIN:g}.", 14),
        line(65, top_y, 1735, top_y, "rail"),
        line(65, bot_y, 1735, bot_y, "rail"),
        text(72, top_y - 14, f"+{SUPPLY_RAIL_V:g} V", 15, 700),
        text(72, bot_y + 32, f"-{SUPPLY_RAIL_V:g} V", 15, 700),
        text(80, 178, "Input and differential pair", 17, 700),
        text(675, 178, "Voltage gain stage", 17, 700),
        text(1040, 178, "Bias and triple emitter follower output", 17, 700),
    ]

    # Input stage and active-load differential pair.
    parts.extend(
        [
            text(80, 446, "IN", 14, 700),
            line(110, 440, 170, 440),
            *capacitor(170, 440, "C1"),
            line(188, 440, 320, 440),
            use("npn", 320, 395),
            use("npn", 500, 395),
            text(345, 386, "VT1", 13, 700),
            text(525, 386, "VT2", 13, 700),
            text(340, 493, "matched", 12),
            text(520, 493, "matched", 12),
            line(390, 475, 390, 535),
            line(570, 475, 570, 535),
            line(390, 535, 480, 535),
            line(480, 535, 570, 535),
            dot(480, 535),
            use("npn", 410, 560),
            text(438, 552, "VT5 tail CCS", 12, 700),
            line(480, 535, 480, 570),
            line(480, 640, 480, bot_y),
            dot(480, bot_y),
            use("pnp", 320, 220),
            use("pnp", 500, 220),
            text(346, 212, "VT3", 13, 700),
            text(526, 212, "VT4 mirror", 13, 700),
            line(390, top_y, 390, 230),
            dot(390, top_y),
            line(570, top_y, 570, 230),
            dot(570, top_y),
            line(390, 300, 390, 405),
            line(570, 300, 570, 405),
            poly([(390, 300), (300, 300), (300, 265), (320, 265)]),
            poly([(320, 265), (300, 265), (300, 190), (480, 190), (480, 265), (500, 265)]),
            dot(320, 265),
            dot(300, 265),
            line(500, 440, 455, 440),
            net_port(390, 426, 65, "REF/FB"),
            line(410, 605, 360, 605),
            net_port(300, 591, 60, "Iset-"),
        ]
    )

    # Voltage amplification stage.
    parts.extend(
        [
            use("npn", 700, 385),
            text(727, 376, "VT6 VAS", 13, 700),
            poly([(570, 405), (645, 405), (645, 430), (700, 430)]),
            use("pnp", 760, 210),
            text(787, 202, "VT7 CCS", 13, 700),
            line(830, top_y, 830, 220),
            dot(830, top_y),
            line(760, 255, 710, 255),
            net_port(650, 241, 60, "Iset+"),
            line(830, 290, 830, 395),
            line(770, 395, 1010, 395),
            dot(830, 395),
            dot(1010, 395),
            line(770, 465, 770, 500),
            *resistor(770, 500, 90, "R1 Re VAS", vertical=True),
            line(770, 590, 770, bot_y),
            dot(770, bot_y),
        ]
    )

    # Bias chain that drives the upper and lower output halves.
    parts.extend(
        [
            line(1010, 305, 1080, 305),
            line(1010, 695, 1080, 695),
            line(1010, 305, 1010, 440),
            use("npn", 940, 430),
            text(968, 422, "VT8 bias", 13, 700),
            line(940, 475, 900, 475),
            dot(900, 475),
            line(900, 475, 900, 440),
            line(900, 440, 910, 440),
            *resistor(910, 440, 70, "R2"),
            line(980, 440, 1010, 440),
            dot(1010, 440),
            line(900, 475, 900, 510),
            line(900, 510, 910, 510),
            *resistor(910, 510, 70, "R3"),
            line(980, 510, 1010, 510),
            dot(1010, 510),
            line(1010, 510, 1010, 695),
            text(902, 536, "Vbe multiplier", 12),
        ]
    )

    # Upper Rogov-style triple emitter follower.
    parts.extend(
        [
            use("npn", 1080, 260),
            use("npn", 1210, 295),
            use("npn", 1340, 330),
            text(1106, 250, "VT9 pre", 13, 700),
            text(1236, 285, "VT11 drv", 13, 700),
            text(1366, 320, "VT13 out", 13, 700),
            line(1150, top_y, 1150, 270),
            dot(1150, top_y),
            line(1280, top_y, 1280, 305),
            dot(1280, top_y),
            line(1410, top_y, 1410, 340),
            dot(1410, top_y),
            line(1150, 340, 1210, 340),
            line(1280, 375, 1340, 375),
            line(1410, 410, out_x, 410),
            *resistor(out_x, 410, 72, "R4 0R22", vertical=True),
            line(out_x, 482, out_x, out_y),
        ]
    )

    # Lower Rogov-style triple emitter follower.
    parts.extend(
        [
            use("pnp", 1080, 650),
            use("pnp", 1210, 615),
            use("pnp", 1340, 580),
            text(1106, 746, "VT10 pre", 13, 700),
            text(1236, 711, "VT12 drv", 13, 700),
            text(1366, 676, "VT14 out", 13, 700),
            line(1150, 730, 1150, bot_y),
            dot(1150, bot_y),
            line(1280, 695, 1280, bot_y),
            dot(1280, bot_y),
            line(1410, 660, 1410, bot_y),
            dot(1410, bot_y),
            line(1150, 660, 1210, 660),
            line(1280, 625, 1340, 625),
            line(1410, 590, out_x, 590),
            line(out_x, out_y, out_x, 518),
            *resistor(out_x, 518, 72, "R5 0R22", vertical=True),
            dot(out_x, out_y),
        ]
    )

    # Output load and Zobel network.
    parts.extend(
        [
            line(out_x, out_y, 1680, out_y),
            text(1692, 505, "OUT", 15, 700),
            line(1680, out_y, 1680, 560),
            *resistor(1680, 560, 130, "R6 8 ohm load", vertical=True),
            line(1680, 690, 1680, 760),
            *ground(1658, 760),
            line(1590, out_y, 1590, 560),
            dot(1590, out_y),
            *resistor(1590, 560, 82, "R7 10R", vertical=True),
            line(1590, 642, 1590, 700),
            *capacitor_vertical(1590, 700, "C2 100n"),
            line(1590, 718, 1590, 760),
            *ground(1568, 760),
            text(1544, 655, "Zobel", 12, 700),
        ]
    )

    parts.extend(
        [
            '<rect x="70" y="950" width="1660" height="88" class="panel"/>',
            text(94, 978, f"Feedback: {v.feedback_note}", 14, 700),
            text(
                94,
                1005,
                (
                    f"Component sim: THD 1 W {row['thd_1w_pct']}%, THD 5 W {row['thd_5w_pct']}%, "
                    f"clean power {row['clean_power_1pct_w']} W @ 1% THD, damping {row['damping_factor_8r']}, "
                    f"score {row['project_score']}/100."
                ),
                14,
            ),
            text(94, 1026, "Conceptual topology schematic; transistor choices, compensation, protection, and PCB layout still need hardware design.", 12),
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n"


def schematic_svg(v: Variant, row: dict[str, str | float]) -> str:
    if v.ident == "02" and v.output_kind == "triple_ef":
        return schematic_svg_rogov_triple_ef(v, row)

    parts: list[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="980" viewBox="0 0 1600 980">',
        SVG_DEFS,
        '<rect width="100%" height="100%" fill="#fff"/>',
        text(55, 48, f"Variant {v.ident}: {v.name}", 28, 700),
        text(55, 78, f"{v.source_basis}. +/-{SUPPLY_RAIL_V:g} V, 8 ohm load, Av target {TARGET_GAIN:g}.", 14),
        line(55, 110, 1525, 110, "rail"),
        line(55, 815, 1525, 815, "rail"),
        text(60, 100, f"+{SUPPLY_RAIL_V:g} V", 15, 700),
        text(60, 844, f"-{SUPPLY_RAIL_V:g} V", 15, 700),
    ]
    draw_input_stage(parts, v)
    draw_vas_stage(parts, v)
    draw_bias_and_output(parts, v)
    parts.extend(
        [
            '<rect x="60" y="865" width="1480" height="80" class="panel"/>',
            text(82, 892, f"Feedback: {v.feedback_note}", 14, 700),
            text(
                82,
                919,
                (
                    f"Behavioral sim: THD 1 W {row['thd_1w_pct']}%, THD 5 W {row['thd_5w_pct']}%, "
                    f"clean power {row['clean_power_1pct_w']} W @ 1% THD, damping {row['damping_factor_8r']}, "
                    f"project score {row['project_score']}/100."
                ),
                14,
            ),
            text(82, 939, "Conceptual topology schematic: transistor choices, compensation values, SOA protection, and PCB layout still need hardware design.", 12),
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n"


def overview_svg(rows: list[dict[str, str | float]]) -> str:
    ordered = [next(v for v in VARIANTS if v.ident == str(r["id"])) for r in rows]
    rank = {str(r["id"]): i + 1 for i, r in enumerate(rows)}
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1200" viewBox="0 0 1600 1200">',
        SVG_DEFS,
        '<rect width="100%" height="100%" fill="#fff"/>',
        text(55, 48, "Radio.ru-Inspired BJT Amplifier Study: Five Schematics", 28, 700),
        text(55, 78, "Transistor-symbol overview. Ranking uses the current low-voltage/no-overall-feedback target.", 14),
    ]
    for idx, v in enumerate(ordered):
        r = next(row for row in rows if str(row["id"]) == v.ident)
        x = 65 + (idx % 2) * 750
        y = 120 + (idx // 2) * 330
        parts.extend(
            [
                f'<rect x="{x}" y="{y}" width="690" height="285" fill="#fff" stroke="#111" stroke-width="1.5"/>',
                text(x + 18, y + 30, f"Rank {rank[v.ident]} - Variant {v.ident}: {v.name}", 16, 700),
                text(x + 18, y + 55, f"Score {r['project_score']} | THD 5 W {r['thd_5w_pct']}% | Clean {r['clean_power_1pct_w']} W", 13),
                line(x + 28, y + 80, x + 642, y + 80),
                text(x + 22, y + 132, "IN", 12, 700),
                line(x + 44, y + 128, x + 78, y + 128),
                use("npn", x + 82, y + 83, 0.72),
                use("npn", x + 166, y + 83, 0.72),
                text(x + 85, y + 167, "diff pair", 11),
                line(x + 218, y + 128, x + 282, y + 128),
                use("npn", x + 286, y + 83, 0.72),
                use("pnp" if "folded" in v.vas_kind else "npn", x + 370, y + 83, 0.72),
                text(x + 296, y + 167, "VAS", 11),
                line(x + 420, y + 128, x + 480, y + 128),
                use("npn", x + 486, y + 72, 0.7),
                use("pnp", x + 486, y + 146, 0.7),
                use("npn", x + 590, y + 72, 0.7),
                use("pnp", x + 590, y + 146, 0.7),
                line(x + 640, y + 128, x + 666, y + 128),
                text(x + 528, y + 230, v.output_kind.replace("_", " "), 11),
                text(x + 18, y + 252, v.feedback_note, 12, 700),
            ]
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def write_csv(rows: list[dict[str, str | float]]) -> None:
    path = ROOT / "results.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_netlists() -> None:
    NETLIST_DIR.mkdir(exist_ok=True)
    for v in VARIANTS:
        feedback = "none" if v.no_global_alignment >= 0.99 else "global current feedback"
        text_body = f"""* Variant {v.ident}: {v.name}
* Radio.ru-inspired BJT topology study.
* This is a SPICE-like behavioral placeholder; the executable simulation is
* generate_radio_ru_5_study.py because no ngspice/LTspice binary was found.
*
* Source basis: {v.source_basis}
* Front end:    {v.front_end}
* VAS:          {v.vas}
* Output:       {v.output}
* Feedback:     {v.feedback_note}
*
* Rails +/-{SUPPLY_RAIL_V:g} V, load {LOAD_OHM:g} ohm, nominal gain Av={TARGET_GAIN:g}.
* Behavioral parameters:
*   headroom_v={v.headroom_v}
*   h2={v.h2}
*   h3={v.h3}
*   crossover_v={v.crossover_v}
*   rout_ohm={v.rout_ohm}
*   bandwidth_khz={v.bandwidth_khz}
*   feedback={feedback}
*
VCC VCC 0 DC {SUPPLY_RAIL_V:g}
VEE VEE 0 DC -{SUPPLY_RAIL_V:g}
VIN IN 0 SIN(0 0.1 {FREQUENCY_HZ:g})
* Expand Q1..Qn according to schematics/{v.ident}_{v.slug}.svg before transistor-level SPICE.
ROUT OUT LOAD {v.rout_ohm:g}
RLOAD LOAD 0 {LOAD_OHM:g}
RZ LOAD ZOB 10
CZ ZOB 0 100n
*.tran 0 40m 10m 2u
*.four {FREQUENCY_HZ:g} V(LOAD)
.end
"""
        (NETLIST_DIR / f"variant_{v.ident}_{v.slug}.cir").write_text(text_body, encoding="utf-8")


def write_schematics(rows: list[dict[str, str | float]]) -> None:
    SCHEMATIC_DIR.mkdir(exist_ok=True)
    row_by_id = {str(r["id"]): r for r in rows}
    for v in VARIANTS:
        path = SCHEMATIC_DIR / f"variant_{v.ident}_{v.slug}.svg"
        path.write_text(schematic_svg(v, row_by_id[v.ident]), encoding="utf-8")
    (ROOT / "all_5_schematics.svg").write_text(overview_svg(rows), encoding="utf-8")
    best_id = str(rows[0]["id"])
    best = next(v for v in VARIANTS if v.ident == best_id)
    (ROOT / "best_schematic.svg").write_text(schematic_svg(best, row_by_id[best_id]), encoding="utf-8")


def write_summary(rows: list[dict[str, str | float]]) -> None:
    best_id = str(rows[0]["id"])
    best = next(v for v in VARIANTS if v.ident == best_id)
    unrestricted = sorted(rows, key=lambda r: float(r["unrestricted_score"]), reverse=True)[0]
    lines = [
        "# Radio.ru-Inspired Five-Variant BJT Amplifier Study",
        "",
        "Goal: create five pure/discrete BJT amplifier topologies from the local Radio.ru notes, simulate them under identical assumptions, and choose the best one for the current low-voltage amplifier direction.",
        "",
        "Simulation method: Python behavioral transfer model. I checked for a local SPICE engine and found Python only, so this is a comparative topology screen rather than transistor-level signoff. All candidates use +/-15 V rails, 8 ohm load, 1 kHz sine tests, Class AB bias, and Av = 10.",
        "",
        "Source preference: official `radio.ru`, `ftp.radio.ru`, and `archive.radio.ru` references remain primary. The five variants use concepts from Grechishkin 2013, Syrico 2017, Rogov 2018, and Petrov 2018 as recorded in `../radio_ru_bjt_amplifier_knowledge.md`.",
        "",
        f"## Selected Best: Variant {best.ident}",
        "",
        f"**{best.name}**",
        "",
        best.notes,
        "",
        f"Best schematic: `best_schematic.svg` and `schematics/variant_{best.ident}_{best.slug}.svg`.",
        "",
        "## Ranking",
        "",
        "| Rank | ID | Project Score | Unrestricted Score | 1 W THD % | 5 W THD % | 8 W THD % | Clean W @ 1% THD | Damping | Phase Margin | No-Global Align | Topology |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(rows, start=1):
        lines.append(
            f"| {i} | {r['id']} | {r['project_score']} | {r['unrestricted_score']} | {r['thd_1w_pct']} | "
            f"{r['thd_5w_pct']} | {r['thd_8w_pct']} | {r['clean_power_1pct_w']} | {r['damping_factor_8r']} | "
            f"{r['phase_margin_deg_est']} | {r['no_global_alignment']} | {r['name']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Variant 04 wins for the stated direction because it stays no-overall-feedback while using local CFP/Sziklai feedback where it is most useful: the output stage.",
            "- Variant 05 is the measurement-first option if global current feedback is allowed; it has the highest unrestricted score, but it violates the no-overall-feedback preference and needs the most stability proof.",
            "- Variant 03 is the safest fallback if CFP stability becomes troublesome: it gives good headroom and simpler loop behavior.",
            "- Variant 02 improves output impedance and crossover behavior, but triple emitter followers spend too much voltage on +/-15 V rails.",
            "- Variant 01 remains the debug-friendly baseline and should be breadboarded first if the goal is learning rather than maximum performance.",
            "",
            "## Generated Files",
            "",
            "- `results.csv`: numeric simulation/ranking table.",
            "- `all_5_schematics.svg`: one-page overview of the five variants.",
            "- `best_schematic.svg`: selected topology schematic.",
            "- `schematics/*.svg`: one transistor-symbol schematic per variant.",
            "- `behavioral_netlists/*.cir`: SPICE-like placeholders documenting topology and behavioral parameters.",
            "",
            f"Unrestricted performance winner: Variant {unrestricted['id']} ({unrestricted['name']}). Project winner: Variant {best.ident} ({best.name}).",
        ]
    )
    (ROOT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ROOT.mkdir(exist_ok=True)
    rows = variant_rows()
    write_csv(rows)
    write_netlists()
    write_schematics(rows)
    write_summary(rows)
    best = rows[0]
    print(f"Best project choice: {best['id']} - {best['name']} (score {best['project_score']})")
    print(f"Results: {ROOT / 'results.csv'}")
    print(f"Summary: {ROOT / 'summary.md'}")
    print(f"Overview: {ROOT / 'all_5_schematics.svg'}")
    print(f"Best schematic: {ROOT / 'best_schematic.svg'}")


if __name__ == "__main__":
    main()
