from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from circuitlib.analysis import (
    nearest_125_scale,
    read_operating_point,
    read_rows,
    rms,
    scale_label,
    waveform_y_limit,
)
from circuitlib.common import input_peak_from_swing_mvpp, normalize_text_file, write_text_lf
from circuitlib.plot import Plot
from circuitlib.spice import run_ngspice
from circuitlib.svg import (
    base_svg,
    capacitor_h,
    capacitor_v,
    ground,
    line,
    npn,
    poly,
    resistor_v,
    text,
)


RESULT_DIR = Path(__file__).resolve().parents[1]
DATA = RESULT_DIR / "data"
PLOTS = RESULT_DIR / "plots"
SCHEMATIC = RESULT_DIR / "schematic"
NETLISTS = RESULT_DIR / "netlists"
NETLIST = NETLISTS / "common_emitter_amp.cir"

VCC = 12.0
R1_VALUE = 110_000.0
R2_VALUE = 24_000.0
RC_VALUE = 5_600.0
RE_VALUE = 1_200.0
RLOAD_VALUE = 10_000.0
RSOURCE_VALUE = 1_000.0
CIN_UF = 1.0
COUT_UF = 10.0
CSUPPLY_UF = 100.0
CEMITTER_BYPASS_UF = 100.0
VIN_SWING_MVPP = 20.0
VIN_PEAK = input_peak_from_swing_mvpp(VIN_SWING_MVPP)


MODEL = """.model KT3102A NPN(Is=2e-14 Bf=100 Br=6 Vaf=100 Var=20 Ikf=0.12 Ikr=0.02
+ Rc=1 Re=0.35 Rb=60 Cje=9p Cjc=4p Tf=0.4n Tr=35n)"""


def value_label(value: float) -> str:
    if value >= 1_000_000.0:
        return f"{value / 1_000_000.0:g}M"
    if value >= 1000.0:
        return f"{value / 1000.0:g}k"
    return f"{value:g}"


def capacitor_label(value_uf: float) -> str:
    if value_uf >= 1.0:
        return f"{value_uf:g}u"
    return f"{value_uf * 1000:g}n"


def node(x: float, y: float) -> str:
    return f'<circle cx="{x:g}" cy="{y:g}" r="5" class="node"/>'


def common_emitter_schematic_svg() -> str:
    body: list[str] = [
        text(42, 42, "005 single-stage NPN common-emitter amplifier", 22, 700),
        text(42, 68, "Collector biased close to half of the 12 V supply; emitter resistor has an AC bypass capacitor", 13),
        line(220, 108, 760, 108),
        poly([(760, 100), (777, 108), (760, 116)], "wire"),
        text(795, 114, "+12 V", 18, 700),
        node(220, 108),
        node(300, 108),
        node(470, 108),
        *capacitor_v(220, 108, 230, f"C3 {capacitor_label(CSUPPLY_UF)}", "left", "top"),
        *ground(220, 230),
        *resistor_v(300, 108, 320, f"R1 {value_label(R1_VALUE)}", "left"),
        *resistor_v(300, 320, 500, f"R2 {value_label(R2_VALUE)}", "left"),
        *ground(300, 500),
        node(300, 320),
        text(42, 302, "Input", 16, 700),
        line(42, 320, 92, 320),
        *capacitor_h(92, 320, 242, f"C1 {capacitor_label(CIN_UF)}", "right"),
        line(242, 320, 386, 320),
        *npn(440, 320, "VT1 KT3102A"),
        line(300, 320, 386, 320),
        *resistor_v(470, 108, 275, f"RC {value_label(RC_VALUE)}", "right"),
        node(470, 275),
        line(470, 275, 530, 275),
        *capacitor_h(530, 275, 680, f"C2 {capacitor_label(COUT_UF)}", "left"),
        line(680, 275, 730, 275),
        node(730, 275),
        text(742, 280, "OUT", 14, 700),
        *resistor_v(730, 275, 500, f"Rload {value_label(RLOAD_VALUE)}", "right"),
        *ground(730, 500),
        *resistor_v(470, 365, 500, f"RE {value_label(RE_VALUE)}", "right"),
        line(470, 365, 560, 365),
        *capacitor_v(560, 365, 500, f"C4 {capacitor_label(CEMITTER_BYPASS_UF)}", "right", "top"),
        line(470, 500, 560, 500),
        *ground(470, 500),
    ]
    return base_svg(920, 620, body)


def main_netlist() -> str:
    return f"""* Single-stage NPN common-emitter amplifier, collector near half supply
.options abstol=1n reltol=0.003 itl1=500 itl4=500
.temp 27

VCC vcc 0 {VCC:g}
VIN src 0 DC 0 AC 1 SIN(0 {VIN_PEAK:.8g} 1k)
RS src input {RSOURCE_VALUE:g}
C1 input base {CIN_UF:g}u
R1 vcc base {R1_VALUE:g}
R2 base 0 {R2_VALUE:g}
RC vcc collector {RC_VALUE:g}
Q1 collector base emitter KT3102A
RE emitter 0 {RE_VALUE:g}
CE emitter 0 {CEMITTER_BYPASS_UF:g}u
C2 collector out {COUT_UF:g}u
RLOAD out 0 {RLOAD_VALUE:g}
C3 vcc 0 {CSUPPLY_UF:g}u

{MODEL}

.control
set noaskquit
op
print v(base) v(emitter) v(collector) v(out)
print i(vcc)
print @q1[ic] @q1[ib]
ac dec 80 5 500k
wrdata ac_response.csv frequency vdb(out) vp(out)
tran 5u 80m 60m
wrdata transient_1khz.csv time v(src) v(base) v(collector) v(out)
quit
.endc
.end
"""


def render_gain_plot() -> None:
    ac = read_rows(DATA / "ac_response.csv")
    gain_points = [(row[0], row[4]) for row in ac]
    max_gain = max(y for _, y in gain_points)
    min_gain = min(y for _, y in gain_points)
    ymin = math.floor((min_gain - 3.0) / 5.0) * 5.0
    ymax = math.ceil((max_gain + 3.0) / 5.0) * 5.0
    Plot(
        920,
        520,
        "Common-emitter AC voltage gain",
        "Frequency, Hz",
        "Gain, dB",
        True,
    ).render(
        [("gain", gain_points, "#1665d8")],
        PLOTS / "common_emitter_gain_vs_frequency.svg",
        5,
        500000,
        ymin,
        ymax,
        [10, 100, 1000, 10000, 100000],
        [tick for tick in range(int(ymin), int(ymax) + 1, 5)],
    )


def render_sine_plot() -> None:
    rows = read_rows(DATA / "transient_1khz.csv")
    t0 = rows[0][0]
    time_ms = [(row[0] - t0) * 1000.0 for row in rows]
    src_mv = [row[3] * 1000.0 for row in rows]
    base_mv = [(row[5] - sum(row[5] for row in rows) / len(rows)) * 1000.0 for row in rows]
    collector_mean = sum(row[7] for row in rows) / len(rows)
    collector_mv = [(row[7] - collector_mean) * 1000.0 for row in rows]
    out_mean = sum(row[9] for row in rows) / len(rows)
    out_mv = [(row[9] - out_mean) * 1000.0 for row in rows]
    output_max_abs = max(max(abs(value) for value in out_mv), max(abs(value) for value in collector_mv))
    src_max_abs = max(abs(value) for value in src_mv)
    src_scale = nearest_125_scale(output_max_abs / src_max_abs) if src_max_abs > 0 else 1.0
    src_scaled = [value * src_scale for value in src_mv]
    duration_ms = 4.0
    visible_values = [
        value
        for t, values in zip(time_ms, zip(out_mv, collector_mv, src_scaled, base_mv))
        if 0 <= t <= duration_ms
        for value in values
    ]
    ymax = waveform_y_limit(max(abs(value) for value in visible_values))
    Plot(
        920,
        520,
        f"Common-emitter sine response, 1 kHz, Vin = {VIN_SWING_MVPP:g} mVpp",
        "Time after 60 ms settling, ms",
        "AC voltage, mV",
    ).render(
        [
            ("load output", list(zip(time_ms, out_mv)), "#1665d8"),
            ("collector AC", list(zip(time_ms, collector_mv)), "#13795b"),
            (f"input x{scale_label(src_scale)}", list(zip(time_ms, src_scaled)), "#b54708"),
            ("base AC", list(zip(time_ms, base_mv)), "#7c3aed"),
        ],
        PLOTS / "common_emitter_sine_response_1khz.svg",
        0,
        duration_ms,
        -ymax,
        ymax,
        [0, 1, 2, 3, 4],
        [-ymax, -ymax / 2.0, 0, ymax / 2.0, ymax],
    )


def write_summary_csv() -> dict[str, float]:
    op = read_operating_point(DATA / "ngspice.log")
    rows = read_rows(DATA / "transient_1khz.csv")
    src = [row[3] for row in rows]
    out = [row[9] for row in rows]
    out_mean = sum(out) / len(out)
    out_ac = [value - out_mean for value in out]
    src_rms = rms(src)
    out_rms = rms(out_ac)
    gain = out_rms / src_rms if src_rms else 0.0
    ac = read_rows(DATA / "ac_response.csv")
    gain_1khz_db = min(ac, key=lambda row: abs(row[0] - 1000.0))[4]
    summary = {
        "v_base_v": op.get("v(base)", float("nan")),
        "v_emitter_v": op.get("v(emitter)", float("nan")),
        "v_collector_v": op.get("v(collector)", float("nan")),
        "collector_current_ma": abs(op.get("@q1[ic]", float("nan"))) * 1000.0,
        "supply_current_ma": abs(op.get("i(vcc)", float("nan"))) * 1000.0,
        "gain_1khz_v_v": gain,
        "gain_1khz_db": gain_1khz_db,
        "output_rms_mv": out_rms * 1000.0,
    }
    with (DATA / "summary.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)
    return summary


def write_readme(summary: dict[str, float]) -> None:
    readme = f"""# 005 single-stage NPN common-emitter amplifier

This result is a simple one-transistor common-emitter voltage amplifier.  The circuit uses a KT3102A-like NPN model, a base divider, an emitter resistor for DC stability, an emitter bypass capacitor for higher AC gain, and input/output coupling capacitors.

The main design target was to bias the collector near half of the 12 V supply so the collector can swing in both directions before clipping.  The chosen E24 values are:

- `R1`: {value_label(R1_VALUE)} from +12 V to base
- `R2`: {value_label(R2_VALUE)} from base to ground
- `RC`: {value_label(RC_VALUE)} collector resistor
- `RE`: {value_label(RE_VALUE)} emitter resistor
- `Rload`: {value_label(RLOAD_VALUE)}
- `C1`: {capacitor_label(CIN_UF)} input coupling
- `C2`: {capacitor_label(COUT_UF)} output coupling
- `C3`: {capacitor_label(CSUPPLY_UF)} supply bypass
- `C4`: {capacitor_label(CEMITTER_BYPASS_UF)} emitter bypass, positive terminal toward the emitter

## Operating point

ngspice DC operating point:

- Base voltage: `{summary["v_base_v"]:.3f} V`
- Emitter voltage: `{summary["v_emitter_v"]:.3f} V`
- Collector voltage: `{summary["v_collector_v"]:.3f} V`
- Collector current: `{summary["collector_current_ma"]:.3f} mA`
- Total supply current in this small-signal model: `{summary["supply_current_ma"]:.3f} mA`

## Simulation

At 1 kHz with `{VIN_SWING_MVPP:g} mVpp` input:

- Transient voltage gain: `{summary["gain_1khz_v_v"]:.2f} V/V`
- AC gain at 1 kHz: `{summary["gain_1khz_db"]:.2f} dB`
- Output RMS voltage: `{summary["output_rms_mv"]:.2f} mV`

![Schematic](schematic/common_emitter_amplifier.png)

![1 kHz sine response](plots/common_emitter_sine_response_1khz.png)

![AC gain](plots/common_emitter_gain_vs_frequency.png)

## Files

- `variants/common_emitter.py`: reusable circuit variant with schematic drawing, SPICE netlist, plots, and README generation.
- `schematic/common_emitter_amplifier.svg/png`: generated schematic.
- `netlists/common_emitter_amp.cir`: main ngspice netlist.
- `data/ngspice.log`: operating point and ngspice run log.
- `data/ac_response.csv`: AC gain/phase data.
- `data/transient_1khz.csv`: 1 kHz transient data.
- `data/summary.csv`: compact numeric summary.
"""
    write_text_lf(RESULT_DIR / "README.md", readme)


def run() -> None:
    for folder in [DATA, PLOTS, SCHEMATIC, NETLISTS]:
        folder.mkdir(parents=True, exist_ok=True)
    write_text_lf(SCHEMATIC / "common_emitter_amplifier.svg", common_emitter_schematic_svg())
    write_text_lf(NETLIST, main_netlist())
    run_ngspice(NETLIST, DATA / "ngspice.log", DATA)
    normalize_text_file(DATA / "ac_response.csv")
    normalize_text_file(DATA / "transient_1khz.csv")
    render_gain_plot()
    render_sine_plot()
    summary = write_summary_csv()
    write_readme(summary)


if __name__ == "__main__":
    run()
