# Analog Sketch Lab

Standalone browser GUI for sketching and simulating small analog schematics.

Open `index.html` in a browser. No package install is required.

## What It Supports

- Canvas schematic editor with select, drag, wire, and component placement tools.
- Components: resistors, capacitors, voltage sources, current sources, diodes, NPN/PNP BJTs, idealized op-amps, and ground.
- Built-in examples:
  - RC low-pass filter.
  - Half-wave rectifier.
  - BJT common-emitter amplifier.
  - Inverting op-amp low-pass amplifier.
- DC operating point solve.
- Transient solve with a scope plot for any resolved circuit node.
- SPICE-like netlist export.
- Save/restore circuit JSON in browser local storage.

## Simulation Notes

The solver is intentionally compact and local:

- Resistors are linear conductances.
- Capacitors use backward-Euler transient stamping.
- Voltage sources use MNA branch-current equations.
- Diodes use a simple exponential diode equation.
- BJTs use a simplified Ebers-Moll-like exponential model.
- Op-amps are finite-gain controlled sources with soft rail limiting.

This is good for education, topology sketching, and quick sanity checks. It is not a replacement for ngspice, Xyce, LTspice, Qucs-S, or bench validation.

## Open-Source References Used

- CircuitJS1: browser-based electronic circuit simulator.
  https://github.com/pfalstad/circuitjs1
- ngspice: open-source SPICE simulator for passive and active analog/digital devices.
  https://ngspice.sourceforge.io/index.html
- Qucs-S: Qt GUI with schematic capture, device libraries, and multiple simulation kernels including ngspice and Xyce.
  https://github.com/ra3xdh/qucs_s
- Xyce: open-source SPICE-compatible high-performance analog simulator.
  https://xyce.sandia.gov/
- Mosaic: web-based analog schematic entry/simulation flow using ngspice/Xyce in its open-source edition.
  https://nyancad.github.io/Mosaic/

## Next Useful Steps

- Add AC small-signal analysis.
- Add inductors and controlled sources.
- Add model cards and real transistor/op-amp libraries.
- Add import/export for `.cir` files.
- Add optional ngspice backend when a local `ngspice` binary is available.
