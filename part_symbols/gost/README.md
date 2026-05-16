# GOST / ESKD Symbols

Project-local redrawings for Russian-style schematics. Use these as the default family for `archive.radio.ru` and Russian radio/audio schematics.

- [part_symbols_gost.svg](part_symbols_gost.svg)
- [part_symbols_gost.png](part_symbols_gost.png)
- [symbols](symbols/): one SVG and one PNG per symbol.
- [../common/symbols](../common/symbols/): canonical files for symbols identical across the current GOST, IEC, and ANSI redrawings.

Primary references: GOST 2.721, 2.723, 2.728, 2.730, 2.741, 2.742, 2.755, 2.759.

Style-specific key files include [resistor](symbols/resistor.svg) and [variable resistor](symbols/variable_resistor.svg). Shared symbols should normally link to [capacitor](../common/symbols/capacitor.svg), [inductor](../common/symbols/inductor.svg), [diode](../common/symbols/diode.svg), [BJT NPN](../common/symbols/bjt_npn.svg), [BJT PNP](../common/symbols/bjt_pnp.svg), [op-amp](../common/symbols/opamp.svg), and [loudspeaker](../common/symbols/loudspeaker.svg).
