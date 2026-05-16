# Schematic Drawing Rules

Reusable rules for generated schematic images in this project.

## Symbols

- Prefer GOST/ESKD-style UGO for Russian-language radio schematics.
- Keep component symbols in fixed proportions. Do not stretch parts horizontally or vertically to solve layout problems.
- Draw resistors as rectangles, not zig-zags.
- Draw electrolytic capacitors as capacitor plates plus a separate polarity mark.
- Draw bipolar transistors with clear NPN/PNP arrows. The arrow must stay inside the transistor circle and be visually symmetric around the emitter line.
- Use a speaker symbol for a real loudspeaker load, not just a resistor box, when the load is meant to be a speaker.

## Wiring

- Prefer vertical and horizontal conductors.
- Use diagonal conductors only where the established schematic shape expects them, or where an orthogonal route would be less readable.
- Avoid unnecessary bends. Each bend should route around a component, avoid a label, or align with a meaningful net path.
- Keep a visible straight lead before each bend at a component terminal. Do not turn a wire immediately next to a component body or symbol outline.
- Avoid crossing components, wires, and labels. Rearrange the schematic before accepting an ambiguous crossing.
- Leave readable clearance around component bodies, transistor circles, labels, polarity marks, and node dots.
- Use net labels for long feedback, bootstrap, supply, or output links when a physical wire would make the schematic less readable.

## Connection Dots

- Put a visible dot only where three or more conductors meet electrically.
- Do not put dots on simple two-terminal or straight-through connections.
- Do not rely on crossings to imply a connection. If a crossing must be connected, redraw it as an explicit junction with a dot.
- Keep dots away from component outlines so the junction is visually distinct.

## Layout

- Preserve the functional flow of the circuit: input on the left, output/load on the right, supply rails above, ground below.
- If the drawing becomes crowded, enlarge the schematic canvas or increase spacing between stages instead of changing component proportions.
- Place bias chains and feedback/bias resistors close to the stage they control, but with enough routing clearance.
- Keep related transistor pairs visually paired and aligned when possible.
- Prefer one clean trunk for shared output or supply nodes, with branches leaving at right angles.
- If the schematic is based on an original scan, keep the topology recognizable while still improving readability.
