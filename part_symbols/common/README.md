# Common Part Symbols

Last checked: 2026-05-17.

This folder contains project-local SVG symbols that are identical in the current GOST/ESKD, IEC, and ANSI/IEEE redrawings. Use these files when a schematic generator does not need a standard-specific override.

- [part_symbols_common.svg](part_symbols_common.svg)
- [part_symbols_common.png](part_symbols_common.png)
- [symbols](symbols/): one reusable SVG and one rendered PNG preview per shared symbol.

Style folders may keep compatibility copies, but new code should prefer these canonical common files when the symbol is the same in every local style family.

## Common Symbols

- `symbols/battery.svg`
- `symbols/bjt_npn.svg`
- `symbols/bjt_pnp.svg`
- `symbols/capacitor.svg`
- `symbols/diode.svg`
- `symbols/fuse.svg`
- `symbols/ground.svg`
- `symbols/inductor.svg`
- `symbols/junction_dot.svg`
- `symbols/led.svg`
- `symbols/loudspeaker.svg`
- `symbols/net_label.svg`
- `symbols/opamp.svg`
- `symbols/polarized_capacitor.svg`
- `symbols/switch.svg`
- `symbols/transformer.svg`
- `symbols/zener_diode.svg`

Resistors are not common across all current styles because ANSI uses zig-zag resistors while GOST and IEC use rectangular resistor symbols.
