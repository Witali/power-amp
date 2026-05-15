from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from generate_radio_ru_5_study import (
    LOAD_OHM,
    SCHEMATIC_DIR,
    SUPPLY_RAIL_V,
    TARGET_GAIN,
    VARIANTS,
    Variant,
    schematic_svg,
)


ROOT = Path(__file__).resolve().parent
NETLIST_DIR = ROOT / "spice_component_netlists"
RESULTS_PATH = ROOT / "spice_component_results.csv"
SUMMARY_PATH = ROOT / "spice_component_summary.md"
BEST_SCHEMATIC_PATH = ROOT / "best_spice_component_schematic.svg"

POINTS = 48
SINE = [math.sin(2.0 * math.pi * i / POINTS) for i in range(POINTS)]
COS_TABLE = [
    [math.cos(2.0 * math.pi * h * i / POINTS) for i in range(POINTS)]
    for h in range(1, 10)
]
SIN_TABLE = [
    [math.sin(2.0 * math.pi * h * i / POINTS) for i in range(POINTS)]
    for h in range(1, 10)
]


@dataclass(frozen=True)
class BjtModel:
    name: str
    kind: str
    beta: float
    is_base: float


@dataclass(frozen=True)
class Resistor:
    n1: str
    n2: str
    value: float


@dataclass(frozen=True)
class Capacitor:
    n1: str
    n2: str
    value: float


@dataclass(frozen=True)
class VoltageSource:
    n_plus: str
    n_minus: str
    value: Callable[[float, dict[str, float]], float]
    label: str


@dataclass(frozen=True)
class Bjt:
    name: str
    c: str
    b: str
    e: str
    model: BjtModel


@dataclass
class Circuit:
    resistors: list[Resistor]
    capacitors: list[Capacitor]
    voltage_sources: list[VoltageSource]
    bjts: list[Bjt]
    node_names: list[str]
    load_ohm: float


SMALL_NPN = BjtModel("NPN_SMALL", "npn", beta=95.0, is_base=1.1e-15)
SMALL_PNP = BjtModel("PNP_SMALL", "pnp", beta=75.0, is_base=1.4e-15)
POWER_NPN = BjtModel("NPN_POWER", "npn", beta=55.0, is_base=4.8e-15)
POWER_PNP = BjtModel("PNP_POWER", "pnp", beta=48.0, is_base=5.6e-15)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def exp_limited(x: float) -> float:
    return math.exp(clamp(x, -40.0, 40.0))


def node_voltage(x: list[float], node_index: dict[str, int], node: str) -> float:
    if node == "0":
        return 0.0
    return x[node_index[node]]


def add_node(nodes: set[str], name: str) -> None:
    if name != "0":
        nodes.add(name)


def drive_parameters(v: Variant) -> tuple[float, float, float]:
    if v.output_kind == "triple_ef":
        return 4.02, 32.0, 1.00
    if v.output_kind == "cfp":
        return 2.18, 18.0, 1.04
    if v.output_kind == "current_feedback":
        return 2.76, 16.0, 1.06
    if v.vas_kind == "folded":
        return 2.72, 38.0, 1.02
    return 2.74, 56.0, 1.00


def source_value(
    bias: float,
    sign: float,
    drive_peak: float,
    t_norm: float,
    loop_gain: float,
    load_ohm: float,
) -> Callable[[float, dict[str, float]], float]:
    raw = drive_peak * math.sin(2.0 * math.pi * t_norm) + sign * bias / 2.0

    def value(_: float, voltages: dict[str, float]) -> float:
        if loop_gain <= 0.0:
            return raw
        desired_v = drive_peak * math.sin(2.0 * math.pi * t_norm)
        out_v = voltages.get("OUT", 0.0)
        current_error = desired_v / load_ohm - out_v / load_ohm
        correction = loop_gain * current_error * load_ohm
        return raw + correction

    return value


def build_circuit(v: Variant, drive_peak: float, t_norm: float, load_ohm: float = LOAD_OHM) -> Circuit:
    bias, source_r, gain_trim = drive_parameters(v)
    drive_peak *= gain_trim
    loop_gain = 0.42 if v.output_kind == "current_feedback" else 0.0
    resistors = [
        Resistor("UPSRC", "UP", source_r),
        Resistor("DNSRC", "DN", source_r),
        Resistor("OUT", "0", load_ohm),
        Resistor("OUT", "ZOB", 10.0),
    ]
    capacitors = [Capacitor("ZOB", "0", 100e-9)]
    voltage_sources = [
        VoltageSource("VCC", "0", lambda _t, _v: SUPPLY_RAIL_V, "VCC"),
        VoltageSource("VEE", "0", lambda _t, _v: -SUPPLY_RAIL_V, "VEE"),
        VoltageSource("UPSRC", "0", source_value(bias, +1.0, drive_peak, t_norm, loop_gain, load_ohm), "VUP"),
        VoltageSource("DNSRC", "0", source_value(bias, -1.0, drive_peak, t_norm, loop_gain, load_ohm), "VDN"),
    ]
    bjts: list[Bjt] = []

    if v.output_kind == "triple_ef":
        bjts.extend(
            [
                Bjt("QUPRE", "VCC", "UP", "UPRE", SMALL_NPN),
                Bjt("QUDRV", "VCC", "UPRE", "UBASE", SMALL_NPN),
                Bjt("QUOUT", "VCC", "UBASE", "UEMIT", POWER_NPN),
                Bjt("QDPRE", "VEE", "DN", "DPRE", SMALL_PNP),
                Bjt("QDDRV", "VEE", "DPRE", "DBASE", SMALL_PNP),
                Bjt("QDOUT", "VEE", "DBASE", "DEMIT", POWER_PNP),
            ]
        )
        resistors.extend(
            [
                Resistor("UPRE", "UBASE", 4.7),
                Resistor("DPRE", "DBASE", 4.7),
                Resistor("UEMIT", "OUT", 0.22),
                Resistor("DEMIT", "OUT", 0.22),
            ]
        )
    elif v.output_kind == "cfp":
        bjts.extend(
            [
                Bjt("QUDRV", "OUT", "UP", "UBASE", SMALL_PNP),
                Bjt("QUOUT", "VCC", "UBASE", "UEMIT", POWER_NPN),
                Bjt("QDDRV", "OUT", "DN", "DBASE", SMALL_NPN),
                Bjt("QDOUT", "VEE", "DBASE", "DEMIT", POWER_PNP),
            ]
        )
        resistors.extend(
            [
                Resistor("UBASE", "OUT", 330.0),
                Resistor("DBASE", "OUT", 330.0),
                Resistor("UEMIT", "OUT", 0.22),
                Resistor("DEMIT", "OUT", 0.22),
            ]
        )
    else:
        bjts.extend(
            [
                Bjt("QUDRV", "VCC", "UP", "UBASE", SMALL_NPN),
                Bjt("QUOUT", "VCC", "UBASE", "UEMIT", POWER_NPN),
                Bjt("QDDRV", "VEE", "DN", "DBASE", SMALL_PNP),
                Bjt("QDOUT", "VEE", "DBASE", "DEMIT", POWER_PNP),
            ]
        )
        resistors.extend(
            [
                Resistor("UBASE", "OUT", 1000.0 if v.vas_kind == "folded" else 1800.0),
                Resistor("DBASE", "OUT", 1000.0 if v.vas_kind == "folded" else 1800.0),
                Resistor("UEMIT", "OUT", 0.22),
                Resistor("DEMIT", "OUT", 0.22),
            ]
        )

    nodes: set[str] = set()
    for r in resistors:
        add_node(nodes, r.n1)
        add_node(nodes, r.n2)
    for c in capacitors:
        add_node(nodes, c.n1)
        add_node(nodes, c.n2)
    for s in voltage_sources:
        add_node(nodes, s.n_plus)
        add_node(nodes, s.n_minus)
    for q in bjts:
        add_node(nodes, q.c)
        add_node(nodes, q.b)
        add_node(nodes, q.e)
    return Circuit(resistors, capacitors, voltage_sources, bjts, sorted(nodes), load_ohm)


def bjt_currents(q: Bjt, vc: float, vb: float, ve: float) -> tuple[float, float, float]:
    vt = 0.02585
    beta = q.model.beta
    is_base = q.model.is_base
    if q.model.kind == "npn":
        vbe = vb - ve
        vbc = vb - vc
        ibe = is_base * (exp_limited(vbe / vt) - 1.0)
        ibc = 0.08 * is_base * (exp_limited(vbc / vt) - 1.0)
        ice = beta * ibe * clamp(1.0 + (vc - ve) / 90.0, 0.15, 2.5)
        i_c = ice - ibc
        i_b = ibe + ibc
        i_e = -ibe - ice
        return i_c, i_b, i_e
    veb = ve - vb
    vcb = vc - vb
    ieb = is_base * (exp_limited(veb / vt) - 1.0)
    icb = 0.08 * is_base * (exp_limited(vcb / vt) - 1.0)
    iec = beta * ieb * clamp(1.0 + (ve - vc) / 90.0, 0.15, 2.5)
    i_e = ieb + iec
    i_b = -ieb - icb
    i_c = icb - iec
    return i_c, i_b, i_e


def residual(
    x: list[float],
    circuit: Circuit,
    node_index: dict[str, int],
    source_index: dict[str, int],
    cap_prev: dict[tuple[str, str], float],
    dt: float,
    t: float,
) -> list[float]:
    n_nodes = len(circuit.node_names)
    res = [0.0 for _ in range(n_nodes + len(circuit.voltage_sources))]
    voltages = {name: node_voltage(x, node_index, name) for name in circuit.node_names}

    def stamp_current(node: str, current: float) -> None:
        if node != "0":
            res[node_index[node]] += current

    for r in circuit.resistors:
        v1 = node_voltage(x, node_index, r.n1)
        v2 = node_voltage(x, node_index, r.n2)
        current = (v1 - v2) / r.value
        stamp_current(r.n1, current)
        stamp_current(r.n2, -current)

    if dt > 0.0:
        for c in circuit.capacitors:
            v1 = node_voltage(x, node_index, c.n1)
            v2 = node_voltage(x, node_index, c.n2)
            prev = cap_prev.get((c.n1, c.n2), 0.0)
            current = c.value / dt * ((v1 - v2) - prev)
            stamp_current(c.n1, current)
            stamp_current(c.n2, -current)

    for q in circuit.bjts:
        vc = node_voltage(x, node_index, q.c)
        vb = node_voltage(x, node_index, q.b)
        ve = node_voltage(x, node_index, q.e)
        ic, ib, ie = bjt_currents(q, vc, vb, ve)
        stamp_current(q.c, ic)
        stamp_current(q.b, ib)
        stamp_current(q.e, ie)

    for i, src in enumerate(circuit.voltage_sources):
        branch = n_nodes + i
        current = x[branch]
        stamp_current(src.n_plus, current)
        stamp_current(src.n_minus, -current)
        vp = node_voltage(x, node_index, src.n_plus)
        vn = node_voltage(x, node_index, src.n_minus)
        res[branch] = vp - vn - src.value(t, voltages)
    return res


def solve_linear(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    aug = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-18:
            raise ValueError("singular matrix")
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        div = aug[col][col]
        for j in range(col, n + 1):
            aug[col][j] /= div
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor == 0.0:
                continue
            for j in range(col, n + 1):
                aug[r][j] -= factor * aug[col][j]
    return [aug[i][n] for i in range(n)]


def solve_circuit(
    circuit: Circuit,
    previous: list[float] | None,
    cap_prev: dict[tuple[str, str], float],
    dt: float,
    t: float,
) -> tuple[list[float], dict[str, float]]:
    node_index = {name: i for i, name in enumerate(circuit.node_names)}
    source_index = {src.label: len(circuit.node_names) + i for i, src in enumerate(circuit.voltage_sources)}
    size = len(circuit.node_names) + len(circuit.voltage_sources)
    if previous is None or len(previous) != size:
        x = [0.0 for _ in range(size)]
        if "VCC" in node_index:
            x[node_index["VCC"]] = SUPPLY_RAIL_V
        if "VEE" in node_index:
            x[node_index["VEE"]] = -SUPPLY_RAIL_V
    else:
        x = previous[:]

    for _ in range(28):
        r0 = residual(x, circuit, node_index, source_index, cap_prev, dt, t)
        norm = max(abs(v) for v in r0)
        if norm < 2e-7:
            voltages = {name: node_voltage(x, node_index, name) for name in circuit.node_names}
            return x, voltages
        jac: list[list[float]] = []
        eps_base = 1e-5
        for col in range(size):
            xp = x[:]
            step = eps_base * max(1.0, abs(x[col]))
            xp[col] += step
            rp = residual(xp, circuit, node_index, source_index, cap_prev, dt, t)
            jac.append([(rp[row] - r0[row]) / step for row in range(size)])
        # Transpose column-built Jacobian into rows.
        j_rows = [[jac[col][row] for col in range(size)] for row in range(size)]
        try:
            delta = solve_linear(j_rows, [-v for v in r0])
        except ValueError:
            break
        alpha = 1.0
        old_norm = norm
        accepted = False
        while alpha >= 0.0625:
            trial = [x[i] + alpha * delta[i] for i in range(size)]
            rt = residual(trial, circuit, node_index, source_index, cap_prev, dt, t)
            new_norm = max(abs(v) for v in rt)
            if new_norm < old_norm * 0.98 or new_norm < 1e-6:
                x = trial
                accepted = True
                break
            alpha *= 0.5
        if not accepted:
            x = [x[i] + 0.05 * delta[i] for i in range(size)]
    voltages = {name: node_voltage(x, node_index, name) for name in circuit.node_names}
    return x, voltages


def run_waveform(v: Variant, drive_peak: float, load_ohm: float = LOAD_OHM) -> list[float]:
    prev: list[float] | None = None
    cap_prev: dict[tuple[str, str], float] = {}
    outputs: list[float] = []
    dt = 1.0 / (1000.0 * POINTS)
    for i in range(POINTS):
        t_norm = i / POINTS
        circuit = build_circuit(v, drive_peak, t_norm, load_ohm)
        prev, voltages = solve_circuit(circuit, prev, cap_prev, dt, i * dt)
        outputs.append(voltages.get("OUT", 0.0))
        for c in circuit.capacitors:
            cap_prev[(c.n1, c.n2)] = voltages.get(c.n1, 0.0) - voltages.get(c.n2, 0.0)
    return outputs


def rms(values: list[float]) -> float:
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) * (v - mean) for v in values) / len(values))


def harmonic_rms(values: list[float]) -> list[float]:
    n = len(values)
    mean = sum(values) / n
    amps = []
    for h in range(1, 10):
        a = 0.0
        b = 0.0
        for i, y0 in enumerate(values):
            y = y0 - mean
            a += y * COS_TABLE[h - 1][i]
            b += y * SIN_TABLE[h - 1][i]
        a *= 2.0 / n
        b *= 2.0 / n
        amps.append(math.sqrt(a * a + b * b) / math.sqrt(2.0))
    return amps


def thd_percent(values: list[float]) -> float:
    hs = harmonic_rms(values)
    if hs[0] < 1e-9:
        return 999.0
    return 100.0 * math.sqrt(sum(h * h for h in hs[1:])) / hs[0]


def simulate_power_point(v: Variant, watts: float, load_ohm: float = LOAD_OHM) -> tuple[float, float, float]:
    target_vrms = math.sqrt(watts * load_ohm)
    drive_peak = target_vrms * math.sqrt(2.0)
    y = run_waveform(v, drive_peak, load_ohm)
    # Calibrate the SPICE-style source amplitude so the comparison is made
    # at actual output power, not at the ideal unloaded drive voltage.
    for _ in range(3):
        actual = rms(y)
        if actual <= 1e-9:
            drive_peak *= 2.0
        else:
            drive_peak *= clamp(target_vrms / actual, 0.55, 1.85)
        y = run_waveform(v, drive_peak, load_ohm)
    return drive_peak, rms(y), thd_percent(y)


def clean_power(v: Variant, cache: dict[float, tuple[float, float, float]]) -> float:
    best = 0.0
    for watts in [0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9]:
        if watts not in cache:
            cache[watts] = simulate_power_point(v, watts)
        _, vrms, thd = cache[watts]
        actual = vrms * vrms / LOAD_OHM
        if thd <= 1.0 and actual >= 0.95 * watts:
            best = actual
        else:
            break
    return round(best, 2)


def output_resistance(v: Variant) -> tuple[float, float]:
    drive = 0.65
    y_open = run_waveform(v, drive, 100000.0)
    y_load = run_waveform(v, drive, LOAD_OHM)
    v_open = rms(y_open)
    v_load = rms(y_load)
    if v_load <= 1e-9:
        return 999.0, 0.0
    rout = LOAD_OHM * max(v_open / v_load - 1.0, 0.0)
    damping = LOAD_OHM / max(rout, 1e-6)
    return round(rout, 4), round(damping, 1)


def score(row: dict[str, float], v: Variant) -> float:
    no_global = v.no_global_alignment
    return round(
        100.0
        * (
            0.18 * clamp(1.0 - row["thd_1w_pct"] / 0.80, 0.0, 1.0)
            + 0.23 * clamp(1.0 - row["thd_5w_pct"] / 1.50, 0.0, 1.0)
            + 0.13 * clamp(row["clean_power_1pct_w"] / 8.0, 0.0, 1.0)
            + 0.11 * clamp(row["damping_factor_8r"] / 110.0, 0.0, 1.0)
            + 0.10 * clamp(v.phase_margin_deg / 75.0, 0.0, 1.0)
            + 0.07 * clamp(v.headroom_v / 12.2, 0.0, 1.0)
            + 0.05 * clamp(1.0 - v.idle_ma / 180.0, 0.0, 1.0)
            + 0.05 * v.radio_source_score
            + 0.08 * no_global
        ),
        2,
    )


def simulate_variant(v: Variant) -> dict[str, str | float]:
    cache: dict[float, tuple[float, float, float]] = {}
    cache[1.0] = simulate_power_point(v, 1.0)
    cache[5.0] = simulate_power_point(v, 5.0)
    drive1, vrms1, thd1 = cache[1.0]
    drive5, vrms5, thd5 = cache[5.0]
    rout, damping = output_resistance(v)
    clean = clean_power(v, cache)
    row: dict[str, str | float] = {
        "id": v.ident,
        "name": v.name,
        "output_kind": v.output_kind,
        "source_basis": v.source_basis,
        "drive_1w_peak_v": round(drive1, 4),
        "actual_1w_vrms": round(vrms1, 4),
        "thd_1w_pct": round(thd1, 4),
        "drive_5w_peak_v": round(drive5, 4),
        "actual_5w_vrms": round(vrms5, 4),
        "thd_5w_pct": round(thd5, 4),
        "clean_power_1pct_w": clean,
        "rout_ohm_est": rout,
        "damping_factor_8r": damping,
        "phase_margin_deg_est": v.phase_margin_deg,
        "no_global_alignment": v.no_global_alignment,
        "notes": v.notes,
    }
    numeric = {k: float(value) for k, value in row.items() if isinstance(value, (int, float))}
    row["component_score"] = score(numeric, v)
    return row


def write_component_netlist(v: Variant) -> None:
    bias, source_r, trim = drive_parameters(v)
    lines = [
        f"* Variant {v.ident}: {v.name}",
        "* Transistor-level SPICE component netlist for the local component simulation.",
        f"* Source basis: {v.source_basis}",
        f"* Drive bias spread: {bias:g} V, source resistance: {source_r:g} ohm, drive trim: {trim:g}",
        "",
        ".model NPN_SMALL NPN(IS=1.1e-15 BF=95 VAF=90)",
        ".model PNP_SMALL PNP(IS=1.4e-15 BF=75 VAF=90)",
        ".model NPN_POWER NPN(IS=4.8e-15 BF=55 VAF=90)",
        ".model PNP_POWER PNP(IS=5.6e-15 BF=48 VAF=90)",
        f"VCC VCC 0 DC {SUPPLY_RAIL_V:g}",
        f"VEE VEE 0 DC -{SUPPLY_RAIL_V:g}",
        "* VUP/VDN are stepped sine drive sources in the Python component solver.",
        "RUPDRV UPSRC UP " + f"{source_r:g}",
        "RDNDRV DNSRC DN " + f"{source_r:g}",
    ]
    if v.output_kind == "triple_ef":
        lines.extend(
            [
                "QUPRE VCC UP UPRE NPN_SMALL",
                "QUDRV VCC UPRE UBASE NPN_SMALL",
                "QUOUT VCC UBASE UEMIT NPN_POWER",
                "QDPRE VEE DN DPRE PNP_SMALL",
                "QDDRV VEE DPRE DBASE PNP_SMALL",
                "QDOUT VEE DBASE DEMIT PNP_POWER",
                "RUPRE UPRE UBASE 4.7",
                "RDPRE DPRE DBASE 4.7",
            ]
        )
    elif v.output_kind == "cfp":
        lines.extend(
            [
                "QUDRV OUT UP UBASE PNP_SMALL",
                "QUOUT VCC UBASE UEMIT NPN_POWER",
                "QDDRV OUT DN DBASE NPN_SMALL",
                "QDOUT VEE DBASE DEMIT PNP_POWER",
                "RLOCALU UBASE OUT 330",
                "RLOCALD DBASE OUT 330",
            ]
        )
    else:
        feedback_comment = "* VUP/VDN include output-current-sense correction in solver." if v.output_kind == "current_feedback" else ""
        lines.extend(
            [
                feedback_comment,
                "QUDRV VCC UP UBASE NPN_SMALL",
                "QUOUT VCC UBASE UEMIT NPN_POWER",
                "QDDRV VEE DN DBASE PNP_SMALL",
                "QDOUT VEE DBASE DEMIT PNP_POWER",
                f"RLOCALU UBASE OUT {1000 if v.vas_kind == 'folded' else 1800}",
                f"RLOCALD DBASE OUT {1000 if v.vas_kind == 'folded' else 1800}",
            ]
        )
    lines.extend(
        [
            "REU UEMIT OUT 0.22",
            "RED DEMIT OUT 0.22",
            f"RLOAD OUT 0 {LOAD_OHM:g}",
            "RZ OUT ZOB 10",
            "CZ ZOB 0 100n",
            ".tran 0 20m 10m 2u",
            ".four 1k V(OUT)",
            ".end",
        ]
    )
    (NETLIST_DIR / f"variant_{v.ident}_{v.slug}.cir").write_text("\n".join(line for line in lines if line) + "\n", encoding="utf-8")


def write_outputs(rows: list[dict[str, str | float]]) -> None:
    NETLIST_DIR.mkdir(exist_ok=True)
    SCHEMATIC_DIR.mkdir(exist_ok=True)
    for v in VARIANTS:
        write_component_netlist(v)
    with RESULTS_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    best = rows[0]
    best_variant = next(v for v in VARIANTS if v.ident == str(best["id"]))
    svg_row = dict(best)
    svg_row["project_score"] = best["component_score"]
    BEST_SCHEMATIC_PATH.write_text(schematic_svg(best_variant, svg_row), encoding="utf-8")
    lines = [
        "# SPICE-Component Simulation Results",
        "",
        "This pass replaces the earlier behavioral transfer screen with transistor-level SPICE-style components. The local machine does not have ngspice/LTspice/PySpice installed, so the script solves the generated `Q`/`R`/`C`/`V` circuits with a small Python nodal solver using a simplified BJT exponential model.",
        "",
        f"Selected best for the current no-overall-feedback target: **Variant {best['id']} - {best['name']}**.",
        "",
        f"Best component-simulation schematic: `best_spice_component_schematic.svg`.",
        "",
        "| Rank | ID | Score | 1 W THD % | 5 W THD % | Clean W @ 1% THD | Rout ohm | Damping | No-Global Align | Topology |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(rows, start=1):
        lines.append(
            f"| {i} | {r['id']} | {r['component_score']} | {r['thd_1w_pct']} | {r['thd_5w_pct']} | "
            f"{r['clean_power_1pct_w']} | {r['rout_ohm_est']} | {r['damping_factor_8r']} | "
            f"{r['no_global_alignment']} | {r['name']} |"
        )
    lines.extend(
        [
            "",
            "Caveat: the solver is intentionally small. It is useful for comparing these five component topologies under the same assumptions, not for final PCB values, SOA, thermal runaway, or high-frequency compensation signoff.",
            "",
            "Generated files:",
            "",
            "- `spice_component_results.csv`",
            "- `spice_component_netlists/*.cir`",
            "- `best_spice_component_schematic.svg`",
            "- existing transistor-symbol schematics in `schematics/*.svg`",
        ]
    )
    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = [simulate_variant(v) for v in VARIANTS]
    rows.sort(key=lambda r: float(r["component_score"]), reverse=True)
    write_outputs(rows)
    print(f"Best SPICE-component choice: {rows[0]['id']} - {rows[0]['name']} (score {rows[0]['component_score']})")
    print(f"Results: {RESULTS_PATH}")
    print(f"Summary: {SUMMARY_PATH}")
    print(f"Netlists: {NETLIST_DIR}")


if __name__ == "__main__":
    main()
