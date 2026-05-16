from __future__ import annotations

import csv
import math
from pathlib import Path

import simulate_and_render as base


DATA = base.DATA / "bootstrap"
SWEEP = DATA / "sweep"
SQUARE = DATA / "square"
PLOTS = base.PLOTS
NETLIST = base.NETLISTS / "radiostorage_amp_bootstrap.cir"
RLOAD = base.RLOAD
VIN_PEAK = base.VIN_PEAK


MODELS = """.model KD521A D(Is=2.5n Rs=1.8 N=1.85 Cjo=2p M=0.33 Bv=75 Ibv=5u Tt=4n)
.model KT3102A NPN(Is=2e-14 Bf=100 Br=6 Vaf=100 Var=20 Ikf=0.12 Ikr=0.02
+ Rc=1 Re=0.35 Rb=60 Cje=9p Cjc=4p Tf=0.4n Tr=35n)
.model KT817A NPN(Is=9e-14 Bf=50 Br=5 Vaf=70 Var=15 Ikf=3.0 Ikr=0.4
+ Rc=0.12 Re=0.06 Rb=2.5 Cje=140p Cjc=80p Tf=0.45u Tr=6u)
.model KT816A PNP(Is=1.1e-13 Bf=50 Br=5 Vaf=60 Var=15 Ikf=2.5 Ikr=0.35
+ Rc=0.14 Re=0.07 Rb=2.8 Cje=160p Cjc=90p Tf=0.55u Tr=7u)
"""


def bootstrap_bias() -> str:
    return f"""R1A vcc boot {base.R1A_BOOT_VALUE:g}
R1B boot b_top {base.R1B_BOOT_VALUE:g}
C4 boot out {base.CBOOT_VALUE_UF:g}u"""


def circuit(vin_line: str, control: str) -> str:
    return f"""* Bootstrapped RadioStorage shema-1804-6 single-supply BJT audio amplifier
.options abstol=1n reltol=0.003 itl1=500 itl4=500
.temp 27

VCC vcc 0 12
{vin_line}
R4 vin 0 470k
C3 vin b_in 10u
R3 b_in 0 {base.R3_VALUE:g}
R2 out b_in {base.R2_VALUE:g}
Q1 drive b_in e_vt1 KT3102A
R5 e_vt1 0 {base.RE_VT1_VALUE:g}
{bootstrap_bias()}
D1 b_top d_mid KD521A
D2 d_mid drive KD521A
Q2 vcc b_top out KT817A
Q3 0 drive out KT816A
C2 out load {base.C2_VALUE_UF:g}u
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
    return circuit("VIN vin 0 DC 0 AC 1 SIN(0 1m 1k)", control)


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
        netlist.write_text(sweep_netlist(freq, VIN_PEAK, csv_path.name), encoding="utf-8")
        base.run_ngspice(netlist, log, SWEEP)
        data = base.read_rows(csv_path)
        times = [row[0] for row in data]
        load = [row[3] for row in data]
        vin = [row[5] for row in data]
        load_rms = base.rms([v - sum(load) / len(load) for v in load])
        vin_rms = base.rms(vin)
        thd, fundamental_rms = base.harmonic_thd(times, load, freq)
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
        netlist = SQUARE / f"bootstrap_square_response_{tag}.cir"
        csv_path = SQUARE / f"bootstrap_square_response_{tag}.csv"
        log = SQUARE / f"bootstrap_square_response_{tag}.log"
        netlist.write_text(square_netlist(freq, VIN_PEAK, csv_path.name), encoding="utf-8")
        base.run_ngspice(netlist, log, SQUARE)
        rows = base.read_rows(csv_path)
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
    rows = base.read_rows(SQUARE / f"bootstrap_square_response_{tag}.csv")
    t0 = rows[0][0]
    time_ms = [(row[0] - t0) * 1000.0 for row in rows]
    load = [row[5] for row in rows]
    vin_raw = [row[3] for row in rows]
    load_max_abs = max(abs(v) for v in load)
    vin_max_abs = max(abs(v) for v in vin_raw)
    vin_scale = load_max_abs / vin_max_abs if vin_max_abs > 0 else 1.0
    vin = [value * vin_scale for value in vin_raw]
    max_abs = max(load_max_abs, max(abs(v) for v in vin))
    ymax = base.waveform_y_limit(max_abs)
    duration_ms = 4.0 / freq * 1000.0
    x_ticks = [0, 1, 2, 3, 4] if freq == 1000.0 else [0, 0.1, 0.2, 0.3, 0.4]
    y_ticks = [-ymax, -ymax / 2.0, 0, ymax / 2.0, ymax]
    base.Plot(
        920,
        520,
        f"Bootstrap square response, {freq / 1000:g} kHz, Vin = {2 * VIN_PEAK * 1000:.1f} mVpp",
        "Time after 60 ms settling, ms",
        "Voltage, V",
    ).render(
        [("load output", list(zip(time_ms, load)), "#1665d8"), (f"input x{base.scale_label(vin_scale)}", list(zip(time_ms, vin)), "#b54708")],
        PLOTS / f"bootstrap_square_response_{tag}.svg",
        0,
        duration_ms,
        -ymax,
        ymax,
        x_ticks,
        y_ticks,
    )


def render_outputs(sweep_rows: list[dict[str, float]], square_rows: list[dict[str, float]]) -> None:
    ac = base.read_rows(DATA / "ac_response.csv")
    gain_points = [(row[0], row[4]) for row in ac]
    phase_points = [(row[0], row[6]) for row in ac]
    base.Plot(920, 520, "Bootstrap AC gain and phase, load = 8 ohm", "Frequency, Hz", "Gain dB / phase deg", True).render(
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
    thd_ymax = max(1.0, math.ceil(max_thd * 1.25))
    base.Plot(920, 520, f"Bootstrap THD vs frequency, Vin = {VIN_PEAK * 1000:.0f} mV peak", "Frequency, Hz", "THD, %", True).render(
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
    power_ymax = max(10.0, math.ceil(max_power * 1.25 / 10.0) * 10.0)
    base.Plot(920, 520, f"Bootstrap output power vs frequency, Vin = {VIN_PEAK * 1000:.0f} mV peak", "Frequency, Hz", "Power, mW into 8 ohm", True).render(
        [("Pout", power_points, "#1665d8")],
        PLOTS / "bootstrap_output_power_vs_frequency.svg",
        20,
        20000,
        0,
        power_ymax,
        [20, 50, 100, 1000, 10000, 20000],
        [0, power_ymax / 4, power_ymax / 2, power_ymax * 3 / 4, power_ymax],
    )
    base.render_sine_plot(
        DATA / "transient_1khz.csv",
        PLOTS / "bootstrap_sine_response_1khz.svg",
        f"Bootstrap sine-wave response, 1 kHz, Vin = {2 * VIN_PEAK * 1000:.1f} mVpp",
    )

    for row in square_rows:
        render_square_plot(row["frequency_hz"])


def main() -> None:
    for folder in [DATA, SWEEP, SQUARE, PLOTS, base.NETLISTS]:
        folder.mkdir(parents=True, exist_ok=True)
    NETLIST.write_text(main_netlist(), encoding="utf-8")
    base.run_ngspice(NETLIST, DATA / "ngspice.log", DATA)
    sweep_rows = run_frequency_sweep()
    square_rows = run_square_responses()
    render_outputs(sweep_rows, square_rows)


if __name__ == "__main__":
    main()
