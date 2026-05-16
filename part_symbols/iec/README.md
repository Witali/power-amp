# IEC Symbols

Project-local redrawings for IEC-style schematics. Use this folder when reading or producing European/international-style drawings.

- [part_symbols_iec.svg](part_symbols_iec.svg)
- [part_symbols_iec.png](part_symbols_iec.png)
- [symbols](symbols/): one SVG and one PNG per symbol.
- [../common/symbols](../common/symbols/): canonical files for symbols identical across the current GOST, IEC, and ANSI redrawings.

Primary reference: IEC 60617.

Style-specific key files include [resistor](symbols/resistor.svg) and [variable resistor](symbols/variable_resistor.svg). Shared symbols should normally link to [capacitor](../common/symbols/capacitor.svg), [inductor](../common/symbols/inductor.svg), [diode](../common/symbols/diode.svg), [BJT NPN](../common/symbols/bjt_npn.svg), [BJT PNP](../common/symbols/bjt_pnp.svg), [op-amp](../common/symbols/opamp.svg), and [loudspeaker](../common/symbols/loudspeaker.svg).
