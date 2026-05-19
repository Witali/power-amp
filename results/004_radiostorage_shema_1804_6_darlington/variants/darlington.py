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
DATA = RESULT_DIR / "data" / "darlington"
SWEEP = DATA / "sweep"
POWER_SWEEP = DATA / "power_sweep"
SQUARE = DATA / "square"
PLOTS = RESULT_DIR / "plots"
SCHEMATIC = RESULT_DIR / "schematic"
NETLISTS = RESULT_DIR / "netlists"
NETLIST = NETLISTS / "radiostorage_amp_darlington.cir"

RLOAD = 8.0
VIN_SWING_MVPP = 1000.0
VIN_PEAK = input_peak_from_swing_mvpp(VIN_SWING_MVPP)
THD_FREQUENCY_TARGET_POWERS_MW = [20.0, 50.0, 100.0]
POWER_SWEEP_FREQS_HZ = [100.0, 500.0, 1000.0, 5000.0, 10000.0]
POWER_SWEEP_INPUT_MVPP = [20.0, 50.0, 100.0, 200.0, 500.0, 1000.0, 2000.0, 5000.0]
C2_VALUE_UF = 4700.0
R2_VALUE = 62000.0
R3_VALUE = 10000.0
RE_VT1_VALUE = 51.0
R1A_BOOT_VALUE = 620.0
R1B_BOOT_VALUE = 3300.0
CBOOT_VALUE_UF = 470.0


MODELS = """.model KD521A D(Is=2.5n Rs=1.8 N=1.85 Cjo=2p M=0.33 Bv=75 Ibv=5u Tt=4n)
.model KT3102A NPN(Is=2e-14 Bf=100 Br=6 Vaf=100 Var=20 Ikf=0.12 Ikr=0.02
+ Rc=1 Re=0.35 Rb=60 Cje=9p Cjc=4p Tf=0.4n Tr=35n)
.model KT817A NPN(Is=9e-14 Bf=50 Br=5 Vaf=70 Var=15 Ikf=3.0 Ikr=0.4
+ Rc=0.12 Re=0.06 Rb=2.5 Cje=140p Cjc=80p Tf=0.45u Tr=6u)
.model KT816A PNP(Is=1.1e-13 Bf=50 Br=5 Vaf=60 Var=15 Ikf=2.5 Ikr=0.35
+ Rc=0.14 Re=0.07 Rb=2.8 Cje=160p Cjc=90p Tf=0.55u Tr=7u)
"""


def diode_v_left_label(x: float, y1: float, y2: float, label: str) -> list[str]:
    mid = (y1 + y2) / 2.0
    return [
        line(x, y1, x, mid - 24),
        poly([(x - 22, mid - 24), (x + 22, mid - 24), (x, mid + 8), (x - 22, mid - 24)], "wire"),
        line(x - 22, mid + 14, x + 22, mid + 14),
        line(x, mid + 14, x, y2),
        text(x - 34, mid + 4, label, 14, 700, "end"),
    ]


def resistor_value_label(value: float) -> str:
    if value >= 1000.0:
        scaled = value / 1000.0
        return f"{scaled:g}k"
    return f"{value:g}"


def darlington_schematic_svg() -> str:
    body: list[str] = [
        text(42, 42, "004 shema-1804-6 BJT audio amplifier, upper Darlington variant", 22, 700),
        text(42, 68, "Based on 003 bootstrap circuit; VT2A + VT2B form the upper Darlington emitter follower", 13),
        line(300, 98, 1080, 98),
        poly([(1080, 90), (1097, 98), (1080, 106)], "wire"),
        text(1115, 104, "+12 V", 18, 700),
        '<circle cx="460" cy="98" r="5" class="node"/>',
        '<circle cx="720" cy="98" r="5" class="node"/>',
        '<circle cx="870" cy="98" r="5" class="node"/>',
        *capacitor_v(300, 98, 220, "C1 1000u", "left", "top"),
        *ground(300, 220),
        *resistor_v(460, 98, 195, f"R1A {resistor_value_label(R1A_BOOT_VALUE)}", "left"),
        '<circle cx="460" cy="195" r="5" class="node"/>',
        *resistor_v(460, 195, 295, f"R1B {resistor_value_label(R1B_BOOT_VALUE)}", "left"),
        '<circle cx="460" cy="295" r="5" class="node"/>',
        *diode_v_left_label(460, 295, 355, "VD1 KD521A"),
        *diode_v_left_label(460, 355, 415, "VD2 KD521A"),
        *diode_v_left_label(460, 415, 475, "VD3 KD521A"),
        line(460, 475, 460, 510),
        line(460, 195, 500, 195),
        line(500, 195, 500, 225),
        line(500, 225, 520, 225),
        *capacitor_h(520, 225, 620, f"C4 {CBOOT_VALUE_UF:g}u", "left"),
        line(620, 225, 660, 225),
        text(676, 230, "OUT", 12, 700),
        line(950, 385, 950, 770),
        *npn(690, 295, ""),
        text(628, 372, "VT2A KT3102A", 14, 700, "middle"),
        line(720, 250, 720, 98),
        line(460, 295, 636, 295),
        *npn(840, 340, ""),
        text(912, 334, "VT2B KT817A", 14, 700),
        line(870, 295, 870, 98),
        line(720, 340, 786, 340),
        line(870, 385, 950, 385),
        '<circle cx="950" cy="385" r="5" class="node"/>',
        *pnp(840, 510, "VT3 KT816A"),
        line(870, 465, 950, 465),
        '<circle cx="950" cy="465" r="5" class="node"/>',
        line(870, 555, 870, 670),
        *ground(870, 670),
        '<circle cx="950" cy="425" r="5" class="node"/>',
        text(970, 450, "OUT", 13, 700),
        line(950, 425, 990, 425),
        *capacitor_h(990, 425, 1135, f"C2 {C2_VALUE_UF:g}u", "left"),
        line(1135, 425, 1190, 425),
        *speaker_v(1190, 425, 603, "B1 8 ohm"),
        *ground(1190, 603),
        text(1144, 399, "speaker", 14, 700),
        text(42, 547, "Input", 16, 700),
        line(42, 555, 96, 555),
        *capacitor_h(96, 555, 252, "C3 10u", "right"),
        line(252, 555, 306, 555),
        '<circle cx="306" cy="555" r="5" class="node"/>',
        *resistor_v(306, 555, 695, "R3 10k", "left"),
        *ground(306, 695),
        *npn(430, 555, "VT1 KT3102A"),
        line(306, 555, 376, 555),
        '<circle cx="460" cy="510" r="5" class="node"/>',
        line(460, 510, 786, 510),
        line(460, 600, 460, 620),
        *resistor_v(460, 620, 735, f"R4 {resistor_value_label(RE_VT1_VALUE)}", "right"),
        *ground(460, 735),
        *resistor_h(180, 450, 306, f"R2 {resistor_value_label(R2_VALUE)}"),
        line(24, 770, 950, 770),
        line(24, 450, 24, 770),
        line(24, 450, 180, 450),
        line(306, 450, 306, 555),
    ]
    return base_svg(1320, 840, body)


def darlington_bias() -> str:
    return f"""R1A vcc boot {R1A_BOOT_VALUE:g}
R1B boot b_top {R1B_BOOT_VALUE:g}
C4 boot out {CBOOT_VALUE_UF:g}u"""


def circuit(vin_line: str, control: str) -> str:
    return f"""* RadioStorage shema-1804-6 single-supply BJT audio amplifier, upper Darlington variant
.options abstol=1n reltol=0.003 itl1=500 itl4=500
.temp 27

VCC vcc 0 12
{vin_line}
C3 vin b_in 10u
R3 b_in 0 {R3_VALUE:g}
R2 out b_in {R2_VALUE:g}
Q1 drive b_in e_vt1 KT3102A
R4 e_vt1 0 {RE_VT1_VALUE:g}
{darlington_bias()}
D1 b_top d_mid1 KD521A
D2 d_mid1 d_mid2 KD521A
D3 d_mid2 drive KD521A
Q2A vcc b_top b_upper KT3102A
Q2B vcc b_upper out KT817A
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
print v(b_in) v(e_vt1) v(drive) v(d_mid1) v(d_mid2) v(b_top) v(b_upper) v(boot) v(out) v(load)
print i(vcc)
print @q1[ic] @q2a[ic] @q2b[ic] @q3[ic]
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


def measure_sine_point(freq: float, vin_peak: float, folder: Path, stem: str) -> dict[str, float]:
    netlist = folder / f"{stem}.cir"
    csv_path = folder / f"{stem}.csv"
    log = folder / f"{stem}.log"
    write_text_lf(netlist, sweep_netlist(freq, vin_peak, csv_path.name))
    run_ngspice(netlist, log, folder)
    normalize_text_file(csv_path)
    data = read_rows(csv_path)
    times = [row[0] for row in data]
    load = [row[3] for row in data]
    vin = [row[5] for row in data]
    load_center = sum(load) / len(load)
    load_centered = [v - load_center for v in load]
    load_rms = rms(load_centered)
    vin_rms = rms(vin)
    thd, fundamental_rms = harmonic_thd(times, load, freq)
    return {
        "frequency_hz": float(freq),
        "vin_peak_v": vin_peak,
        "vin_swing_mvpp": vin_peak * 2000.0,
        "vin_rms_v": vin_rms,
        "vout_rms_v": load_rms,
        "fundamental_rms_v": fundamental_rms,
        "gain_v_v": load_rms / vin_rms if vin_rms else 0.0,
        "power_w": load_rms * load_rms / RLOAD,
        "thd_percent": thd,
        "load_pp_v": max(load) - min(load),
        "load_min_v": min(load),
        "load_max_v": max(load),
    }


def run_frequency_sweep() -> list[dict[str, float]]:
    SWEEP.mkdir(parents=True, exist_ok=True)
    freqs = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
    rows: list[dict[str, float]] = []
    for target_mw in THD_FREQUENCY_TARGET_POWERS_MW:
        target_w = target_mw / 1000.0
        for freq in freqs:
            tag = f"{int(freq):05d}hz_{int(target_mw):03d}mw"
            low_peak = 0.0
            high_peak = VIN_PEAK
            high_point = measure_sine_point(freq, high_peak, SWEEP, f"darlington_sweep_{tag}_high1")
            high_index = 1
            while high_point["power_w"] < target_w and high_peak < 4.0:
                high_index += 1
                high_peak = min(4.0, high_peak * 1.8)
                high_point = measure_sine_point(freq, high_peak, SWEEP, f"darlington_sweep_{tag}_high{high_index}")

            best_point = high_point
            for iteration in range(7):
                mid_peak = (low_peak + high_peak) / 2.0
                point = measure_sine_point(freq, mid_peak, SWEEP, f"darlington_sweep_{tag}_b{iteration + 1}")
                if abs(point["power_w"] - target_w) < abs(best_point["power_w"] - target_w):
                    best_point = point
                if point["power_w"] < target_w:
                    low_peak = mid_peak
                else:
                    high_peak = mid_peak

            best_point["target_power_mw"] = target_mw
            rows.append(best_point)

    out = DATA / "frequency_sweep.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def run_power_sweep() -> list[dict[str, float]]:
    POWER_SWEEP.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, float]] = []
    for freq in POWER_SWEEP_FREQS_HZ:
        for swing_mvpp in POWER_SWEEP_INPUT_MVPP:
            vin_peak = input_peak_from_swing_mvpp(swing_mvpp)
            tag = f"{int(freq):05d}hz_{int(swing_mvpp):05d}mvpp"
            point = measure_sine_point(freq, vin_peak, POWER_SWEEP, f"darlington_power_sweep_{tag}")
            rows.append(point)

    out = DATA / "power_sweep.csv"
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
        netlist = SQUARE / f"darlington_square_response_{tag}.cir"
        csv_path = SQUARE / f"darlington_square_response_{tag}.csv"
        log = SQUARE / f"darlington_square_response_{tag}.log"
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
    rows = read_rows(SQUARE / f"darlington_square_response_{tag}.csv")
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
        f"Darlington square response, {freq / 1000:g} kHz, Vin = {VIN_SWING_MVPP:g} mVpp",
        "Time after 60 ms settling, ms",
        "Voltage, V",
    ).render(
        [
            ("load output", list(zip(time_ms, load)), "#1665d8"),
            (f"input x{scale_label(vin_scale)}", list(zip(time_ms, vin)), "#b54708"),
        ],
        PLOTS / f"darlington_square_response_{tag}.svg",
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
    Plot(920, 520, "Darlington AC gain and phase, load = 8 ohm", "Frequency, Hz", "Gain dB / phase deg", True).render(
        [("gain, dB", gain_points, "#1665d8"), ("phase, deg", phase_points, "#b54708")],
        PLOTS / "darlington_gain_vs_frequency.svg",
        5,
        200000,
        -20,
        45,
        [10, 100, 1000, 10000, 100000],
        [-20, 0, 20, 40],
    )

    thd_series: list[tuple[str, list[tuple[float, float]], str]] = []
    colors = ["#13795b", "#1665d8", "#b54708"]
    for index, target_mw in enumerate(THD_FREQUENCY_TARGET_POWERS_MW):
        points = [
            (row["frequency_hz"], row["thd_percent"])
            for row in sweep_rows
            if abs(row["target_power_mw"] - target_mw) < 1e-9
        ]
        thd_series.append((f"{target_mw:g} mW", points, colors[index % len(colors)]))
    max_thd = max(row["thd_percent"] for row in sweep_rows)
    thd_ymax = ceiling_125(max(1.0, max_thd * 1.25))
    Plot(920, 520, "Darlington THD vs frequency at fixed output power", "Frequency, Hz", "THD, %", True).render(
        thd_series,
        PLOTS / "darlington_thd_vs_frequency.svg",
        20,
        20000,
        0,
        thd_ymax,
        [20, 50, 100, 1000, 10000, 20000],
        [0, thd_ymax / 4, thd_ymax / 2, thd_ymax * 3 / 4, thd_ymax],
    )

    power_series: list[tuple[str, list[tuple[float, float]], str]] = []
    for index, target_mw in enumerate(THD_FREQUENCY_TARGET_POWERS_MW):
        points = [
            (row["frequency_hz"], row["power_w"] * 1000.0)
            for row in sweep_rows
            if abs(row["target_power_mw"] - target_mw) < 1e-9
        ]
        power_series.append((f"{target_mw:g} mW target", points, colors[index % len(colors)]))
    max_power = max(row["power_w"] * 1000.0 for row in sweep_rows)
    power_ymax = ceiling_125(max_power * 1.25)
    Plot(920, 520, "Darlington output power vs frequency", "Frequency, Hz", "Power, mW into 8 ohm", True).render(
        power_series,
        PLOTS / "darlington_output_power_vs_frequency.svg",
        20,
        20000,
        0,
        power_ymax,
        [20, 50, 100, 1000, 10000, 20000],
        [0, power_ymax / 4, power_ymax / 2, power_ymax * 3 / 4, power_ymax],
    )

    thd_power_series: list[tuple[str, list[tuple[float, float]], str]] = []
    power_colors = ["#7c3aed", "#13795b", "#1665d8", "#b54708", "#93370d"]
    all_power_points: list[tuple[float, float]] = []
    for index, freq in enumerate(POWER_SWEEP_FREQS_HZ):
        points = [
            (row["power_w"] * 1000.0, row["thd_percent"])
            for row in power_rows
            if abs(row["frequency_hz"] - freq) < 1e-9 and row["power_w"] > 0
        ]
        points.sort()
        all_power_points.extend(points)
        label = f"{freq / 1000:g} kHz" if freq >= 1000 else f"{freq:g} Hz"
        thd_power_series.append((label, points, power_colors[index % len(power_colors)]))
    min_thd_power = min(x for x, _ in all_power_points)
    max_thd_power = max(x for x, _ in all_power_points)
    thd_power_ticks = [
        tick
        for tick in [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
        if min_thd_power <= tick <= max_thd_power
    ]
    if not thd_power_ticks:
        thd_power_ticks = [min_thd_power, max_thd_power]
    thd_power_ymax = ceiling_125(max(1.0, max(y for _, y in all_power_points) * 1.25))
    Plot(
        920,
        520,
        "Darlington THD vs output power",
        "Output power, mW into 8 ohm",
        "THD, %",
        True,
    ).render(
        thd_power_series,
        PLOTS / "darlington_thd_vs_output_power.svg",
        min_thd_power,
        max_thd_power,
        0,
        thd_power_ymax,
        thd_power_ticks,
        [0, thd_power_ymax / 4, thd_power_ymax / 2, thd_power_ymax * 3 / 4, thd_power_ymax],
    )

    render_sine_plot(
        DATA / "transient_1khz.csv",
        PLOTS / "darlington_sine_response_1khz.svg",
        f"Darlington sine-wave response, 1 kHz, Vin = {VIN_SWING_MVPP:g} mVpp",
    )

    for row in square_rows:
        render_square_plot(row["frequency_hz"])


def write_readme(
    sweep_rows: list[dict[str, float]],
    power_rows: list[dict[str, float]],
    square_rows: list[dict[str, float]],
) -> None:
    at_1k_100mw = min(
        (row for row in sweep_rows if abs(row["target_power_mw"] - 100.0) < 1e-9),
        key=lambda row: abs(row["frequency_hz"] - 1000),
    )
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
    op_b_upper = op.get("v(b_upper)", float("nan"))
    op_out = op.get("v(out)", float("nan"))
    op_load = op.get("v(load)", float("nan"))
    op_q2a_ma = abs(op.get("@q2a[ic]", float("nan"))) * 1000.0
    op_q2b_ma = abs(op.get("@q2b[ic]", float("nan"))) * 1000.0
    op_q3_ma = abs(op.get("@q3[ic]", float("nan"))) * 1000.0
    op_supply_ma = abs(op.get("i(vcc)", float("nan"))) * 1000.0
    text_body = f"""# 004 RadioStorage shema-1804-6 Upper Darlington Variant

This folder is derived from `003_radiostorage_shema_1804_6`. The circuit keeps the bootstrap voltage-addition network and adds an extra NPN transistor in the upper output arm, so `VT2A` and `VT2B` work as a Darlington emitter follower.

Source image:

`https://radiostorage.net/uploads/Image/schemes/18/shema-1804-6.png`

## GitHub Preview

### Source Image

![Original RadioStorage schematic](source/shema-1804-6.png)

### Reconstructed Schematic

![Reconstructed Darlington amplifier schematic](schematic/reconstructed_amplifier_darlington.png)

### Simulation Plots

![1 kHz sine-wave response](plots/darlington_sine_response_1khz.png)

![AC gain and phase](plots/darlington_gain_vs_frequency.png)

![THD vs frequency](plots/darlington_thd_vs_frequency.png)

![THD vs output power](plots/darlington_thd_vs_output_power.png)

![Output power vs frequency](plots/darlington_output_power_vs_frequency.png)

![1 kHz square-wave response](plots/darlington_square_response_1khz.png)

![10 kHz square-wave response](plots/darlington_square_response_10khz.png)

## Circuit Changes Compared With 003

- `VT2A`: added KT3102A NPN Darlington driver, `Bf = 100`.
- `VT2B`: existing KT817A NPN upper power transistor, `Bf = 50`.
- `VD3`: added KD521A diode in the bias chain so the upper Darlington pair has an extra base-emitter drop available.
- `VT3`: lower KT816A PNP emitter follower, unchanged.
- `R1A`, `R1B`, and `R2`: retuned to common E24 values (`{resistor_value_label(R1A_BOOT_VALUE)}`, `{resistor_value_label(R1B_BOOT_VALUE)}`, `{resistor_value_label(R2_VALUE)}`) so the output emitter node sits close to half of the 12 V supply.
- `R3`, `C2`, and `C4`: kept from the 003 bootstrap run for a direct comparison.
- `R4`: changed to `{resistor_value_label(RE_VT1_VALUE)}` in the VT1 emitter path; the bias network was retuned after this change.

## ngspice Check

The Darlington model converged in ngspice.

Operating point from `data/darlington/ngspice.log`:

- `V(b_in)`: about {op_b_in:.3f} V
- `V(e_vt1)`: about {op_e_vt1:.3f} V
- `V(drive)`: about {op_drive:.3f} V
- `V(b_top)`: about {op_b_top:.3f} V
- `V(b_upper)`: about {op_b_upper:.3f} V
- `V(out)`: about {op_out:.3f} V before output capacitor
- `V(load)`: about {op_load:.3f} V DC after output capacitor
- VT2A collector current: about {op_q2a_ma:.2f} mA
- VT2B collector current: about {op_q2b_ma:.2f} mA
- VT3 collector current: about {op_q3_ma:.2f} mA
- Total supply current in this simplified transistor model: about {op_supply_ma:.2f} mA

## THD Sweeps

The THD-vs-frequency graph now has separate target-power curves at {", ".join(f"{value:g} mW" for value in THD_FREQUENCY_TARGET_POWERS_MW)}. Each point retunes the input amplitude toward the requested output power before estimating harmonics 2-5 from transient data.

At 1 kHz and the 100 mW target, the simulated point is:

- Output power: `{at_1k_100mw["power_w"] * 1000:.2f} mW`
- Load RMS voltage: `{at_1k_100mw["vout_rms_v"]:.3f} V`
- Input swing: `{at_1k_100mw["vin_swing_mvpp"]:.1f} mVpp`
- THD estimate: `{at_1k_100mw["thd_percent"]:.3f} %`

The THD-vs-output-power graph now includes {", ".join("1 kHz" if freq == 1000 else (f"{freq / 1000:g} kHz" if freq > 1000 else f"{freq:g} Hz") for freq in POWER_SWEEP_FREQS_HZ)}. The largest simulated power-sweep point is about `{max_power_row["power_w"] * 1000:.2f} mW` into 8 ohm with `{max_power_row["thd_percent"]:.2f} %` THD.

## Non-Clipping Check

- Sine input swing: `{max(sine_vin) - min(sine_vin):.4f} Vpp`.
- Output node before C2: `{min(sine_amp_out):.4f}..{max(sine_amp_out):.4f} V`.
- Rail headroom at that node: at least `{sine_headroom:.4f} V`.
- Speaker/load swing after C2: `{sine_load_pp:.4f} Vpp`.

## Square-Wave Response

- 1 kHz: load swing about `{square_1k["load_pp_v"]:.3f} Vpp`.
- 10 kHz: load swing about `{square_10k["load_pp_v"]:.3f} Vpp`.

## Reusable Runner

Run the complete regeneration flow from the repository root with:

```powershell
python scripts\\run_circuit_result.py results\\004_radiostorage_shema_1804_6_darlington\\variants\\darlington.py
```

## Files

- `source/shema-1804-6.png`: original downloaded image.
- `variants/darlington.py`: reusable circuit variant with schematic drawing, SPICE netlists, measurements, and result description.
- `schematic/reconstructed_amplifier_darlington.svg/png`: redrawn Darlington schematic.
- `netlists/radiostorage_amp_darlington.cir`: main ngspice netlist.
- `data/darlington/ac_response.csv`: AC gain/phase data from ngspice.
- `data/darlington/transient_1khz.csv`: 1 kHz transient data from ngspice.
- `data/darlington/frequency_sweep.csv`: fixed-output-power frequency sweep with THD estimates.
- `data/darlington/power_sweep.csv`: multi-frequency input-level sweep with THD versus output power.
- `data/darlington/square/*.csv`: 1 kHz and 10 kHz square-wave transient data.
- `plots/darlington_*.svg/png`: generated plots for the Darlington variant.
"""
    write_text_lf(RESULT_DIR / "README.md", text_body)


def run() -> None:
    for folder in [DATA, SWEEP, POWER_SWEEP, SQUARE, PLOTS, SCHEMATIC, NETLISTS]:
        folder.mkdir(parents=True, exist_ok=True)
    write_text_lf(SCHEMATIC / "reconstructed_amplifier_darlington.svg", darlington_schematic_svg())
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
