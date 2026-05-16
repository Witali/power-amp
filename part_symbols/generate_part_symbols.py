from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent


STYLE = """<defs>
<style>
.wire{stroke:#111;stroke-width:2.6;fill:none;stroke-linecap:round;stroke-linejoin:round}
.thin{stroke:#111;stroke-width:1.7;fill:none;stroke-linecap:round;stroke-linejoin:round}
.node{fill:#111;stroke:none}
.label{font-family:Arial, Helvetica, sans-serif;font-size:16px;font-weight:700;fill:#111}
.note{font-family:Arial, Helvetica, sans-serif;font-size:13px;font-weight:400;fill:#333}
.title{font-family:Arial, Helvetica, sans-serif;font-size:24px;font-weight:700;fill:#111}
.small{font-family:Arial, Helvetica, sans-serif;font-size:12px;font-weight:400;fill:#444}
</style>
</defs>"""


def svg_text(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def line(x1: float, y1: float, x2: float, y2: float, cls: str = "wire") -> str:
    return f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" class="{cls}"/>'


def text(x: float, y: float, value: str, cls: str = "label") -> str:
    return f'<text x="{x:g}" y="{y:g}" class="{cls}">{svg_text(value)}</text>'


def poly(points: list[tuple[float, float]], cls: str = "wire") -> str:
    values = " ".join(f"{x:g},{y:g}" for x, y in points)
    return f'<polyline points="{values}" class="{cls}"/>'


def rect(x: float, y: float, width: float, height: float) -> str:
    return f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" class="wire"/>'


def sheet(title: str, note: str, groups: list[str], height: int = 760) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}">',
            STYLE,
            '<rect width="100%" height="100%" fill="#fff"/>',
            text(40, 42, title, "title"),
            text(40, 66, note, "note"),
            *groups,
            "</svg>",
            "",
        ]
    )


def symbol_file(width: int, height: int, body: list[str]) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            STYLE,
            '<rect width="100%" height="100%" fill="none"/>',
            *body,
            "</svg>",
            "",
        ]
    )


def resistor_rect(x: int, y: int, label: str, note: str) -> str:
    return "\n".join(
        [
            f'<g transform="translate({x} {y})">',
            text(0, -18, label),
            line(0, 30, 42, 30),
            rect(42, 10, 84, 40),
            line(126, 30, 170, 30),
            text(0, 78, note, "note"),
            "</g>",
        ]
    )


def resistor_zigzag(x: int, y: int, label: str, note: str) -> str:
    return "\n".join(
        [
            f'<g transform="translate({x} {y})">',
            text(0, -18, label),
            line(0, 30, 35, 30),
            poly([(35, 30), (45, 15), (60, 45), (75, 15), (90, 45), (105, 15), (120, 45), (135, 15), (145, 30)]),
            line(145, 30, 185, 30),
            text(0, 78, note, "note"),
            "</g>",
        ]
    )


def variable_resistor_rect(x: int, y: int, label: str, note: str) -> str:
    return "\n".join(
        [
            f'<g transform="translate({x} {y})">',
            text(0, -18, label),
            line(0, 30, 42, 30),
            rect(42, 10, 84, 40),
            line(126, 30, 170, 30),
            line(66, 62, 114, -4),
            poly([(105, 0), (114, -4), (113, 7)]),
            text(0, 78, note, "note"),
            "</g>",
        ]
    )


def variable_resistor_zigzag(x: int, y: int, label: str, note: str) -> str:
    return "\n".join(
        [
            f'<g transform="translate({x} {y})">',
            text(0, -18, label),
            line(0, 30, 35, 30),
            poly([(35, 30), (45, 15), (60, 45), (75, 15), (90, 45), (105, 15), (120, 45), (135, 15), (145, 30)]),
            line(145, 30, 185, 30),
            line(68, 66, 124, -4),
            poly([(115, 0), (124, -4), (123, 7)]),
            text(0, 78, note, "note"),
            "</g>",
        ]
    )


def capacitor(x: int, y: int, label: str, note: str, polarized: bool = False) -> str:
    plus = [text(54, -8, "+")] if polarized else []
    return "\n".join(
        [
            f'<g transform="translate({x} {y})">',
            text(0, -18, label),
            line(0, 30, 70, 30),
            line(70, 2, 70, 58),
            line(100, 2, 100, 58),
            line(100, 30, 170, 30),
            *plus,
            text(0, 78, note, "note"),
            "</g>",
        ]
    )


def inductor(x: int, y: int, label: str, note: str) -> str:
    return "\n".join(
        [
            f'<g transform="translate({x} {y})">',
            text(0, -18, label),
            line(0, 30, 35, 30),
            '<path d="M35 30 C35 4 65 4 65 30 C65 4 95 4 95 30 C95 4 125 4 125 30 C125 4 155 4 155 30" class="wire"/>',
            line(155, 30, 190, 30),
            text(0, 78, note, "note"),
            "</g>",
        ]
    )


def diode_group(x: int, y: int, label: str, note: str) -> str:
    return "\n".join(
        [
            f'<g transform="translate({x} {y})">',
            text(0, -18, label),
            line(0, 30, 40, 30),
            '<polygon points="40,4 40,56 86,30" class="wire"/>',
            line(90, 4, 90, 56),
            line(90, 30, 130, 30),
            '<g transform="translate(160 0)">',
            line(0, 30, 40, 30),
            '<polygon points="40,4 40,56 86,30" class="wire"/>',
            poly([(90, 4), (90, 22), (102, 22)]),
            poly([(90, 56), (90, 38), (78, 38)]),
            line(90, 30, 130, 30),
            "</g>",
            '<g transform="translate(325 0)">',
            line(0, 30, 40, 30),
            '<polygon points="40,4 40,56 86,30" class="wire"/>',
            line(90, 4, 90, 56),
            line(90, 30, 130, 30),
            line(116, -2, 132, -18, "thin"),
            poly([(126, -18), (132, -18), (132, -12)], "thin"),
            line(104, -18, 120, -34, "thin"),
            poly([(114, -34), (120, -34), (120, -28)], "thin"),
            "</g>",
            text(0, 78, note, "note"),
            "</g>",
        ]
    )


def bjt_pair(x: int, y: int, label: str, note: str) -> str:
    return "\n".join(
        [
            f'<g transform="translate({x} {y})">',
            text(0, -18, label),
            '<g transform="translate(55 54)">',
            '<circle cx="0" cy="0" r="48" class="wire"/>',
            line(-48, 0, -14, 0),
            line(-14, -30, -14, 30),
            line(-14, -20, 30, -42),
            line(-14, 20, 30, 42),
            '<polygon points="20,37 5,35 11,24" fill="#111"/>',
            text(-34, 74, "NPN", "small"),
            "</g>",
            '<g transform="translate(190 54)">',
            '<circle cx="0" cy="0" r="48" class="wire"/>',
            line(-48, 0, -14, 0),
            line(-14, -30, -14, 30),
            line(-14, -20, 30, -42),
            line(-14, 20, 30, 42),
            '<polygon points="-3,-25 12,-24 6,-13" fill="#111"/>',
            text(-34, 74, "PNP", "small"),
            "</g>",
            text(0, 150, note, "note"),
            "</g>",
        ]
    )


def opamp(x: int, y: int, label: str, note: str) -> str:
    return "\n".join(
        [
            f'<g transform="translate({x} {y})">',
            text(0, -18, label),
            '<polygon points="40,10 40,110 150,60" class="wire"/>',
            line(0, 35, 40, 35),
            line(0, 85, 40, 85),
            line(150, 60, 200, 60),
            text(22, 39, "+"),
            text(24, 89, "-"),
            text(0, 150, note, "note"),
            "</g>",
        ]
    )


def ground_junction(x: int, y: int, label: str, note: str) -> str:
    return "\n".join(
        [
            f'<g transform="translate({x} {y})">',
            text(0, -18, label),
            line(45, 0, 45, 34),
            line(15, 34, 75, 34),
            line(25, 50, 65, 50),
            line(35, 66, 55, 66),
            '<g transform="translate(135 12)">',
            line(0, 40, 120, 40),
            line(60, 0, 60, 80),
            '<circle cx="60" cy="40" r="5" class="node"/>',
            "</g>",
            text(0, 120, note, "note"),
            "</g>",
        ]
    )


def loudspeaker(x: int, y: int, label: str, note: str) -> str:
    return "\n".join(
        [
            f'<g transform="translate({x} {y})">',
            text(0, -18, label),
            line(0, 40, 55, 40),
            rect(55, 8, 36, 64),
            '<polygon points="91,18 150,-10 150,90 91,62" class="wire"/>',
            line(150, 40, 195, 40),
            text(0, 120, note, "note"),
            "</g>",
        ]
    )


def battery(x: int, y: int, label: str, note: str) -> str:
    return "\n".join(
        [
            f'<g transform="translate({x} {y})">',
            text(0, -18, label),
            line(0, 40, 58, 40),
            line(58, 4, 58, 76),
            line(86, 18, 86, 62),
            line(86, 40, 145, 40),
            text(46, -4, "+"),
            text(0, 120, note, "note"),
            "</g>",
        ]
    )


def switch_fuse(x: int, y: int, label: str, note: str) -> str:
    return "\n".join(
        [
            f'<g transform="translate({x} {y})">',
            text(0, -18, label),
            line(0, 55, 45, 55),
            '<circle cx="45" cy="55" r="4" class="node"/>',
            line(45, 55, 102, 22),
            '<circle cx="128" cy="55" r="4" class="node"/>',
            line(128, 55, 170, 55),
            '<g transform="translate(210 0)">',
            line(0, 55, 40, 55),
            rect(40, 35, 86, 40),
            line(126, 55, 170, 55),
            "</g>",
            text(0, 130, note, "note"),
            "</g>",
        ]
    )


def net_label(x: int, y: int, label: str, note: str) -> str:
    return "\n".join(
        [
            f'<g transform="translate({x} {y})">',
            text(0, -18, label),
            line(0, 40, 90, 40),
            text(100, 45, "OUT"),
            text(0, 120, note, "note"),
            "</g>",
        ]
    )


def write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8", newline="\n")


def resistor_rect_symbol() -> str:
    return symbol_file(220, 90, [line(10, 45, 52, 45), rect(52, 25, 84, 40), line(136, 45, 210, 45)])


def resistor_zigzag_symbol() -> str:
    return symbol_file(
        230,
        90,
        [
            line(10, 45, 45, 45),
            poly([(45, 45), (55, 30), (70, 60), (85, 30), (100, 60), (115, 30), (130, 60), (145, 30), (155, 45)]),
            line(155, 45, 220, 45),
        ],
    )


def variable_resistor_rect_symbol() -> str:
    return symbol_file(
        220,
        110,
        [
            line(10, 55, 52, 55),
            rect(52, 35, 84, 40),
            line(136, 55, 210, 55),
            line(76, 92, 124, 26),
            poly([(115, 30), (124, 26), (123, 37)]),
        ],
    )


def variable_resistor_zigzag_symbol() -> str:
    return symbol_file(
        230,
        110,
        [
            line(10, 55, 45, 55),
            poly([(45, 55), (55, 40), (70, 70), (85, 40), (100, 70), (115, 40), (130, 70), (145, 40), (155, 55)]),
            line(155, 55, 220, 55),
            line(78, 96, 134, 26),
            poly([(125, 30), (134, 26), (133, 37)]),
        ],
    )


def capacitor_symbol(polarized: bool = False) -> str:
    body = [
        line(10, 50, 80, 50),
        line(80, 22, 80, 78),
        line(110, 22, 110, 78),
        line(110, 50, 180, 50),
    ]
    if polarized:
        body.append(text(64, 14, "+"))
    return symbol_file(190, 100, body)


def inductor_symbol() -> str:
    return symbol_file(
        230,
        90,
        [
            line(10, 45, 45, 45),
            '<path d="M45 45 C45 19 75 19 75 45 C75 19 105 19 105 45 C105 19 135 19 135 45 C135 19 165 19 165 45" class="wire"/>',
            line(165, 45, 220, 45),
        ],
    )


def transformer_symbol() -> str:
    return symbol_file(
        360,
        120,
        [
            line(10, 60, 44, 60),
            '<path d="M44 60 C44 38 70 38 70 60 C70 38 96 38 96 60 C96 38 122 38 122 60" class="wire"/>',
            line(122, 60, 142, 60),
            line(160, 28, 160, 92, "thin"),
            line(170, 28, 170, 92, "thin"),
            line(190, 60, 210, 60),
            '<path d="M210 60 C210 38 236 38 236 60 C236 38 262 38 262 60 C262 38 288 38 288 60" class="wire"/>',
            line(288, 60, 350, 60),
        ],
    )


def diode_symbol() -> str:
    return symbol_file(180, 100, [line(10, 50, 50, 50), '<polygon points="50,24 50,76 96,50" class="wire"/>', line(100, 24, 100, 76), line(100, 50, 170, 50)])


def zener_symbol() -> str:
    return symbol_file(
        180,
        100,
        [
            line(10, 50, 50, 50),
            '<polygon points="50,24 50,76 96,50" class="wire"/>',
            poly([(100, 24), (100, 42), (112, 42)]),
            poly([(100, 76), (100, 58), (88, 58)]),
            line(100, 50, 170, 50),
        ],
    )


def led_symbol() -> str:
    return symbol_file(
        220,
        130,
        [
            line(10, 70, 50, 70),
            '<polygon points="50,44 50,96 96,70" class="wire"/>',
            line(100, 44, 100, 96),
            line(100, 70, 170, 70),
            line(126, 38, 142, 22, "thin"),
            poly([(136, 22), (142, 22), (142, 28)], "thin"),
            line(114, 22, 130, 6, "thin"),
            poly([(124, 6), (130, 6), (130, 12)], "thin"),
        ],
    )


def bjt_symbol(kind: str) -> str:
    if kind not in {"npn", "pnp"}:
        raise ValueError(kind)
    arrow = '<polygon points="120,127 105,125 111,114" fill="#111"/>' if kind == "npn" else '<polygon points="97,65 112,66 106,77" fill="#111"/>'
    return symbol_file(
        180,
        180,
        [
            '<circle cx="90" cy="90" r="48" class="wire"/>',
            line(42, 90, 76, 90),
            line(76, 60, 76, 120),
            line(76, 70, 120, 48),
            line(76, 110, 120, 132),
            arrow,
        ],
    )


def opamp_symbol() -> str:
    return symbol_file(
        240,
        160,
        [
            '<polygon points="60,20 60,140 190,80" class="wire"/>',
            line(10, 50, 60, 50),
            line(10, 110, 60, 110),
            line(190, 80, 230, 80),
            text(38, 54, "+"),
            text(40, 114, "-"),
        ],
    )


def ground_symbol() -> str:
    return symbol_file(120, 120, [line(60, 10, 60, 44), line(30, 44, 90, 44), line(40, 60, 80, 60), line(50, 76, 70, 76)])


def junction_symbol() -> str:
    return symbol_file(140, 140, [line(10, 70, 130, 70), line(70, 10, 70, 130), '<circle cx="70" cy="70" r="5" class="node"/>'])


def battery_symbol() -> str:
    return symbol_file(190, 120, [line(10, 60, 68, 60), line(68, 24, 68, 96), line(96, 38, 96, 82), line(96, 60, 180, 60), text(56, 16, "+")])


def switch_symbol() -> str:
    return symbol_file(210, 120, [line(10, 70, 55, 70), '<circle cx="55" cy="70" r="4" class="node"/>', line(55, 70, 122, 32), '<circle cx="158" cy="70" r="4" class="node"/>', line(158, 70, 200, 70)])


def fuse_symbol() -> str:
    return symbol_file(230, 110, [line(10, 55, 50, 55), rect(50, 35, 96, 40), line(146, 55, 220, 55)])


def loudspeaker_symbol() -> str:
    return symbol_file(240, 140, [line(10, 70, 65, 70), rect(65, 38, 36, 64), '<polygon points="101,48 170,16 170,124 101,92" class="wire"/>', line(170, 70, 230, 70)])


def net_label_symbol() -> str:
    return symbol_file(190, 90, [line(10, 45, 100, 45), text(110, 50, "OUT")])


def write_symbols(style: str, symbols: dict[str, str]) -> None:
    symbols_dir = ROOT / style / "symbols"
    for name, body in symbols.items():
        write(symbols_dir / f"{name}.svg", body)


def main() -> None:
    common_note = "Project-local redrawings; verify exact symbols against the cited standard when strict compliance is needed."

    gost_groups = [
        resistor_rect(50, 110, "Resistor, R", "GOST/IEC rectangle; keep aspect ratio."),
        variable_resistor_rect(330, 110, "Variable resistor, RP", "Diagonal arrow marks adjustment."),
        capacitor(620, 110, "Capacitor, C", "Parallel plates."),
        capacitor(900, 110, "Electrolytic capacitor, C", "Separate plus sign.", True),
        inductor(50, 255, "Inductor, L", "Coil form; core marks optional."),
        diode_group(330, 255, "Diode / Zener / LED, VD", "Use VD designators in Russian-style schematics."),
        bjt_pair(50, 420, "BJT NPN / PNP, VT", "Arrow direction and placement must be exact."),
        opamp(390, 420, "Operational amplifier, DA", "Analog IC element."),
        switch_fuse(690, 420, "Switch and fuse, SA / FU", "Keep contacts and fuse body readable."),
        ground_junction(50, 640, "Ground and junction", "Dot only for real junctions."),
        battery(390, 640, "Battery / DC source, G / GB", "Electrochemical source family."),
        loudspeaker(690, 640, "Loudspeaker, B", "Acoustic load symbol."),
        net_label(960, 640, "Net label", "Use for long feedback/supply links."),
    ]
    write(ROOT / "gost" / "part_symbols_gost.svg", sheet("GOST / ESKD-style part symbols", common_note, gost_groups))

    iec_groups = [
        resistor_rect(50, 110, "Resistor", "IEC-style rectangle."),
        variable_resistor_rect(330, 110, "Variable resistor", "Arrow shows adjustability."),
        capacitor(620, 110, "Capacitor", "Parallel plates."),
        capacitor(900, 110, "Polarized capacitor", "Polarity mark shown separately.", True),
        inductor(50, 255, "Inductor", "Coil form."),
        diode_group(330, 255, "Diode / Zener / LED", "Semiconductor symbols."),
        bjt_pair(50, 420, "BJT NPN / PNP", "Arrow remains inside the circle here."),
        opamp(390, 420, "Operational amplifier", "Common practical triangle form."),
        switch_fuse(690, 420, "Switch and fuse", "Readable contacts."),
        ground_junction(50, 640, "Ground and junction", "Explicit node dot."),
        battery(390, 640, "Battery / DC source", "Long plate is positive."),
        loudspeaker(690, 640, "Loudspeaker", "Electroacoustic transducer."),
        net_label(960, 640, "Net label", "Project routing aid."),
    ]
    write(ROOT / "iec" / "part_symbols_iec.svg", sheet("IEC-style part symbols", common_note, iec_groups))

    ansi_groups = [
        resistor_zigzag(50, 110, "Resistor", "ANSI/US zig-zag style."),
        variable_resistor_zigzag(330, 110, "Variable resistor", "Diagonal arrow over zig-zag."),
        capacitor(620, 110, "Capacitor", "Parallel plates."),
        capacitor(900, 110, "Polarized capacitor", "Project keeps explicit plus mark.", True),
        inductor(50, 255, "Inductor", "Coil form."),
        diode_group(330, 255, "Diode / Zener / LED", "Semiconductor symbols."),
        bjt_pair(50, 420, "BJT NPN / PNP", "Check arrow direction carefully."),
        opamp(390, 420, "Operational amplifier", "Triangle op-amp symbol."),
        switch_fuse(690, 420, "Switch and fuse", "Readable contacts."),
        ground_junction(50, 640, "Ground and junction", "Explicit node dot."),
        battery(390, 640, "Battery / DC source", "Long plate is positive."),
        loudspeaker(690, 640, "Loudspeaker", "Electroacoustic transducer."),
        net_label(960, 640, "Net label", "Project routing aid."),
    ]
    write(ROOT / "ansi" / "part_symbols_ansi.svg", sheet("ANSI-style part symbols", common_note, ansi_groups))

    shared = {
        "capacitor": capacitor_symbol(False),
        "polarized_capacitor": capacitor_symbol(True),
        "inductor": inductor_symbol(),
        "transformer": transformer_symbol(),
        "diode": diode_symbol(),
        "zener_diode": zener_symbol(),
        "led": led_symbol(),
        "bjt_npn": bjt_symbol("npn"),
        "bjt_pnp": bjt_symbol("pnp"),
        "opamp": opamp_symbol(),
        "ground": ground_symbol(),
        "junction_dot": junction_symbol(),
        "battery": battery_symbol(),
        "switch": switch_symbol(),
        "fuse": fuse_symbol(),
        "loudspeaker": loudspeaker_symbol(),
        "net_label": net_label_symbol(),
    }
    rectangular = {
        "resistor": resistor_rect_symbol(),
        "variable_resistor": variable_resistor_rect_symbol(),
        **shared,
    }
    zigzag = {
        "resistor": resistor_zigzag_symbol(),
        "variable_resistor": variable_resistor_zigzag_symbol(),
        **shared,
    }
    write_symbols("gost", rectangular)
    write_symbols("iec", rectangular)
    write_symbols("ansi", zigzag)


if __name__ == "__main__":
    main()
