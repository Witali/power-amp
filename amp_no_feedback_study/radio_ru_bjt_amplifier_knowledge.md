# Radio.ru BJT Amplifier Knowledge Notes

Source focus: Russian `Радио` magazine material, with official `radio.ru`, `ftp.radio.ru`, and `archive.radio.ru` pages preferred over mirrors. Newer items are ranked first, and pure bipolar/discrete transistor amplifier material is ranked higher than IC, tube, MOSFET, or mixed/hybrid material.

Copyright note: these are distilled engineering notes and source pointers, not article copies.

## Source Ranking

Scoring bias used here:

- Official Radio sources first: use `radio.ru`, `ftp.radio.ru`, and `archive.radio.ru` for confirmation and scans whenever available; use mirrors only as secondary leads or readable fallbacks.
- Newer publication date: higher score.
- Pure BJT or mostly discrete transistor signal/output path: higher score.
- Directly useful for audio power amplifier design: higher score.
- Articles that are mainly tube, IC-only, MOSFET-only, Class D, peripherals, or subjective listening reports: lower score.

| Rank | Source | Why It Matters | Reuse Priority |
|---:|---|---|---|
| 1 | V. Grechishkin, "Усилитель мощности на биполярных транзисторах", `Радио`, 2013 №5, p.14. Annual TOC confirms entry in [`2013.pdf`](https://ftp.radio.ru/pub/2013/12/58.pdf); readable reprint: [RadioRadar](https://www.radioradar.net/radiofan/audio_equipment/power_amplifier_using_bipolar_transistors.html). | Pure BJT/discrete power amplifier. Differential input, current-source tail, current mirror, VAS, emitter-follower buffer, 3-stage complementary output, Vbe bias transistor, output stability networks, setup and layout notes. | Very high |
| 2 | A. Syrico, "Выходной каскад УМЗЧ со стабилизацией тока покоя", `Радио`, 2017 №10, pp.7-9. Indexed by [TUSUR](https://lib.tusur.ru/irbis-new/i64r_15/cgiirbis_64.exe?C21COM=S&I21DBN=LIB&LNG=&P21DBN=LIB&S21CNR=&S21FMT=fullwebr&S21LOG=1&S21P01=0&S21P02=0&S21P03=K%3D&S21REF=&S21STN=1&S21STR=%D0%B2%D0%BE%D1%81%D0%BF%D1%80%D0%BE%D0%B8%D0%B7%D0%B2%D0%B5%D0%B4%D0%B5%D0%BD%D0%B8%D0%B5&Z21ID=) and 2018 annual TOC. | Focused on output-stage idle-current stabilization: thermal compensation, accuracy, drift control. | Very high |
| 3 | A. Syrico, "Простой драйвер для выходных каскадов УМЗЧ", `Радио`, 2017 №9, pp.13-14. Listed in 2018 annual TOC as related consultation material. | Driver-stage ideas for discrete output stages; useful when separating VAS loading from output transistor drive. | High |
| 4 | I. Rogov, "Выходной каскад УМЗЧ - две или три ступени повторителя?", `Радио`, 2018 №12, p.27. Listed in [`2018.pdf`](https://ftp.radio.ru/pub/2018/12/2018.pdf). | Directly matches a design choice: 2-stage vs 3-stage emitter-follower output. Important for low-rail headroom, drive current, crossover behavior, and thermal complexity. | High |
| 5 | A. Petrov, "УМЗЧ с токовой обратной связью", `Радио`, 2018 №6, pp.10-16. Listed in [`2018.pdf`](https://ftp.radio.ru/pub/2018/12/2018.pdf) and [TUSUR](https://lib.tusur.ru/irbis-new/i64r_15/cgiirbis_64.exe?C21COM=S&I21DBN=LIB_PRINT&LNG=&P21DBN=LIB&S21CNR=500&S21FMT=FULLW_print&S21LOG=1&S21P01=0&S21P02=0&S21P03=K%3D&S21REF=&S21STN=1&S21STR=ARDUINO&Z21ID=). | Current-feedback amplifier concepts: bandwidth, distortion, impedance interactions. Useful conceptually, but lower if the target is no global feedback. | Medium-high |
| 6 | A. Petrov, "Исследование модели УМЗЧ (цирклотрон на ОУ и транзисторах)", `Радио`, 2018 №7/8, pp.21/7; and "Усовершенствованный вариант цирклотрона", 2018 №9, p.13. Listed in [`2018.pdf`](https://ftp.radio.ru/pub/2018/12/2018.pdf) and TUSUR. | Symmetric/circlotron thinking, clipping behavior, model-based distortion study. Mixed OP-amp/transistor relevance. | Medium |
| 7 | A. Petrov, "Первый полюс в АЧХ и его влияние на параметры усилителей с общей ООС", `Радио`, 2018 №10/11. Listed in [`2018.pdf`](https://ftp.radio.ru/pub/2018/12/2018.pdf). | Feedback-loop stability and dominant-pole thinking. Useful even when avoiding global feedback, because local loops and compensation still need phase-margin discipline. | Medium |
| 8 | S. Ageev, "Сверхлинейный УМЗЧ с глубокой ООС", `Радио`, 1999 №10-12; 2000 №1,2,4-6. Article summary/reprint: [Diagram](https://www.diagram.com.ua/list/sound/sound64.shtml). Archive scans available through `archive.radio.ru` years 1999/2000. | Hybrid OP-amp plus BJT power amplifier with very deep/wide feedback, careful layout, local rectification/decoupling, protection, and measurement discipline. Lower rank because it is not pure discrete/no-feedback, but the layout and test ideas are valuable. | Medium |
| 9 | N. Sukhov, "УМЗЧ высокой верности", `Радио`, 1989 №6 pp.55-57 and №7 pp.57-61. Available in `archive.radio.ru` scans; background PDF: [radiochipi mirror](https://www.radiochipi.ru/wp-content/uploads/2015/05/usilitel-suhov.pdf). | Classic high-fidelity Soviet transistor amplifier lineage: OP-amp assisted, BJT output, compensation of speaker-wire resistance, multi-loop feedback. Historically important. | Medium-low for no-feedback work |

## Most Reusable BJT Amplifier Concepts

### Front End

- Use a differential input pair when DC stability, symmetric clipping, and predictable feedback/local reference behavior matter.
- Tail current source improves common-mode rejection and input-pair linearity compared with a plain emitter resistor.
- Current mirrors in collector loads improve gain and symmetry, but matching and thermal proximity matter.
- Input RF filtering is not optional in practical amplifiers: keep a small low-pass/high-pass input network so RF does not enter the nonlinear front end.
- For no-global-feedback designs, input-stage linearity matters more because later feedback will not correct its errors.

### Voltage Amplifier Stage

- A VAS transistor loaded by a current source or mirror gives high gain but is easy to overdrive or destabilize.
- Unload the VAS with an emitter-follower buffer or driver when the output stage presents significant variable current demand.
- Local VAS emitter degeneration is a direct trade: less gain, more predictable distortion, better thermal and part-spread tolerance.
- Cascode or common-base sections reduce Miller-capacitance modulation and auto-intermodulation, but add voltage headroom requirements.
- On low rails such as `+/-15 V`, folded cascode or lower-stack-height arrangements preserve swing better than tall cascoded stacks.

### Output Stage

- The common BJT power path is: driver emitter follower -> output emitter follower, with emitter ballast resistors.
- A third emitter-follower stage reduces required VAS/driver current and can reduce output impedance/crossover stress, but costs extra `Vbe` headroom and complicates thermal bias tracking.
- Two-stage emitter followers are often better on low supply rails.
- CFP/Sziklai pairs give strong local feedback in the output stage and can preserve headroom compared with triple emitter followers, but must be checked for HF stability and capacitive-load behavior.
- Output emitter resistors are doing several jobs: current sharing, thermal stability, bias measurement, and some local degeneration. Do not omit them.
- For parallel output transistors, give each device its own ballast resistor and verify current sharing individually.

### Bias And Thermal Stability

- Bias spread and drift dominate crossover behavior in Class AB. Treat the bias generator as a thermal/mechanical design, not just a schematic symbol.
- A Vbe multiplier or bias transistor should be thermally coupled to the power devices or their heatsink.
- Set idle current by measuring voltage across emitter resistors after warm-up; then re-check after thermal soak.
- More idle current is not automatically better: it reduces crossover artifacts but raises temperature and can reduce safety margin.
- Bias networks need RF bypassing and layout care so output-stage signal currents do not modulate the bias reference.

### Feedback And Compensation

- Global voltage feedback can deliver very low distortion and low output impedance, but it moves the problem into loop stability, compensation, PCB layout, and load interaction.
- Current feedback/topologies with current sensing can improve slew/bandwidth and alter output impedance behavior, but the source/load impedance assumptions become part of the design.
- Multi-loop designs can be excellent, but each loop needs an identified bandwidth and a clear summing point.
- For no-global-feedback work, borrow the local-feedback tools: emitter degeneration, CFP/Sziklai action, current-source linearization, cascode/common-base isolation, and emitter resistors.
- Do not expect Radio-style `0.003%` THD numbers from a no-global-feedback amplifier unless the open-loop stages are exceptionally linear and biased generously.

### Stability Networks

- Add a Zobel/snubber at the output, commonly a resistor in series with a capacitor to ground.
- Add an output inductor with damping resistor when driving capacitive speaker cables.
- Use base-stopper resistors on driver and output transistors where HF parasitic oscillation is plausible.
- Use local supply decoupling near each high-current and high-gain stage.
- Verify with square waves, capacitive loads, reactive loads, and both small and large signal levels.

### Layout And Power

- Keep high-current output and supply loops physically short.
- Route input ground, signal ground, power ground, and speaker return deliberately; join them at a controlled point.
- Twisting supply and speaker leads reduces loop area and radiated pickup.
- Use shielded input wiring and keep it away from rectifiers, transformer wiring, and output wiring.
- Linear transformer supplies are bulky but predictable and quiet; switch-mode supplies need much more EMI work.
- Large reservoir capacitors are not cosmetic: they reduce rail sag and ripple under current peaks, but inrush and rectifier stress must be handled.
- Putting rectifiers/reservoir capacitors close to the power stage can reduce parasitic supply inductance, but raises mechanical/thermal layout demands.

### Setup And Verification

- First power-up through current-limiting resistors or a current-limited supply.
- Short the input during initial DC checks.
- Check output DC offset before connecting a speaker.
- Check for HF oscillation before setting final bias.
- Set bias after warm-up, then re-check after at least 10 minutes.
- Test stability with realistic cable capacitance and reactive speaker-equivalent loads, not only a dummy resistor.
- For distortion work, measure beyond audio-band behavior too: RF instability or ringing can masquerade as subjective harshness.

## Reuse For The Current +/-15 V No-Global-Feedback Amplifier

- Prefer the newer pure-BJT source pattern of differential input, current-source biasing, current mirrors, and buffered VAS, but avoid relying on global feedback for cleanup.
- Because the rails are only `+/-15 V`, treat triple emitter followers as suspicious: they cost too much voltage swing unless the power target is modest.
- The ranked fallback output choices are:
  1. CFP/Sziklai Class AB output with careful compensation and load testing.
  2. Two-stage complementary emitter follower with generous driver current and local degeneration.
  3. Triple emitter follower only if headroom calculations still meet the power target.
- Use a Vbe multiplier/bias transistor with strong thermal coupling, output emitter resistors, Zobel, output inductor/damping resistor, and base stoppers.
- Keep no-global-feedback honest: no wire from output back to the input or VAS summing node. Local output-stage feedback inside CFP/Sziklai is acceptable if documented.
- For behavioral comparison, penalize topologies that spend extra `Vbe` drops, need high loop gain to linearize, or rely on IC op-amps as the main correction engine.

## Follow-Up Sources To Inspect If More Time Is Available

- `archive.radio.ru` 1999-2000 scans for Ageev's multi-part "Сверхлинейный УМЗЧ с глубокой ООС".
- `archive.radio.ru` 1989 №6/№7 scans for Sukhov's "УМЗЧ высокой верности".
- `Радио` 2018 №12 p.27 for the full Rogov two-stage/three-stage emitter-follower article.
- `Радио` 2017 №9/№10 for Syrico driver and idle-current stabilization articles.
- `Радио` 2018 №6 for Petrov current-feedback amplifier article.
