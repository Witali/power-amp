# Radio.ru-Inspired Five-Variant BJT Amplifier Study

Current authoritative result: see `spice_component_summary.md`.

The first pass used a behavioral transfer model to sketch the trade space. After the request to use SPICE components, the study was rerun with generated `Q`/`R`/`C`/`V` netlists and a small local nodal solver because no `ngspice`, LTspice CLI, PySpice, Numpy, or Scipy installation was available in this workspace.

Selected best from the component simulation:

**Variant 02 - Rogov-style triple emitter follower output**

Why it won:

- It keeps the no-overall-feedback constraint.
- Its triple emitter-follower output reduces driver loading and output impedance.
- In the component run it had the lowest 1 W and 5 W THD among the no-global-feedback variants.
- The price is headroom: the extra `Vbe` drops make it less attractive if the target output power rises beyond the present +/-15 V, 8 ohm screen.

Generated files:

- `spice_component_summary.md`: current ranking and caveats.
- `spice_component_results.csv`: numeric component-simulation results.
- `spice_component_netlists/*.cir`: SPICE-style component netlists.
- `best_spice_component_schematic.svg`: selected schematic.
- `schematics/*.svg`: all five transistor-symbol schematics.
- `all_5_schematics.svg`: overview drawing of the five variants.
