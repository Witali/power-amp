# Schematic Drawing Rules

Reusable rules for generated schematic images in this project.

Project-local symbol library and source links are stored in [part_symbols](../part_symbols/README.md).

## Drawing Priorities

When rules conflict, use this order:

1. Preserve symbol proportions and terminal meaning. Do not resize, squash, stretch, mirror, or distort UGO symbols to make the layout fit.
2. Prevent overlaps and ambiguous reading. Components, wires, node dots, polarity marks, and labels must not cross each other; keep readable clearance around them.
3. Prefer short, simple conductors. After the first two priorities are satisfied, route wires with minimum practical length and minimum bends.

If a compact route would require distorted symbols or tight overlaps, move parts apart or enlarge the schematic instead.

Draw element symbols with maximum practical fidelity. Match the required arrow directions, dot placement, polarity marks, terminal positions, plate/line shapes, and small distinguishing details; do not replace them with merely similar-looking approximations.

## GOST/ESKD References

Use these standards as the baseline when drawing Russian-style radio schematics:

- [GOST 2.701-2008](https://docs.cntd.ru/document/1200069439/titles): scheme types and general requirements. For complete analog circuits, treat the drawing as an electrical schematic diagram (`E3` / `Э3`) unless another type is explicitly requested.
- [GOST 2.702-2011](https://docs.cntd.ru/document/1200086241): rules for electrical schematics.
- [GOST 2.721-74](https://protect.gost.ru/gost/details/c153a749-14f2-49e8-8544-acc32ab35406): general-purpose UGO symbols, including electrical connections, wires, buses, grounding, screens, and signal/current direction marks.
- [GOST 2.728-74](https://docs.cntd.ru/document/1200006616): UGO symbols for resistors and capacitors.
- [GOST 2.730-73](https://docs.cntd.ru/document/1200006618/titles/7DA0K5): UGO symbols for semiconductor devices, including diodes and bipolar transistors.
- [GOST 2.710-81](https://www.gostinfo.ru/catalog/Details/?id=4131401): letter-number reference designations in electrical schematics.

## Symbols

- Prefer GOST/ESKD-style UGO for Russian-language radio schematics.
- Use standardized UGO families consistently: resistors and capacitors from `GOST 2.728-74`, semiconductor devices from `GOST 2.730-73`, and grounding/connection/common marks from `GOST 2.721-74`.
- Keep component symbols in fixed proportions. Do not stretch parts horizontally or vertically to solve layout problems.
- Draw resistors as rectangles, not zig-zags.
- Keep resistor UGO rectangles at a consistent aspect ratio; move neighboring parts or enlarge the schematic instead of compressing a resistor body.
- Draw electrolytic capacitors as capacitor plates plus a separate polarity mark.
- Draw bipolar transistors with clear NPN/PNP arrows. The arrow must stay inside the transistor circle and be visually symmetric around the emitter line.
- Use a speaker symbol for a real loudspeaker load, not just a resistor box, when the load is meant to be a speaker.
- Keep UGO orientation conventional and readable. Rotate symbols by 90 degrees when needed, but do not mirror or distort them in a way that changes terminal meaning.
- Use separate functional symbols instead of rectangular placeholders for ordinary radio parts whenever the element type is known.

## Wiring

- Prefer vertical and horizontal conductors.
- Use diagonal conductors only where the established schematic shape expects them, or where an orthogonal route would be less readable.
- Avoid unnecessary bends. Each bend should route around a component, avoid a label, or align with a meaningful net path.
- Avoid compact nested hook shapes at junctions or crossings. If a route starts to look like a folded symbol, redraw it as a plain vertical/horizontal trunk with one clear T-connection.
- Keep a visible straight lead before each bend at a component terminal. Do not turn a wire immediately next to a component body or symbol outline.
- Avoid crossing components, wires, and labels. Rearrange the schematic before accepting an ambiguous crossing.
- Leave readable clearance around component bodies, transistor circles, labels, polarity marks, and node dots.
- Use net labels for long feedback, bootstrap, supply, or output links when a physical wire would make the schematic less readable.
- Draw electrical links as continuous visible conductors unless a net label or explicit break makes the circuit easier to read.
- Do not use corners, symbol endpoints, graphical dots inside component symbols, or line crossings as implicit branch points.
- If several conductors run in the same direction for a long distance, separate them clearly; use bus/group-line notation only when it improves readability and every branch remains identifiable.

## Connection Dots

- Put a visible dot only where three or more conductors meet electrically.
- Do not put dots on simple two-terminal or straight-through connections.
- Do not rely on crossings to imply a connection. If a crossing must be connected, redraw it as an explicit junction with a dot.
- Keep dots away from component outlines so the junction is visually distinct.
- For unconnected crossing conductors, leave the crossing without a dot and keep enough clearance that it cannot be mistaken for a junction.

## Layout

- Preserve the functional flow of the circuit: input on the left, output/load on the right, supply rails above, ground below.
- If the drawing becomes crowded, enlarge the schematic canvas or increase spacing between stages instead of changing component proportions.
- Place bias chains and feedback/bias resistors close to the stage they control, but with enough routing clearance.
- Keep related transistor pairs visually paired and aligned when possible.
- Prefer one clean trunk for shared output or supply nodes, with branches leaving at right angles.
- If the schematic is based on an original scan, keep the topology recognizable while still improving readability.
- Arrange UGO positions for simple, clear electrical reading; exact physical placement is secondary unless the requested schematic type is a wiring, connection, or layout diagram.
- Use the line-by-line or separated-symbol method only for complex multi-part devices or large repeated structures, and add enough cross references that all parts of the same device are easy to find.
- Keep input/output connectors, supply rails, and external loads visually distinct from the internal amplifier stages.

## Text And Designators

- Assign reference designators according to `GOST 2.710-81` style families where possible: `R` for resistors, `C` for capacitors, `VD` for diodes, `VT` for transistors, `B` or a clear project-local symbol for electroacoustic loads.
- Place a component reference designator and value close to its UGO, preferably above or to the right, without crossing wires or touching the symbol.
- Keep designators sequential after deleting or adding parts unless preserving the original article's numbering is more important for traceability.
- For selected or tuned parts, mark the designator with `*` and add a nearby note such as `* selected during adjustment` / `* подбирают при регулировании`.
- Use one value notation style per drawing. For this project, generated English-compatible SVGs may use `ohm`, `k`, `M`, `uF`; for strict Russian ESKD output, switch to localized SI notation consistently.
