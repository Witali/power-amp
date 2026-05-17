# MusicForums Amplifier Distortion Notes

Source: ["Усилитель: что мешает звучать правильно? (часть 1)"](http://www.musicforums.ru/article/1312403108.html), MusicForums, published 2011-08-04.

Copyright note: these are distilled engineering notes and reuse prompts, not a copy of the article.

## Why This Source Matters

The article is useful for our amplifier work because it treats audible quality as a system problem, not just a single `THD @ 1 kHz` number. It walks through harmonic distortion, clipping/crossover behavior, intermodulation, BJT switching effects, instability, real speaker loading, thermal transients, output impedance, and subjective audibility. The examples are PSPICE-oriented and many are simplified deliberately, but the test ideas are directly reusable in our ngspice/result workflow.

## Reusable Concepts

### Distortion Is Not One Number

- A low THD value at `1 kHz` and rated power is not enough to judge an amplifier.
- The spectrum composition matters: even/odd balance, high-order content, and whether distortion products land in the most audible band.
- Measure at several output powers, especially low power. Class AB crossover artifacts can become proportionally worse as signal level falls.
- For our plots, keep `THD vs frequency` and `THD vs output power`; add low-level points when comparing bias variants.

### Symmetry And Harmonic Content

- Asymmetric nonlinearity creates even harmonics.
- Symmetric nonlinearity tends to suppress even harmonics and emphasize odd components.
- For transistor stages, good matching and symmetric operating points matter even without global feedback.
- In no-global-feedback designs, do not expect feedback to hide input/VAS asymmetry; stage linearity and current-source balance must be designed in.

### Crossover Step And Clipping Are Different Failure Modes

- Crossover "step" distortion is associated with insufficient Class AB bias or poor transfer through zero crossing.
- It is especially dangerous at low signal levels, where the useful signal is small but the dead-zone remains comparable.
- Clipping/saturation is a high-level problem; it becomes prominent when the output swing or protection limits are reached.
- Simulations should separately report small-signal crossover behavior and large-signal clipping headroom.

### Intermodulation Should Be Tested

- Single-tone sine tests miss important behavior.
- Two-tone tests, such as low-frequency plus high-frequency excitation, reveal intermodulation products that are not obvious in `1 kHz` THD.
- Add a reusable IMD measurement later: for example `100 Hz + 2 kHz`, and optionally a higher-frequency pair closer to SMPTE/CCIF style checks.

### BJT Switching And Charge Storage

- Bipolar transistors do not turn off instantly; stored charge must be removed from the base region.
- Output stages that let one device remain conducting while the opposite device starts to conduct can create switching current spikes and distortion.
- Base discharge paths, driver impedance, base stoppers, and avoiding deep saturation are practical design issues, not cosmetic details.
- For emitter-follower outputs, inspect current waveforms in output devices, not only output voltage.

### Stability Margin Is Signal-Dependent

- HF stability depends on loop gain and phase shift, but transistor gain varies with current.
- A circuit that looks stable on one static sine test can move closer to oscillation under different levels, loads, or device spreads.
- Local feedback and degeneration reduce gain variation and make stability more predictable.
- Verify square-wave behavior and reactive/capacitive loads, not only resistive `8R`.

### Load And Cable Are Part Of The Amplifier

- A speaker is not just a resistor; it has mechanical inertia, inductance, resonance, and thermal resistance changes.
- A practical amplifier should tolerate a load down to about half the nominal impedance for short dynamic intervals.
- Speaker cable resistance adds to amplifier output resistance and changes electrical damping.
- Connector and solder quality are mentioned in the article; for our engineering notes the actionable part is to keep high-current connections low resistance, mechanically reliable, and measured rather than assumed.

### Thermal Transients In Class AB

- Bias tracking based on a heatsink-mounted Vbe multiplier is only approximate.
- Output transistor junction temperature can change faster than heatsink temperature.
- After a loud passage followed by a quiet one, the bias sensor may still be warm while output junctions have cooled, temporarily reducing idle current and increasing crossover distortion.
- For real hardware, check idle current after warm-up, after high-power soak, and after abrupt power-level changes.

### Slew And Dynamic Error

- Music is not a steady sine wave; fast level changes matter.
- Slew-rate limiting creates delay and error accumulation, especially when feedback has to recover after the output falls behind.
- Test with square waves and multi-tone transient signals. Our current 1 kHz/10 kHz square plots are a good start, but future amplifier variants should also include slew-sensitive tests at higher output amplitudes.

### Output Impedance And Damping

- Output resistance affects the electrical part of speaker damping and can change low-frequency behavior near resonance.
- Very low output resistance is not the only theoretical option, but it is the safest default for a general-purpose amplifier driving unknown speakers.
- If output impedance is intentionally raised or shaped, document the target speaker model and measure the resulting response.
- Continue reporting estimated output resistance and damping factor for every amplifier result.

### Audibility And Test Weighting

- Human hearing is most sensitive in the midrange, and distortion products from bass can land in that sensitive band.
- Low-frequency fundamentals can mask poorly, while their higher harmonics become more audible.
- A single full-power THD number can look good while low-level or high-order distortion remains audible.
- Rank future designs by a small matrix: low-power THD, 1 W THD, near-clipping THD, IMD, output impedance, square-wave stability, and reactive-load behavior.

## Reuse In This Project

- Add low-level THD points to amplifier plots, especially for Class AB bias experiments.
- Add a two-tone IMD plot once the reusable simulation runner supports it.
- Add output-device current plots for BJT output stages when diagnosing crossover/commutation behavior.
- Keep `8R` resistive load tests, but add `4R` short-duration checks for designs advertised as `8R` amplifiers.
- Add a simple reactive speaker-equivalent load for stability and damping checks.
- Treat bias as dynamic: a stable idle current immediately after warm-up is not enough for hardware confidence.

