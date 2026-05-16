# 001 Rogov Triple EF Amplifier

Selected amplifier variant from the Radio.ru-inspired five-topology study.

## What This Is

Topology: no-overall-feedback BJT amplifier using a Rogov-style triple emitter-follower output stage.

Context:

- Supply rails: `+/-15 V`
- Load: `8 ohm`
- Nominal voltage gain: `10 V/V`, about `20 dB`
- Output stage: three-stage complementary emitter follower
- Source basis: Rogov 2018 two-vs-three emitter-follower discussion plus Grechishkin 2013 BJT signal-path pattern

## Sources

- I. Rogov, "Выходной каскад УМЗЧ - две или три ступени повторителя?", `Радио`, 2018 №12, p.27. Official Radio annual table of contents: [ftp.radio.ru/pub/2018/12/2018.pdf](https://ftp.radio.ru/pub/2018/12/2018.pdf).
- Local collected notes: [amp_no_feedback_study/radio_ru_bjt_amplifier_knowledge.md](../../amp_no_feedback_study/radio_ru_bjt_amplifier_knowledge.md).

## Main Files

Schematic:

- `schematic/rogov_triple_ef_amplifier.svg`
- `schematic/rogov_triple_ef_amplifier.png` (`3600x2160`)

The current schematic redraw uses transistor symbols, rectangular resistor UGO style, explicit junction dots, and mostly orthogonal wiring for readability.

Plots:

- `plots/gain_vs_frequency.svg`
- `plots/gain_vs_frequency.png` (`1840x1000`)
- `plots/thd_vs_frequency_5w.svg`
- `plots/thd_vs_frequency_5w.png` (`1840x1000`)
- `plots/thd_vs_output_power_1khz.svg`
- `plots/thd_vs_output_power_1khz.png` (`1840x1000`)

Data and reproduction:

- `data/selected_amp_curve_data.csv`
- `data/spice_component_results.csv`
- `netlists/variant_02_rogov_triple_ef.cir`
- `source/*.py`

## Key Simulation Points

- `1 kHz, 1 W`: THD about `0.0014%`
- `1 kHz, 5 W`: THD about `0.0035%`
- Clean power before `1%` THD in the local component screen: about `9 W / 8 ohm`
- Estimated output resistance: about `0.165 ohm`
- Estimated damping factor: about `48.5`

## Caveat

These files are generated from the local simplified SPICE-style component model and topology study. They are useful for comparison and documentation, but not a final hardware signoff. Before building hardware, rerun with real transistor models in ngspice/LTspice, add protection/SOA checks, and verify thermal stability and capacitive-load behavior.
