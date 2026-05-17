# No-Overall-Feedback Audio Power Amplifier Best Practices

These notes summarize the practical design ideas learned while comparing no-global-feedback audio power amplifier topologies with total voltage gain constrained to `Av = 10`.

## Main Direction

The best-scoring local candidate is a complementary cascoded voltage amplifier stage followed by a high-linearity emitter-follower output buffer.

Use this as the preferred architecture:

```text
input buffer
  -> complementary cascoded VAS with local degeneration
  -> thermally tracked bias spreader
  -> double or triple complementary emitter follower
  -> output relay, Zobel, and protection
```

The simpler fallback is the same complementary cascoded VAS with a double emitter follower instead of a triple emitter follower. It gives up some damping and output drive, but is easier to bias and stabilize.

## Update For Class AB, +/-15 V Rails

With a `+15 V / 0 / -15 V` supply and Class AB bias, headroom becomes the dominant constraint. A triple emitter follower is no longer the natural first choice because the extra Vbe drops reduce maximum clean swing.

For this low-voltage AB version, prefer:

```text
input pair or buffer
  -> low-voltage folded cascode VAS
  -> thermally tracked AB bias network
  -> CFP/Sziklai or double emitter-follower output
  -> output relay, Zobel, and protection
```

The best-scoring updated candidate is:

```text
complementary folded cascode VAS
  -> complementary feedback pair / Sziklai local output stage
  -> Class AB bias
```

The safer fallback is:

```text
complementary cascoded VAS
  -> double complementary emitter follower
  -> Class AB bias
```

The CFP/Sziklai output is attractive on `+/-15 V` because it preserves more output swing than a triple emitter follower. Its local feedback loop must be checked carefully for stability with real devices, PCB parasitics, and capacitive speaker cables.

Expected practical output is roughly single-digit watts into `8R`. In the behavioral comparison, the best candidate reached about `9 W` before the `1%` THD threshold; treat that as a topology estimate, not a hardware guarantee.

## Useful Ideas From Existing Designs

- Zen-style single-ended MOSFET amplifiers show that simple, high-bias Class A stages can sound and measure respectably without global feedback, but they run hot and have low damping factor.
- Son-of-Zen / balanced ideas are useful because symmetry cancels even-order distortion without requiring an output-to-input feedback loop.
- Cascode stages are useful in the VAS because they reduce voltage swing across the gain transistor, lowering capacitance modulation and Miller-related distortion.
- F4-style thinking is useful for the output stage: let the final stage behave mostly as a no-feedback current buffer, not as another voltage-gain stage.
- Folded cascode plus compound emitter follower is a very strong alternative, especially for Class A, but thermal cost is high.

## Best Practices

- Keep the total gain modest and explicit. For this study, use `Av = 10`.
- Avoid any wire from `OUT` back to the input stage if the design goal is truly no overall/global feedback.
- Still use local linearization: emitter/source degeneration, output emitter resistors, base/gate stoppers, and well-designed current sources.
- Put the cascode in the VAS or input/VAS transition, not in the large-current output devices unless there is a very specific reason.
- Prefer complementary or balanced voltage-gain structures over a single-ended VAS when trying to reduce even-order distortion without global feedback.
- Use transistor/resistor current sources and sinks rather than idealized current-source symbols in the real schematic.
- Choose a bias spreader that thermally tracks the output devices. A Vbe multiplier on the heatsink is the minimum practical approach for BJT emitter-follower outputs.
- Use emitter resistors on output devices, typically in the `0.1R` to `0.33R` range, for current sharing, local feedback, and idle-current measurement.
- Add base stopper resistors on drivers and outputs to reduce parasitic oscillation risk.
- Add a Zobel network at the output, commonly around `10R + 100nF`, adjusted after stability testing.
- Use a speaker relay or DC protection circuit. No-global-feedback designs can still fail with DC at the output.
- Treat DC offset seriously. Use matching, thermal symmetry, and possibly a DC servo if very-low-frequency feedback is acceptable.
- Keep the power supply quiet. No-feedback and low-feedback designs usually have worse PSRR than conventional high-loop-gain amplifiers.
- Keep layout compact around the VAS, drivers, and output transistor bases. Long leads are part of the circuit at audio-power bandwidths.
- Separate signal ground and power ground intentionally, then join at a controlled point.
- Test with resistive and reactive loads, not only an `8R` resistor.
- Check square-wave behavior at several frequencies and with capacitive loading before connecting valuable speakers.

## Schematic Drawing Rules

General reusable drawing rules are stored in [schematic_drawing_rules.md](../docs/schematic_drawing_rules.md).

- Use ESKD/GOST-style UGO for local Russian-language schematics: rectangular resistors, capacitor plates with a separate polarity mark for electrolytics, diode/transistor symbols from the semiconductor UGO family, and a speaker symbol for an actual loudspeaker load.
- Avoid intersections between parts, wires, and labels. Rearrange the schematic before accepting an ambiguous crossing.
- Prefer vertical and horizontal wires, and avoid unnecessary bends. Every bend should either route around a symbol/label or align with a meaningful net path.
- Keep a visible straight lead before each bend at a component terminal; do not turn a wire immediately next to a component body or symbol outline.
- Mark only junctions where three or more conductors meet with a visible connection dot. Do not draw dots for simple two-terminal/straight-through connections.
- Use net labels for long feedback or bootstrap links when a physical wire would make the schematic less readable.

## Practical Selection Guidance

Choose the triple emitter-follower output if:

- you need better damping factor,
- you are comfortable with careful thermal bias setup,
- you can validate stability on the bench.

Choose the double emitter-follower output if:

- you want a simpler, more buildable amplifier,
- you want fewer bias-tracking problems,
- the speaker load is not especially difficult.

Choose the folded-cascode / compound-follower Class A approach if:

- heat and power consumption are acceptable,
- you want a documented no-feedback style architecture,
- you are comfortable with high idle current and large heatsinks.

## Simulation Caveat

The local comparison used a pure-Python behavioral model because `ngspice` and `ltspice` were not available locally. The results are useful for ranking topology direction, not for final hardware signoff.

Before building hardware, create a transistor-level SPICE model and verify:

- operating points,
- thermal drift,
- clipping symmetry,
- slew behavior,
- distortion at multiple powers and frequencies,
- phase margin or large-signal stability indicators,
- output-stage SOA,
- startup and shutdown behavior,
- DC protection behavior.

## Distortion And Load Testing Addendum

Detailed distortion-test notes from the MusicForums article are stored in [musicforums_amplifier_distortion_notes.md](musicforums_amplifier_distortion_notes.md).

- Do not rank an amplifier by `THD @ 1 kHz` alone. Check distortion spectrum, level dependence, and frequency dependence.
- Add low-power Class AB tests; crossover distortion can look worse as the signal level falls.
- Add two-tone IMD tests when possible, because music is not a single sine wave.
- Inspect output-device current waveforms in BJT output stages to catch charge-storage and commutation behavior.
- Test with `4R` short-duration load when the nominal target is `8R`, and add reactive/capacitive load checks.
- Treat thermal bias behavior dynamically: verify after warm-up, high-power soak, and abrupt transition back to low power.

## Source References

- [Pass DIY, The Zen Amplifier](https://www.passdiy.com/project/amplifiers/the-zen-amplifier)
- [Pass DIY, Cascode Amplifier Design](https://www.passdiy.com/project/amplifiers/cascode-amplifier-design)
- [Pass DIY, Zen Variations 6](https://www.passdiy.com/project/amplifiers/zen-variations-6)
- [First Watt F4](https://www.firstwatt.com/product/f4/)
- [Andiha, Class A Cascode Power Amplifier](https://www.andiha.no/audio/projects/cascode.html)
- [MusicForums, "Усилитель: что мешает звучать правильно? (часть 1)"](http://www.musicforums.ru/article/1312403108.html)
