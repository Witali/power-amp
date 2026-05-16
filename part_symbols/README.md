# Part Symbols

Last checked: 2026-05-17.

This folder is a local reference for schematic symbols used in generated radio and audio-amplifier drawings. The folder name is `part_symbols` because these are reusable schematic part symbols, not physical package drawings.

The SVG symbols in this folder are project-local redrawings. They are intended as a practical visual guide for our generated schematics and should not be treated as verbatim copies of any standard.

## Structure

- [gost](gost/README.md): GOST/ESKD-style symbols for Russian schematics.
- [iec](iec/README.md): IEC-style symbols for international/European schematics.
- [ansi](ansi/README.md): ANSI/IEEE-style symbols for American schematics.
- [common](common/README.md): symbols that are identical in the current local GOST, IEC, and ANSI redrawings.
- [part_symbols.svg](part_symbols.svg): older combined overview sheet.
- [part_symbols.png](part_symbols.png): rendered PNG version of the combined overview sheet.
- [symbol_sources.md](symbol_sources.md): source links for standards and practical references.
- [generate_part_symbols.py](generate_part_symbols.py): generator for the per-style SVG sheets and individual SVG symbol files.

## Per-Style Sheets

| Style | SVG | PNG | Main use |
|---|---|---|---|
| Common | [part_symbols_common.svg](common/part_symbols_common.svg) | [part_symbols_common.png](common/part_symbols_common.png) | Canonical shared symbols used by all current local style families. |
| GOST / ESKD | [part_symbols_gost.svg](gost/part_symbols_gost.svg) | [part_symbols_gost.png](gost/part_symbols_gost.png) | Russian radio schematics, `archive.radio.ru`, project default. |
| IEC | [part_symbols_iec.svg](iec/part_symbols_iec.svg) | [part_symbols_iec.png](iec/part_symbols_iec.png) | European/international-style schematics. |
| ANSI / IEEE | [part_symbols_ansi.svg](ansi/part_symbols_ansi.svg) | [part_symbols_ansi.png](ansi/part_symbols_ansi.png) | American-style schematics and older English-language magazines. |

## Individual Symbols

The [common/symbols](common/symbols/) folder is the canonical home for symbols that are identical in all current local style families. Each style folder also has a `symbols/` directory for style-specific symbols and compatibility copies. Example paths:

- `common/symbols/capacitor.svg`
- `common/symbols/bjt_npn.svg`
- `gost/symbols/resistor.svg`
- `ansi/symbols/resistor.svg`
- `common/symbols/diode.svg`
- `common/symbols/loudspeaker.svg`

Use the individual SVG files as the reusable source for future schematic generators. The PNG files are previews.

## Validation

Run the project SVG linter after changing symbol files:

```powershell
python scripts\lint_svg.py part_symbols
```

The symbol generator also runs this linter immediately after writing every SVG sheet and every individual symbol file. If a new symbol is malformed, generation stops before stale previews can hide the problem.

## Drawing Priority

Use the same priority order as the main schematic drawing rules:

1. Preserve symbol proportions and terminal meaning.
2. Prevent overlaps between components, wires, node dots, polarity marks, and labels.
3. Then minimize conductor length and the number of bends.

If a symbol or label does not fit, move parts apart or enlarge the schematic. Do not squash or stretch the UGO.

Draw every element with maximum practical fidelity. Arrow directions, dot placement, polarity marks, terminal positions, plate/line shapes, and small distinguishing details must match the intended symbol, not just resemble it.

## Project Defaults

- Use GOST/IEC-style rectangular resistors by default, not zig-zag resistors.
- Use clear capacitor plates plus a separate `+` mark for polarized capacitors.
- Use clean BJT symbols with arrows inside the circle.
- Use explicit node dots only where three or more conductors meet.
- Use net labels for long feedback, bootstrap, supply, or output connections when a physical wire would make the schematic less readable.
