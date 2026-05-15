# Power Amplifier Chat Summary

This folder contains the local artifacts from a design exploration for an audio power amplifier without overall/global feedback.

## Final Working Constraints

- Amplifier class: `Class AB`
- Power supply: `+15 V / 0 / -15 V`
- Load used in comparison: `8 ohm`
- Total voltage gain target: `Av = 10`
- Global feedback: none. No `OUT` to input/VAS feedback path.
- Local feedback/linearization is allowed: emitter/source degeneration, output emitter resistors, current sources, base/gate stoppers, and local CFP/Sziklai action.

## Current Best Topology

The latest behavioral comparison selected:

```text
Complementary folded cascode VAS
  -> CFP/Sziklai local Class AB output stage
  -> output relay / Zobel / protection
```

Why it won under the `+/-15 V` constraint:

- It preserves more output swing than a triple emitter-follower output.
- The folded cascode works better with low supply voltage than a taller cascoded VAS.
- The CFP/Sziklai output has strong local linearity and low estimated output impedance.
- It still has no overall/global output-to-input feedback path.

Main caveat:

The CFP/Sziklai output stage must be validated for stability with real transistors, PCB parasitics, and capacitive speaker loads.

## Latest Estimated Results

From the local Python behavioral comparison:

- Best variant: `07`
- Name: `Complementary folded cascode, CFP AB output`
- `1 W / 8R` THD estimate: `0.1025%`
- `5 W / 8R` THD estimate: `0.0501%`
- Clean power before `1%` THD estimate: about `9 W / 8R`
- `10 W / 8R` is near/into clipping on `+/-15 V` rails: estimated `2.1535%` THD

These are topology-screening estimates only, not transistor-level SPICE signoff.

## Important Files

- `amp_no_feedback_study/simulate_amp_variants.py`  
  Python behavioral comparison script.

- `amp_no_feedback_study/results.csv`  
  Ranked numeric results for the latest candidates.

- `amp_no_feedback_study/summary.md`  
  Human-readable report of the latest comparison.

- `amp_no_feedback_study/selected_topology.svg`  
  SVG block/schematic-style drawing of the selected topology.

- `amp_no_feedback_study/ten_topologies.svg`  
  SVG overview of all compared candidates.

- `amp_no_feedback_study/best_practices.md`  
  Design lessons and best-practice notes gathered during the discussion.

- `amp_no_feedback_study/behavioral_netlists/`  
  Placeholder SPICE-like netlist notes for the compared variants.

- `no_global_feedback_cascode_amp.svg`  
  Earlier conceptual schematic drawing.

## Design Notes

- Cascode is useful in the voltage amplifier stage, not usually in the large-current output devices.
- With `+/-15 V` rails, avoid output stages that waste too many Vbe drops.
- A triple emitter follower scored well at higher rails, but became less attractive at `+/-15 V`.
- A double emitter follower is the safer fallback if CFP/Sziklai stability is a concern.
- Use a Vbe multiplier or equivalent thermally coupled bias network for AB idle current.
- Use output emitter resistors, typically around `0.1R` to `0.33R`.
- Add speaker DC protection and a relay.
- Add a Zobel network at the output, then confirm stability on the bench.
- Keep power and signal grounds deliberately separated and joined at a controlled point.

## Required Next Step Before Hardware

Create a real transistor-level SPICE design and test:

- operating points,
- output swing on `+/-15 V`,
- bias thermal drift,
- crossover distortion,
- clipping symmetry,
- stability with capacitive loads,
- reactive speaker load behavior,
- SOA protection,
- startup/shutdown DC behavior.

Local `ngspice`/`ltspice` was not available during this session, so all current results are from the local Python behavioral model.
