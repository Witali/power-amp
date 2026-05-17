# SPICE-Component Simulation Results

This pass replaces the earlier behavioral transfer screen with transistor-level SPICE-style components. The local machine does not have ngspice/LTspice/PySpice installed, so the script solves the generated `Q`/`R`/`C`/`V` circuits with a small Python nodal solver using a simplified BJT exponential model.

Selected best for the current no-overall-feedback target: **Variant 02 - Rogov-style triple emitter follower output**.

Best component-simulation schematic: `best_spice_component_schematic.svg`.

| Rank | ID | Score | 1 W THD % | 5 W THD % | Clean W @ 1% THD | Rout ohm | Damping | No-Global Align | Topology |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 02 | 88.22 | 0.0014 | 0.0035 | 9.0 | 0.1651 | 48.5 | 1.0 | Rogov-style triple emitter follower output |
| 2 | 01 | 87.46 | 0.0371 | 0.0649 | 9.0 | 0.2405 | 33.3 | 1.0 | Classic BJT differential amp, double emitter follower |
| 3 | 03 | 86.43 | 0.0401 | 0.0487 | 9.0 | 0.2503 | 32.0 | 1.0 | Low-voltage folded cascode VAS, double emitter follower |
| 4 | 05 | 82.67 | 0.0223 | 0.0507 | 9.0 | 0.1574 | 50.8 | 0.55 | Discrete current-feedback BJT power amplifier |
| 5 | 04 | 29.73 | 7.7528 | 3.6067 | 0.0 | 999.0 | 0.0 | 1.0 | Complementary folded cascode with CFP/Sziklai output |

Caveat: the solver is intentionally small. It is useful for comparing these five component topologies under the same assumptions, not for final PCB values, SOA, thermal runaway, or high-frequency compensation signoff.

Generated files:

- `spice_component_results.csv`
- `spice_component_netlists/*.cir`
- `best_spice_component_schematic.svg`
- existing transistor-symbol schematics in `schematics/*.svg`
