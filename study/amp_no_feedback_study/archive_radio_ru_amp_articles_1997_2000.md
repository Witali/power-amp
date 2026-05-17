# Archive.radio.ru Amplifier Articles, 1997-2000

Источник: официальные сканы журнала `Радио` на `archive.radio.ru`. Этот файл объединяет локально прочитанные материалы по усилителям за 1997, 1998, 1999 и 2000 годы. Я начинал с декабрьских оглавлений, затем скачивал и распознавал страницы статей, отдавая больший вес новым материалам и схемам на дискретных транзисторах.

Примечание об авторском праве: ниже только библиографические ссылки и технические конспекты. Тексты статей и сканы здесь не воспроизводятся.

## Local Evidence

- 1997-1998 annual contents and article OCR: `.tmp/radio_ru_1997_1998/`
- 1999-2000 first pass: `.tmp/latest_available_two_years/`
- 1999-2000 corrected page-offset pass: `.tmp/radio_ru_1997_2000/`
- Earlier two-year report: `study/amp_no_feedback_study/archive_radio_ru_amp_articles_1997_1998.md`
- Earlier 1999-2000 report: `study/amp_no_feedback_study/archive_radio_ru_latest_available_amp_articles_1999_2000.md`

Primary archive entry points:

- https://archive.radio.ru/web/1997/
- https://archive.radio.ru/web/1998/
- https://archive.radio.ru/web/1999/
- https://archive.radio.ru/web/2000/

## OCR And Column Audit

December annual contents pages are mostly two-column pages. For 1997-1998, automatic column detection missed the first contents pages for both years, so those pages were reprocessed with forced two-column OCR. For the selected article pages in 1997-2000 I used fixed two-column OCR (`columns2`, `psm 4`, `prose` profile) when the page layout was a normal magazine text page.

The forced two-column pass reported `LongLines = 0` on all key amplifier pages used in the notes below. That does not make OCR perfect, but it is a useful check that text from adjacent columns was not glued into long unreadable lines. A few neighboring pages turned out to be advertisements, battery articles, equalizer articles, or mostly schematic/table pages; they were used only to confirm article boundaries.

Important correction from this pass: the annual contents page number for N. Rekunov's bridge BSIT amplifier led to the wrong scan if used directly. The actual readable article start in the high-quality scan set is `b.2000-09.011`, not the initially guessed December page range.

## Ranked Articles Read

| Priority | Article | Source | Type | Reusable ideas |
|---:|---|---|---|---|
| 1 | S. Ageev, "Сверхлинейный УМЗЧ с глубокой ООС" | `Радио`, 1999 No. 10-12, continuations/follow-up through 2000. OCR pages include `b.1999-10.014` to `b.1999-10.016`, `b.1999-11.012` to `b.1999-11.014`, `b.1999-12.015` to `b.1999-12.017`, `b.2000-04.039`, `b.2000-04.040`, `b.2000-09.039`. [scan start](https://archive.radio.ru/web/img/1999/b.1999-10.014.jpg) | Hybrid: op-amps plus large discrete BJT power stage | Good high-performance benchmark: very deep/wide feedback, soft limiting, distortion indication, complex load behavior, heavy output stage, protection, separate supply/protection thinking, and PCB/layout discipline. Lower priority for a pure no-IC target, but very useful for measurement discipline and output-stage construction. |
| 2 | A. Pyatrov, "Два усилителя мощности ЗЧ" | `Радио`, 2000 No. 10, p.14. OCR pages: `b.2000-10.014`, `b.2000-10.015`. [scan start](https://archive.radio.ru/web/img/2000/b.2000-10.014.jpg) | Discrete/BSIT power amplifiers | Strong conceptual source for amplifier-load interaction. The article separates low-output-resistance amplification for LF from high-output-resistance/current-output behavior for MF/HF, uses two feedback paths including a DC integrator, and discusses softer overload behavior. Useful for simulations with realistic speaker impedance instead of only an 8 ohm resistor. |
| 3 | N. Rekunov, "Мостовой УМЗЧ с БСИТ" | `Радио`, 2000 No. 9. OCR pages: `b.2000-09.011`, `b.2000-09.012`. [scan start](https://archive.radio.ru/web/img/2000/b.2000-09.011.jpg) | Discrete/BSIT bridge amplifier | A practical bridge amplifier around BSIT output devices. Reusable ideas: bridge topology with load between two anti-phase outputs, separate gain setting in the two halves, class-AB current amplifier stages, setup by equalizing output swing, thermal/heatsink requirements, and the option to scale power by changing the number of output devices. |
| 4 | S. Sakevich, "Простой эстрадный усилитель мощности" | `Радио`, 2000 No. 11 and continuation in No. 12. OCR pages: `b.2000-11.011` to `b.2000-11.013`, `b.2000-12.037`. [scan start](https://archive.radio.ru/web/img/2000/b.2000-11.011.jpg) | Practical two-channel PA power amplifier | Useful as a robust amplifier example: input filtering, op-amp front end, voltage-to-current conversion, nearly symmetric current amplification, many paralleled output transistors, short-circuit protection, switchable damping/output resistance, and optional bias/idle-current improvements for lower HF distortion. |
| 5 | A. Orlov, "УМЗЧ с однокаскадным усилением напряжения" | `Радио`, 1997 No. 12, p.14. OCR pages: `b.1997-12.015`, `b.1997-12.016`. [scan start](https://archive.radio.ru/web/img/1997/b.1997-12.015.jpg) | Discrete/hybrid transistor UMZCH | One-stage voltage amplification as an alternative to common two- and three-stage VAS structures. Useful for high open-loop linearity goals, current sources, current mirrors, cascode-like thinking, wideband feedback, high slew-rate targets, and output-stage setup. |
| 6 | V. Levitsky, "УМЗЧ с индуктивной коррекцией" | `Радио`, 1999 No. 10, p.18. OCR pages: `b.1999-10.017`, `b.1999-10.018`. [scan start](https://archive.radio.ru/web/img/1999/b.1999-10.017.jpg) | Mostly discrete transistor UMZCH | Practical local-correction amplifier. Reusable setup notes include adjusting small-signal stage currents, minimizing output offset, checking driver/output idle current, handling thermal behavior, and optionally replacing the input section with an op-amp version. |
| 7 | V. Orlov, "Каскодная схема ОИ-ОБ в усилителе мощности ЗЧ" | `Радио`, 1997 No. 4, p.17. OCR page: `b.1997-04.018`. [scan](https://archive.radio.ru/web/img/1997/b.1997-04.018.jpg) | Discrete transistor UMZCH with cascode input | Cascode/common-base input ideas for reducing Miller modulation and improving input-stage linearity. Worth comparing against simpler BJT differential inputs in SPICE. |
| 8 | A. Syritso, "Критерии выбора УМЗЧ на биполярных транзисторах" | `Радио`, 1997 No. 8, p.14. OCR pages: `b.1997-08.015`, `b.1997-08.016`. [scan start](https://archive.radio.ru/web/img/1997/b.1997-08.015.jpg) | Theory, BJT amplifier evaluation | A measurement checklist rather than a schematic: compare distortion versus power and frequency, IMD, phase behavior, slew rate, current reserve, output-stage topology, thermal/protection behavior, and the stated load/supply conditions. |
| 9 | M. Sapozhnikov, "УМЗЧ с однополярным источником питания" | `Радио`, 1999 No. 6. OCR pages: `b.1999-06.015`, `b.1999-06.016`. [scan start](https://archive.radio.ru/web/img/1999/b.1999-06.015.jpg) | Single-supply transistor audio amplifier | Useful for single-rail biasing, midpoint/output setup, bridge/shared low-frequency channel ideas, buffer stages for high input impedance, startup checks, and practical replacement of output transistors. |
| 10 | O. Russi, "УМЗЧ с обратной связью по вычитанию искажений" | `Радио`, 1997 No. 3, p.12. OCR pages: `b.1997-03.014`, `b.1997-03.015`. [scan start](https://archive.radio.ru/web/img/1997/b.1997-03.014.jpg) | Hybrid, discrete output with auxiliary error path | Distortion-subtraction feedback is a useful comparison topology. It reduces the signal handled by the auxiliary correction path, but requires careful balance, HF correction and load-stability checks. |
| 11 | A. Kiselev, "Питание УМЗЧ с широкополосной ООС" | `Радио`, 1997 No. 2, p.15. OCR page: `b.1997-02.016`. [scan](https://archive.radio.ru/web/img/1997/b.1997-02.016.jpg) | Power and bias adaptation | Useful warning: changing the supply/reference arrangement of a wideband feedback amplifier can strongly affect output DC and idle current. Bias references should track the correct node. |
| 12 | N. Boyko, "Разделительные LC-фильтры в многополосных УМЗЧ" | `Радио`, 1999 No. 8, p.30. OCR pages: `b.1999-08.030`, `b.1999-08.031`. [scan start](https://archive.radio.ru/web/img/1999/b.1999-08.030.jpg) | Multiway amplifier filters | Not a power stage, but relevant for multi-amplifier systems. LC crossover filters need the amplifier/input impedance and coil losses included in the design; otherwise the real slope differs from the ideal. |
| 13 | S. Ageev, "Должен ли УМЗЧ иметь малое выходное сопротивление?" | `Радио`, 1997 No. 4, p.14. OCR pages: `b.1997-04.016`, `b.1997-04.017`. [scan start](https://archive.radio.ru/web/img/1997/b.1997-04.016.jpg) | Theory: amplifier-load interaction | Important for realistic load models. The loudspeaker is not just resistance; motor behavior, resonance and cable/reactive effects can make output resistance part of the acoustic result. |
| 14 | A. Sirazetdinov, "Устройство мягкого включения УМЗЧ" | `Радио`, 2000 No. 9. OCR page: `b.2000-09.014`. [scan](https://archive.radio.ru/web/img/2000/b.2000-09.014.jpg) | Support/protection | Not an amplifier topology, but useful around large transformer supplies: smooth mains turn-on protects both the amplifier and the power supply from inrush/impulse stress. |
| 15 | A. Kolganov, "Импульсный блок питания мощного УМЗЧ" | `Радио`, 2000 No. 2, p.36. OCR pages: `b.2000-02.036`, `b.2000-02.037`. [scan start](https://archive.radio.ru/web/img/2000/b.2000-02.036.jpg) | SMPS for power amplifier | Useful system-level material for high-power audio: switching supply topology, drive timing, overload behavior, output filtering and practical protection. |
| 16 | "Доработка УМЗЧ с нестандартным включением ОУ" | `Радио`, 2000 No. 8. OCR page: `b.2000-08.016`. [scan](https://archive.radio.ru/web/img/2000/b.2000-08.016.jpg) | Modification/hybrid | Useful as a cautionary follow-up around low idle current, subjective transparency and stability of a nonstandard op-amp-connected amplifier. |
| 17 | E. Karnaukhov, "Усилители мощности звуковой частоты" | `Радио`, 1999 No. 6. OCR pages: `b.1999-06.017`, `b.1999-06.018`. [scan start](https://archive.radio.ru/web/img/1999/b.1999-06.017.jpg) | General overview | Historical benchmark and specifications overview. Lower priority because it is broad survey material rather than a new topology. |
| 18 | 1998 preamp, automotive IC, modification and survey articles | Examples: `b.1998-08.019` to `b.1998-08.022`, `b.1998-10.020` to `b.1998-10.022`, `b.1998-12.018`. [1998 archive](https://archive.radio.ru/web/1998/) | Peripheral or IC-heavy | Useful for tone-control, car-audio and protection context, but low priority for pure transistor UMZCH design. |

## Engineering Takeaways

1. The strongest pure/discrete directions in these four years are not the IC-heavy articles, but the BSIT/discrete designs by Rekunov and Pyatrov, the local-correction Levitsky amplifier, and the 1997 Orlov high-performance topology.
2. From 1999-2000 the dominant theme is not simply nominal THD; authors repeatedly discuss loop bandwidth, overload recovery, output-stage current behavior, loudspeaker interaction and construction/layout.
3. A purely resistive `8 ohm` load is inadequate for comparing these ideas. At minimum, simulations should include a speaker-like impedance curve, cable capacitance, output inductor/Zobel behavior and power versus distortion plots.
4. Several articles imply that output impedance can be a design variable, not only a defect. For multiway systems, low output impedance may be best for LF while current-output or higher output resistance can be interesting for MF/HF.
5. Single-supply and bridge amplifiers need special care around midpoint bias, output DC, startup transient and protection. The Sapozhnikov and Rekunov articles are useful references for those issues.
6. High-performance hybrid designs can still teach useful discrete lessons: local feedback, emitter/source ballast, bias thermal tracking, soft clipping, current limiting, and layout of high-current loops.
7. For our transistor-focused project, the best next SPICE candidates are Rekunov 2000 bridge BSIT, Pyatrov 2000 dual amplifier, Levitsky 1999 inductive correction, Orlov 1997 one-stage voltage amplifier, and Orlov 1997 cascode-input amplifier.

## Follow-Ups

- If the next goal is a pure BJT amplifier, translate the BSIT-based output-stage ideas cautiously rather than copying device behavior directly.
- Add a realistic loudspeaker load model before ranking topologies by THD or output power.
- Keep the two-column OCR workflow as the default for `archive.radio.ru` article pages; use auto-column detection only as a candidate, then audit `LongLines` and title continuity.
