# ANSI / IEEE Symbols

Project-local redrawings for ANSI/IEEE-style schematics. Use this folder when reading or producing American-style drawings, especially older English-language magazines that use zig-zag resistors.

- [part_symbols_ansi.svg](part_symbols_ansi.svg)
- [part_symbols_ansi.png](part_symbols_ansi.png)
- [symbols](symbols/): one SVG and one PNG per symbol.
- [../common/symbols](../common/symbols/): canonical files for symbols identical across the current GOST, IEC, and ANSI redrawings.

Primary reference: IEEE/ANSI 315.

Style-specific key files include [resistor](symbols/resistor.svg) and [variable resistor](symbols/variable_resistor.svg); the ANSI resistor symbols use the zig-zag style. Shared symbols should normally link to [capacitor](../common/symbols/capacitor.svg), [inductor](../common/symbols/inductor.svg), [diode](../common/symbols/diode.svg), [BJT NPN](../common/symbols/bjt_npn.svg), [BJT PNP](../common/symbols/bjt_pnp.svg), [op-amp](../common/symbols/opamp.svg), and [loudspeaker](../common/symbols/loudspeaker.svg).
