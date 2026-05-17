# Archive.radio.ru UMZCH 20-Article Study

Source scope: official `archive.radio.ru` scans and issue contents pages. I searched newest archive years first, then moved backward until there were enough amplifier articles, preferring transistor-only or transistor-dominant UMZCH designs over IC-only amplifiers.

Copyright note: this file contains distilled engineering notes, OCR-derived pointers, and short bibliographic titles only. It does not reproduce article text or scanned pages.

## Method

- OCR tool: local Tesseract 5.5 with `rus+eng`.
- Issue contents pages were scanned from 2000 down to 1989 using `archive.radio.ru/web/img/YYYY/f.YYYY-MM.002.jpg`.
- Article pages were then OCR-read selectively around the relevant page ranges.
- Temporary OCR and downloaded scans are under `.tmp/archive_study/`; they are scratch files, not project knowledge.
- The source link in each row points to the article start or nearest verified article page in the official archive.

## Selection Bias

Priority order:

1. Newer article in the archive.
2. Main audio path is discrete transistor based.
3. Direct UMZCH schematic rather than only a peripheral or measurement note.
4. Useful design concept for later simulation: output stage, biasing, local feedback, protection, stability, or load interaction.

Legend:

- `Discrete`: main signal path is transistor-only or almost transistor-only.
- `Hybrid`: the article uses an op-amp or IC in the input/control/protection path, but still has useful discrete transistor power-stage ideas.
- `Theory`: mostly design method, not one complete build.

## 20 Studied Publications

| # | Rank | Article | Type | Main reusable ideas |
|---:|---|---|---|---|
| 1 | Very high | A. Petrov, "Два усилителя мощности ЗЧ", `Радио`, 2000 №10, p.14. [archive page](https://archive.radio.ru/web/2000/10/013) | Discrete, with protection IC | Fully transistor main amplifier, complementary differential/current stages, high-current output, low output resistance target, damping of loudspeaker resonance, output inductor/Zobel/protection as part of the amplifier rather than an afterthought. |
| 2 | Very high | V. Levitsky, "УМЗЧ с индуктивной коррекцией", `Радио`, 1999 №10, p.18. [archive page](https://archive.radio.ru/web/1999/10/017) | Discrete main path | Symmetric topology, inductive correction in output-transistor emitters, local feedback through the inductor/resistor network, simple biasing and thermal setup, low parts count without an IC in the main amplifier. |
| 3 | Very high | V. Khoroshev, A. Shadrov, "УМЗЧ без общей ООС", `Радио`, 1989 №9, p.65. [archive page](https://archive.radio.ru/web/1989/09/066) | Discrete | No-overall-feedback benchmark: gain set by stage ratios and local degeneration, differential input, current mirror/VAS-like gain stage, explicit distortion-compensation node, soft clipping behavior, strong relevance to our no-global-feedback direction. |
| 4 | Very high | I. Akulinichev, "УМЗЧ с глубокой ООС", `Радио`, 1989 №10, p.56. [archive page](https://archive.radio.ru/web/1989/10/057) | Discrete | Compact all-transistor deep-feedback amplifier, cascaded inverting voltage gain, current-source stabilization, complementary output, compensation/check procedure; useful as a contrast case to no-feedback designs. |
| 5 | High | V. Maltsev, "УМЗЧ с параллельной обратной связью", `Радио`, 1994 №8, p.15. [archive page](https://archive.radio.ru/web/1994/08/016) | Discrete | Parallel feedback variant, high input impedance, common-emitter voltage stage, split rail supply, practical tuning of quiescent current and zero offset, good example of keeping the signal path transistor-only. |
| 6 | High | L. Vinokurov, "УМЗЧ с питанием от низковольтного источника", `Радио`, 1995 №4, p.15. [archive page](https://archive.radio.ru/web/1995/04/014) | Discrete | Low-voltage bridge/symmetric transistor stages, deriving useful output from 1 to 3 V supplies, complementary push-pull tricks, bias current setup with a FET/current source. |
| 7 | High | S. Sakevich, "Простой эстрадный усилитель мощности", `Радио`, 2000 №11, p.12. [archive page](https://archive.radio.ru/web/2000/11/011) | Hybrid | High-power stage with many parallel BJTs, input op-amp as voltage-current converter, output transistor banks, overload and speaker protection, practical ventilation and field reliability ideas. |
| 8 | High | N. Rekunov, "Мостовой УМЗЧ с БСИТ", `Радио`, 2000 №9, p.12. [archive page](https://archive.radio.ru/web/2000/09/011) | Hybrid | Bridge output, BSIT/static-induction transistor use, floating load between two amplifier outputs, bias adjustment by output-stage current, practical high-power bridge symmetry concerns. |
| 9 | Medium-high | S. Ageev, "Сверхлинейный УМЗЧ с глубокой ООС", `Радио`, 1999 №10, p.16. [archive page](https://archive.radio.ru/web/1999/10/015) | Hybrid | Start of the superlinear/deep-feedback series: loop-gain discipline, layout and measurement focus, compensation of wire/speaker interaction, high loop gain as a system-level design choice. |
| 10 | Medium-high | S. Ageev, continuation, `Радио`, 1999 №11, p.13. [archive page](https://archive.radio.ru/web/1999/11/012) | Hybrid | Continuation of the same architecture: practical construction details, power stage and protection refinements, thermal and PCB constraints for very low distortion. |
| 11 | Medium-high | S. Ageev, continuation, `Радио`, 2000 №1, p.18. [archive page](https://archive.radio.ru/web/2000/01/017) | Hybrid | Component selection, bandwidth/phase margin caution, how small parasitics become significant when the feedback depth is very high. |
| 12 | Medium-high | S. Ageev, continuation, `Радио`, 2000 №2, sound section. [archive contents](https://archive.radio.ru/web/2000/02/002) | Hybrid | Load interaction and feedback-loop behavior around real loudspeakers; useful for simulation loads beyond a plain resistor. |
| 13 | Medium-high | S. Ageev, continuation, `Радио`, 2000 №4, p.40. [archive page](https://archive.radio.ru/web/2000/04/039) | Hybrid | Power supply, protection and construction details; careful separation of signal and power currents. |
| 14 | Medium-high | S. Ageev, continuation, `Радио`, 2000 №5, p.22. [archive page](https://archive.radio.ru/web/2000/05/021) | Hybrid | Further implementation details and setup procedure; strong reminder to verify stability and distortion after assembly, not only by schematic reasoning. |
| 15 | Medium-high | S. Ageev, continuation, `Радио`, 2000 №6, p.10. [archive page](https://archive.radio.ru/web/2000/06/010) | Hybrid | Construction, protection and measurement closure of the series; useful notes on avoiding hum, oscillation and wiring-induced errors. |
| 16 | Medium | M. Korzinin, "Схемотехника усилителей мощности звуковой частоты высокой верности", `Радио`, 1995 №11, p.12. [archive page](https://archive.radio.ru/web/1995/11/011) | Theory | Clear division of an UMZCH into voltage gain, current gain, output stage and protection. Useful for comparing single-ended, bridge and split-path architectures. |
| 17 | Medium | M. Korzinin, continuation, `Радио`, 1995 №12, p.16. [archive page](https://archive.radio.ru/web/1995/12/015) | Theory | More high-fidelity amplifier architecture discussion: input-stage limits, feedback depth, output current stage, and practical complexity/cost tradeoffs. |
| 18 | Medium | I. Akulinichev, "УМЗЧ для активной акустической системы и испытаний", `Радио`, 1995 №1, p.20. [archive page](https://archive.radio.ru/web/1995/01/019) | Hybrid | Small active-speaker amplifier, op-amp plus transistor output, differential-test arrangement for comparing amplifiers, useful as a measurement fixture idea. |
| 19 | Medium-low | N. Sukhov, "УМЗЧ высокой верности", `Радио`, 1989 №6, p.55. [archive page](https://archive.radio.ru/web/1989/06/056) | Hybrid | Classic high-fidelity architecture with op-amp assisted input/control, transistor output, DC offset control, speaker-wire compensation and protection. |
| 20 | Medium-low | N. Sukhov, continuation, `Радио`, 1989 №7, p.57. [archive page](https://archive.radio.ru/web/1989/07/058) | Hybrid | Continuation with construction, measurement and setup. Particularly useful for checking output power, distortion versus power, and protection behavior. |

## Most Useful Concepts For Reuse

### Discrete Transistor Signal Path

The strongest transistor-only candidates are Levitsky 1999, Khoroshev/Shadrov 1989, Akulinichev 1989, Maltsev 1994, and Vinokurov 1995. They are the best source material when the target is "no IC in the signal path". Common patterns:

- Symmetric input and voltage-gain stages reduce even-order products without needing an IC.
- Emitter degeneration and local feedback are used everywhere: input pair, voltage stage, drivers, output emitters.
- Output emitter resistors are not optional; they set current sharing, bias measurement and local linearization.
- A simple all-transistor amplifier still needs HF correction, base/gate stopping, and a load-stability network.

### Feedback Choices

The articles show three distinct schools:

- No overall OOS: accepts higher open-loop distortion but relies on local stage linearity, symmetry and soft clipping.
- Deep global OOS: can reach excellent measured distortion, but demands wide bandwidth, phase-margin discipline, careful layout and reactive-load testing.
- Parallel/local feedback: a compromise that improves linearity and output impedance while avoiding one large fragile loop.

For our work, the no-overall-feedback and parallel-feedback examples are more reusable than the Ageev/Sukhov deep-feedback hybrids, but the hybrid articles are still valuable as test and layout references.

### Output Stages

Useful output-stage ideas gathered from the 20 articles:

- Two-stage complementary emitter followers are common when supply headroom matters.
- Parallel output transistors need individual emitter resistors and thermal/current sharing checks.
- Bridge outputs are attractive for low-voltage or high-power designs, but offset, protection and symmetry become harder.
- Inductive emitter correction can reduce high-frequency/intermodulation artifacts in output devices, but the coil becomes a precision part of the bias/stability system.
- BSIT/static-induction devices appear in high-power bridge designs, but they are harder to source now than ordinary BJTs.

### Bias, Protection And Setup

Repeated practical rules:

- Set idle current only after the amplifier warms up.
- Use a current-limited first start and shorted input.
- Check output DC offset before connecting a loudspeaker.
- Protect speakers from DC and turn-on/turn-off transients.
- Test with 4 or 8 ohm dummy loads and with reactive/capacitive loads.
- For high-power parallel outputs, thermal design is part of the schematic.

### Simulation Implications

For future SPICE work:

- Do not simulate only an 8 ohm resistor. Add cable capacitance, Zobel, output inductor and a simple loudspeaker equivalent.
- Sweep quiescent current and transistor beta spread; many old articles rely on selection/matching.
- Include transistor capacitances and realistic op-amp/driver bandwidth when studying feedback-heavy circuits.
- For no-overall-feedback designs, compare harmonic spectrum and IMD, not only total THD.
- For bridge designs, verify both outputs separately and also the differential load voltage.

## Best Candidates To Reuse First

1. `1989 №9` Khoroshev/Shadrov, no overall OOS: best conceptual match to our no-global-feedback direction.
2. `1999 №10` Levitsky, inductive correction: compact, transistor main path, interesting local correction.
3. `1994 №8` Maltsev, parallel feedback: pure transistor and practical.
4. `2000 №10` Petrov, two power amps: newer and detailed transistor power-stage design.
5. `1995 №4` Vinokurov, low-voltage supply: useful for low-rail or battery-powered variants.

## Open Follow-Ups

- Extract the exact component-level netlists for the five best candidates above and simulate normalized versions.
- For each candidate, classify the feedback loops explicitly: none, local, parallel, global voltage, global current.
- Build a reusable SPICE load library: `8R`, `4R`, RLC loudspeaker equivalent, speaker cable capacitance, and reactive stress load.
- Revisit 1996-1998 issue contents for more pure transistor designs if a larger article corpus is needed.
