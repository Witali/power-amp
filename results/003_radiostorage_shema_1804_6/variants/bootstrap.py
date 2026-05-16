from __future__ import annotations

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from circuitlib.analysis import (
    ceiling_125,
    harmonic_thd,
    nearest_125_scale,
    read_operating_point,
    read_rows,
    rms,
    scale_label,
    waveform_y_limit,
)
from circuitlib.common import input_peak_from_swing_mvpp, normalize_text_file, write_text_lf
from circuitlib.plot import Plot, render_sine_plot
from circuitlib.spice import run_ngspice
from circuitlib.svg import (
    base_svg,
    capacitor_h,
    capacitor_v,
    diode_v,
    ground,
    line,
    npn,
    pnp,
    poly,
    resistor_h,
    resistor_v,
    speaker_v,
    text,
)


RESULT_DIR = Path(__file__).resolve().parents[1]
DATA = RESULT_DIR / "data" / "bootstrap"
SWEEP = DATA / "sweep"
POWER_SWEEP = DATA / "power_sweep"
SQUARE = DATA / "square"
PLOTS = RESULT_DIR / "plots"
SCHEMATIC = RESULT_DIR / "schematic"
NETLISTS = RESULT_DIR / "netlists"
NETLIST = NETLISTS / "radiostorage_amp_bootstrap.cir"

RLOAD = 8.0
VIN_SWING_MVPP = 1000.0
VIN_PEAK = input_peak_from_swing_mvpp(VIN_SWING_MVPP)
POWER_SWEEP_FREQ_HZ = 1000.0
POWER_SWEEP_INPUT_MVPP = [20.0, 50.0, 100.0, 200.0, 500.0, 1000.0, 2000.0, 5000.0]
C2_VALUE_UF = 4700.0
R2_VALUE = 47000.0
R3_VALUE = 10000.0
RE_VT1_VALUE = 100.0
R1A_BOOT_VALUE = 560.0
R1B_BOOT_VALUE = 1800.0
CBOOT_VALUE_UF = 470.0


MODELS = """.model KD521A D(Is=2.5n Rs=1.8 N=1.85 Cjo=2p M=0.33 Bv=75 Ibv=5u Tt=4n)
.model KT3102A NPN(Is=2e-14 Bf=100 Br=6 Vaf=100 Var=20 Ikf=0.12 Ikr=0.02
+ Rc=1 Re=0.35 Rb=60 Cje=9p Cjc=4p Tf=0.4n Tr=35n)
.model KT817A NPN(Is=9e-14 Bf=50 Br=5 Vaf=70 Var=15 Ikf=3.0 Ikr=0.4
+ Rc=0.12 Re=0.06 Rb=2.5 Cje=140p Cjc=80p Tf=0.45u Tr=6u)
.model KT816A PNP(Is=1.1e-13 Bf=50 Br=5 Vaf=60 Var=15 Ikf=2.5 Ikr=0.35
+ Rc=0.14 Re=0.07 Rb=2.8 Cje=160p Cjc=90p Tf=0.55u Tr=7u)
"""


def bootstrap_schematic_svg() -> str:
    body: list[str] = [
        text(42, 42, "Reconstructed shema-1804-6 BJT audio amplifier, bootstrap variant", 22, 700),
        text(42, 68, "Upper bias feed split; C4 adds output swing to the upper transistor bias node", 13),
        line(300, 98, 965, 98),
        poly([(965, 90), (982, 98), (965, 106)], "wire"),
        text(1000, 104, "+12 V", 18, 700),
        '<circle cx="460" cy="98" r="5" class="node"/>',
        '<circle cx="730" cy="98" r="5" class="node"/>',
        *capacitor_v(300, 98, 220, "C1 1000u", "left", "top"),
        *ground(300, 220),
        *resistor_v(460, 98, 190, "R1A 560", "left"),
        '<circle cx="460" cy="190" r="5" class="node"/>',
        *resistor_v(460, 190, 282, "R1B 1.8k", "left"),
        '<circle cx="460" cy="282" r="5" class="node"/>',
        *diode_v(460, 282, 366, "VD1 KD521A"),
        *diode_v(460, 366, 450, "VD2 KD521A"),
        *capacitor_h(460, 190, 610, f"C4 {CBOOT_VALUE_UF:g}u", "left"),
        line(610, 190, 790, 190),
        line(790, 190, 790, 390),
        *npn(700, 282, "VT2 KT817A"),
        line(730, 237, 730, 98),
        line(460, 282, 646, 282),
        line(730, 327, 730, 405),
        '<circle cx="730" cy="390" r="5" class="node"/>',
        '<circle cx="790" cy="390" r="5" class="node"/>',
        line(730, 390, 820, 390),
        *pnp(700, 450, "VT3 KT816A"),
        line(730, 495, 730, 610),
        *ground(730, 610),
        text(838, 420, "OUT", 13, 700),
        *capacitor_h(820, 390, 965, f"C2 {C2_VALUE_UF:g}u", "left"),
        line(965, 390, 1018, 390),
        *speaker_v(1018, 390, 570, "B1 8 ohm"),
        *ground(1018, 570),
        text(972, 364, "speaker", 14, 700),
        text(42, 532, "Input", 16, 700),
        line(42, 540, 96, 540),
        *capacitor_h(96, 540, 252, "C3 10u", "right"),
        line(252, 540, 306, 540),
        '<circle cx="306" cy="540" r="5" class="node"/>',
        *resistor_v(306, 540, 670, "R3 10k", "left"),
        *ground(306, 670),
        *npn(430, 540, "VT1 KT3102A"),
        line(306, 540, 376, 540),
        line(460, 450, 460, 495),
        '<circle cx="460" cy="450" r="5" class="node"/>',
        line(460, 450, 646, 450),
        line(460, 585, 460, 610),
        *resistor_v(460, 610, 700, "R4 100", "right"),
        *ground(460, 700),
        *resistor_h(180, 430, 306, "R2 47k"),
        line(156, 430, 180, 430),
        text(130, 435, "OUT", 12, 700),
        line(306, 430, 306, 540),
    ]
    return base_svg(1160, 760, body)


def bootstrap_bias() -> str:
    return f"""R1A vcc boot {R1A_BOOT_VALUE:g}
R1B boot b_top {R1B_BOOT_VALUE:g}
C4 boot out {CBOOT_VALUE_UF:g}u"""


def circuit(vin_line: str, control: str) -> str:
    return f"""* Bootstrapped RadioStorage shema-1804-6 single-supply BJT audio amplifier
.options abstol=1n reltol=0.003 itl1=500 itl4=500
.temp 27

VCC vcc 0 12
{vin_line}
C3 vin b_in 10u
R3 b_in 0 {R3_VALUE:g}
R2 out b_in {R2_VALUE:g}
Q1 drive b_in e_vt1 KT3102A
R4 e_vt1 0 {RE_VT1_VALUE:g}
{bootstrap_bias()}
D1 b_top d_mid KD521A
D2 d_mid drive KD521A
Q2 vcc b_top out KT817A
Q3 0 drive out KT816A
C2 out load {C2_VALUE_UF:g}u
RLOAD load 0 {RLOAD:g}
C1 vcc 0 1000u

{MODELS}
{control}
.end
"""


def main_netlist() -> str:
    control = """.control
set noaskquit
op
print v(b_in) v(e_vt1) v(drive) v(b_top) v(boot) v(out) v(load)
print i(vcc)
print @q1[ic] @q2[ic] @q3[ic]
ac dec 80 5 200k
wrdata ac_response.csv frequency vdb(load) vp(load)
tran 5u 60m 40m
wrdata transient_1khz.csv time v(vin) v(b_in) v(out) v(load)
quit
.endc"""
    return circuit(f"VIN vin 0 DC 0 AC 1 SIN(0 {VIN_PEAK:.8g} 1k)", control)


def sweep_netlist(freq: float, vin_peak: float, out_csv: str) -> str:
    control = f""".control
set noaskquit
tran {1.0 / (freq * 256.0):.10g} {24.0 / freq:.10g} {12.0 / freq:.10g} {1.0 / (freq * 256.0):.10g}
wrdata {out_csv} time v(load) v(vin)
quit
.endc"""
    return circuit(f"VIN vin 0 DC 0 SIN(0 {vin_peak:.8g} {freq:.8g})", control)


def square_netlist(freq: float, vin_peak: float, out_csv: str) -> str:
    period = 1.0 / freq
    rise = min(1e-6, period / 100.0)
    step = period / 512.0
    settle = 0.060
    stop = settle + 4.0 * period
    control = f""".control
set noaskquit
tran {step:.10g} {stop:.10g} {settle:.10g} {step:.10g}
wrdata {out_csv} time v(vin) v(load) v(out)
quit
.endc"""
    vin = f"VIN vin 0 DC 0 PULSE({-vin_peak:.8g} {vin_peak:.8g} 0 {rise:.8g} {rise:.8g} {period / 2.0:.8g} {period:.8g})"
    return circuit(vin, control)


def run_frequency_sweep() -> list[dict[str, float]]:
    SWEEP.mkdir(parents=True, exist_ok=True)
    freqs = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
    rows: list[dict[str, float]] = []
    for freq in freqs:
        tag = f"{int(freq):05d}hz"
        netlist = SWEEP / f"bootstrap_sweep_{tag}.cir"
        csv_path = SWEEP / f"bootstrap_sweep_{tag}.csv"
        log = SWEEP / f"bootstrap_sweep_{tag}.log"
        write_text_lf(netlist, sweep_netlist(freq, VIN_PEAK, csv_path.name))
        run_ngspice(netlist, log, SWEEP)
        normalize_text_file(csv_path)
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
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def run_power_sweep() -> list[dict[str, float]]:
    POWER_SWEEP.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, float]] = []
    for swing_mvpp in POWER_SWEEP_INPUT_MVPP:
        vin_peak = input_peak_from_swing_mvpp(swing_mvpp)
        tag = f"{int(swing_mvpp):05d}mvpp"
        netlist = POWER_SWEEP / f"bootstrap_power_sweep_{tag}.cir"
        csv_path = POWER_SWEEP / f"bootstrap_power_sweep_{tag}.csv"
        log = POWER_SWEEP / f"bootstrap_power_sweep_{tag}.log"
        write_text_lf(netlist, sweep_netlist(POWER_SWEEP_FREQ_HZ, vin_peak, csv_path.name))
        run_ngspice(netlist, log, POWER_SWEEP)
        normalize_text_file(csv_path)
        data = read_rows(csv_path)
        times = [row[0] for row in data]
        load = [row[3] for row in data]
        vin = [row[5] for row in data]
        load_centered = [v - sum(load) / len(load) for v in load]
        load_rms = rms(load_centered)
        vin_rms = rms(vin)
        thd, fundamental_rms = harmonic_thd(times, load, POWER_SWEEP_FREQ_HZ)
        rows.append(
            {
                "frequency_hz": POWER_SWEEP_FREQ_HZ,
                "vin_swing_mvpp": swing_mvpp,
                "vin_rms_v": vin_rms,
                "vout_rms_v": load_rms,
                "fundamental_rms_v": fundamental_rms,
                "gain_v_v": load_rms / vin_rms if vin_rms else 0.0,
                "power_w": load_rms * load_rms / RLOAD,
                "thd_percent": thd,
                "load_pp_v": max(load) - min(load),
            }
        )

    out = DATA / "power_sweep_1khz.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def run_square_responses() -> list[dict[str, float]]:
    SQUARE.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, float]] = []
    for freq in [1000.0, 10000.0]:
        tag = "1khz" if freq == 1000.0 else "10khz"
        netlist = SQUARE / f"bootstrap_square_response_{tag}.cir"
        csv_path = SQUARE / f"bootstrap_square_response_{tag}.csv"
        log = SQUARE / f"bootstrap_square_response_{tag}.log"
        write_text_lf(netlist, square_netlist(freq, VIN_PEAK, csv_path.name))
        run_ngspice(netlist, log, SQUARE)
        normalize_text_file(csv_path)
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
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary)
    return summary


def render_square_plot(freq: float) -> None:
    tag = "1khz" if freq == 1000.0 else "10khz"
    rows = read_rows(SQUARE / f"bootstrap_square_response_{tag}.csv")
    t0 = rows[0][0]
    time_ms = [(row[0] - t0) * 1000.0 for row in rows]
    load = [row[5] for row in rows]
    vin_raw = [row[3] for row in rows]
    load_max_abs = max(abs(v) for v in load)
    vin_max_abs = max(abs(v) for v in vin_raw)
    vin_scale = nearest_125_scale(load_max_abs / vin_max_abs) if vin_max_abs > 0 else 1.0
    vin = [value * vin_scale for value in vin_raw]
    max_abs = max(load_max_abs, max(abs(v) for v in vin))
    ymax = waveform_y_limit(max_abs)
    duration_ms = 4.0 / freq * 1000.0
    x_ticks = [0, 1, 2, 3, 4] if freq == 1000.0 else [0, 0.1, 0.2, 0.3, 0.4]
    y_ticks = [-ymax, -ymax / 2.0, 0, ymax / 2.0, ymax]
    Plot(
        920,
        520,
        f"Bootstrap square response, {freq / 1000:g} kHz, Vin = {VIN_SWING_MVPP:g} mVpp",
        "Time after 60 ms settling, ms",
        "Voltage, V",
    ).render(
        [
            ("load output", list(zip(time_ms, load)), "#1665d8"),
            (f"input x{scale_label(vin_scale)}", list(zip(time_ms, vin)), "#b54708"),
        ],
        PLOTS / f"bootstrap_square_response_{tag}.svg",
        0,
        duration_ms,
        -ymax,
        ymax,
        x_ticks,
        y_ticks,
    )


def render_outputs(
    sweep_rows: list[dict[str, float]],
    power_rows: list[dict[str, float]],
    square_rows: list[dict[str, float]],
) -> None:
    ac = read_rows(DATA / "ac_response.csv")
    gain_points = [(row[0], row[4]) for row in ac]
    phase_points = [(row[0], row[6]) for row in ac]
    Plot(920, 520, "Bootstrap AC gain and phase, load = 8 ohm", "Frequency, Hz", "Gain dB / phase deg", True).render(
        [("gain, dB", gain_points, "#1665d8"), ("phase, deg", phase_points, "#b54708")],
        PLOTS / "bootstrap_gain_vs_frequency.svg",
        5,
        200000,
        -20,
        45,
        [10, 100, 1000, 10000, 100000],
        [-20, 0, 20, 40],
    )

    max_thd = max(row["thd_percent"] for row in sweep_rows)
    thd_ymax = ceiling_125(max(1.0, max_thd * 1.25))
    Plot(920, 520, f"Bootstrap THD vs frequency, Vin = {VIN_SWING_MVPP:g} mVpp", "Frequency, Hz", "THD, %", True).render(
        [("THD", [(row["frequency_hz"], row["thd_percent"]) for row in sweep_rows], "#13795b")],
        PLOTS / "bootstrap_thd_vs_frequency.svg",
        20,
        20000,
        0,
        thd_ymax,
        [20, 50, 100, 1000, 10000, 20000],
        [0, thd_ymax / 4, thd_ymax / 2, thd_ymax * 3 / 4, thd_ymax],
    )

    power_points = [(row["frequency_hz"], row["power_w"] * 1000.0) for row in sweep_rows]
    max_power = max(y for _, y in power_points)
    if max_power < 0.01:
        power_points = [(row["frequency_hz"], row["power_w"] * 1_000_000.0) for row in sweep_rows]
        power_unit = "uW"
    else:
        power_unit = "mW"
    max_power = max(y for _, y in power_points)
    power_ymax = ceiling_125(max_power * 1.25)
    Plot(920, 520, f"Bootstrap output power vs frequency, Vin = {VIN_SWING_MVPP:g} mVpp", "Frequency, Hz", f"Power, {power_unit} into 8 ohm", True).render(
        [("Pout", power_points, "#1665d8")],
        PLOTS / "bootstrap_output_power_vs_frequency.svg",
        20,
        20000,
        0,
        power_ymax,
        [20, 50, 100, 1000, 10000, 20000],
        [0, power_ymax / 4, power_ymax / 2, power_ymax * 3 / 4, power_ymax],
    )

    thd_power_points = [(row["power_w"] * 1000.0, row["thd_percent"]) for row in power_rows if row["power_w"] > 0]
    min_thd_power = min(x for x, _ in thd_power_points)
    max_thd_power = max(x for x, _ in thd_power_points)
    thd_power_ticks = [tick for tick in [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000] if min_thd_power <= tick <= max_thd_power]
    if not thd_power_ticks:
        thd_power_ticks = [min_thd_power, max_thd_power]
    thd_power_ymax = ceiling_125(max(1.0, max(y for _, y in thd_power_points) * 1.25))
    Plot(
        920,
        520,
        "Bootstrap THD vs output power, 1 kHz",
        "Output power, mW into 8 ohm",
        "THD, %",
        True,
    ).render(
        [("THD", thd_power_points, "#7c3aed")],
        PLOTS / "bootstrap_thd_vs_output_power_1khz.svg",
        min_thd_power,
        max_thd_power,
        0,
        thd_power_ymax,
        thd_power_ticks,
        [0, thd_power_ymax / 4, thd_power_ymax / 2, thd_power_ymax * 3 / 4, thd_power_ymax],
    )

    render_sine_plot(
        DATA / "transient_1khz.csv",
        PLOTS / "bootstrap_sine_response_1khz.svg",
        f"Bootstrap sine-wave response, 1 kHz, Vin = {VIN_SWING_MVPP:g} mVpp",
    )

    for row in square_rows:
        render_square_plot(row["frequency_hz"])


def write_readme(
    sweep_rows: list[dict[str, float]],
    power_rows: list[dict[str, float]],
    square_rows: list[dict[str, float]],
) -> None:
    at_1k = min(sweep_rows, key=lambda row: abs(row["frequency_hz"] - 1000))
    max_power_row = max(power_rows, key=lambda row: row["power_w"])
    square_1k = min(square_rows, key=lambda row: abs(row["frequency_hz"] - 1000))
    square_10k = min(square_rows, key=lambda row: abs(row["frequency_hz"] - 10000))
    transient = read_rows(DATA / "transient_1khz.csv")
    sine_vin = [row[3] for row in transient]
    sine_amp_out = [row[7] for row in transient]
    sine_load = [row[9] for row in transient]
    sine_headroom = min(min(sine_amp_out), 12.0 - max(sine_amp_out))
    sine_load_pp = max(sine_load) - min(sine_load)
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
    rail_limited_pp = 2.0 * min(op_out, 12.0 - op_out)
    rail_half_pp = rail_limited_pp / 2.0
    text_body = f"""# 003 RadioStorage shema-1804-6 Bootstrap Reconstruction

This folder contains a local reconstruction of the amplifier schematic from:

`https://radiostorage.net/uploads/Image/schemes/18/shema-1804-6.png`

Only the voltage-addition/bootstrap variant is kept here. The earlier no-bootstrap reconstruction was removed from the published schematic, plots, netlists, and main result data because this variant is now the working design.

## GitHub Preview

### Source Image

![Original RadioStorage schematic](source/shema-1804-6.png)

### Reconstructed Schematic

![Reconstructed bootstrap amplifier schematic](schematic/reconstructed_amplifier_bootstrap.png)

### Simulation Plots

![1 kHz sine-wave response](plots/bootstrap_sine_response_1khz.png)

![AC gain and phase](plots/bootstrap_gain_vs_frequency.png)

![THD vs frequency](plots/bootstrap_thd_vs_frequency.png)

![THD vs output power](plots/bootstrap_thd_vs_output_power_1khz.png)

![Output power vs frequency](plots/bootstrap_output_power_vs_frequency.png)

![1 kHz square-wave response](plots/bootstrap_square_response_1khz.png)

![10 kHz square-wave response](plots/bootstrap_square_response_10khz.png)

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

## 1 kHz THD vs Output Power

The new power sweep uses 1-2-5 input steps from `{POWER_SWEEP_INPUT_MVPP[0]:g}` to `{POWER_SWEEP_INPUT_MVPP[-1]:g}` mVpp at 1 kHz. The largest simulated point is about `{max_power_row["power_w"] * 1000:.2f} mW` into 8 ohm with `{max_power_row["thd_percent"]:.2f} %` THD. The graph is intended as a comparative simulation result for this simplified transistor model, not as a guaranteed measurement for real KT816/KT817 parts.

## Input Level Choice

The DC output node is close to half supply, so the theoretical rail-limited symmetric swing is about `{rail_limited_pp:.2f} Vpp`, and half of that would be about `{rail_half_pp:.2f} Vpp`. This simplified model compresses before it can produce that cleanly. A 1-2-5 series input-level sweep selected `{VIN_SWING_MVPP:g} mVpp` as the practical larger-signal test point; it gives about `{sine_load_pp:.2f} Vpp` at the load on the 1 kHz sine plot, roughly half of the largest useful simulated swing before strong compression.

## Non-Clipping Check

The selected transient input level is intentionally small so the simulated output does not clip.

- Sine input swing: `{max(sine_vin) - min(sine_vin):.4f} Vpp`.
- Output node before C2: `{min(sine_amp_out):.4f}..{max(sine_amp_out):.4f} V`.
- Rail headroom at that node: at least `{sine_headroom:.4f} V`.
- Speaker/load swing after C2: `{sine_load_pp:.4f} Vpp`.

## Square-Wave Response

Square-wave transient runs use the same {VIN_SWING_MVPP:g} mVpp input and show the load voltage after 60 ms of settling.

- 1 kHz: load swing about `{square_1k["load_pp_v"]:.3f} Vpp`.
- 10 kHz: load swing about `{square_10k["load_pp_v"]:.3f} Vpp`.

## Reusable Runner

The concrete circuit variant lives in `variants/bootstrap.py`, while the shared runner and helpers live under `scripts/`.
Run the complete regeneration flow from the repository root with:

```powershell
python scripts\\run_circuit_result.py results\\003_radiostorage_shema_1804_6\\variants\\bootstrap.py
```

## Files

- `source/shema-1804-6.png`: original downloaded image.
- `variants/bootstrap.py`: reusable circuit variant with schematic drawing, SPICE netlists, measurements, and result description.
- `schematic/reconstructed_amplifier_bootstrap.svg/png`: redrawn bootstrap/voltage-addition schematic using transistor symbols.
- `netlists/radiostorage_amp_bootstrap.cir`: main ngspice netlist.
- `data/bootstrap/ac_response.csv`: AC gain/phase data from ngspice.
- `data/bootstrap/transient_1khz.csv`: 1 kHz transient data from ngspice.
- `data/bootstrap/frequency_sweep.csv`: frequency sweep with power and THD estimates.
- `data/bootstrap/power_sweep_1khz.csv`: 1 kHz input-level sweep with THD versus output power.
- `data/bootstrap/square/*.csv`: 1 kHz and 10 kHz square-wave transient data.
- `plots/bootstrap_*.svg/png`: generated plots for the voltage-addition variant.
"""
    write_text_lf(RESULT_DIR / "README.md", text_body)


def run() -> None:
    for folder in [DATA, SWEEP, POWER_SWEEP, SQUARE, PLOTS, SCHEMATIC, NETLISTS]:
        folder.mkdir(parents=True, exist_ok=True)
    write_text_lf(SCHEMATIC / "reconstructed_amplifier_bootstrap.svg", bootstrap_schematic_svg())
    write_text_lf(NETLIST, main_netlist())
    run_ngspice(NETLIST, DATA / "ngspice.log", DATA)
    normalize_text_file(DATA / "ac_response.csv")
    normalize_text_file(DATA / "transient_1khz.csv")
    sweep_rows = run_frequency_sweep()
    power_rows = run_power_sweep()
    square_rows = run_square_responses()
    render_outputs(sweep_rows, power_rows, square_rows)
    write_readme(sweep_rows, power_rows, square_rows)


if __name__ == "__main__":
    run()
