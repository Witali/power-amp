# Selected Amplifier Curves

Selected variant: **02 - Rogov-style triple emitter follower output**.

The plots combine the local SPICE-style BJT output-stage component simulation with the selected VAS bandwidth estimate from the topology study. They are comparison/design curves, not a production ngspice signoff.

Files:

- `best_spice_component_schematic.svg`
- `plots/gain_vs_frequency.svg`
- `plots/thd_vs_frequency_5w.svg`
- `plots/thd_vs_output_power_1khz.svg`
- `plots/selected_amp_curve_data.csv`

Key simulated points:

- 1 kHz, 1 W THD: 0.0014%.
- 1 kHz, 5 W THD: 0.0035%.
- Clean output power before 1% THD in the component screen: 9.0 W / 8 ohm.
- Estimated damping factor: 48.5.
- Nominal voltage gain: 10 V/V (20.00 dB).
