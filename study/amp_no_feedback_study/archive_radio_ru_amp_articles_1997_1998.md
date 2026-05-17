# Archive.radio.ru Amplifier Articles, 1997-1998

Source scope: official `archive.radio.ru` scans for `Радио` magazine, years 1998 and 1997. I used December annual contents pages first, then read selected amplifier-related article pages, preferring discrete/transistor UMZCH material over IC-only or peripheral notes.

Copyright note: this file contains distilled engineering notes and short bibliographic pointers only. It does not reproduce article text or scanned pages.

## Local Evidence

- Annual contents OCR: `.tmp/radio_ru_1997_1998/hits.tsv`
- Annual contents report: `.tmp/radio_ru_1997_1998/hits.md`
- Downloaded article scans: `.tmp/radio_ru_1997_1998/article_pages/`
- Article OCR: `.tmp/radio_ru_1997_1998/article_ocr_fixed2/`

Primary archive entry points:

- https://archive.radio.ru/web/1997/
- https://archive.radio.ru/web/1998/
- https://archive.radio.ru/web/1997/12/
- https://archive.radio.ru/web/1998/12/

## Column-Split Audit

The December contents pages are two-column pages. Automatic column detection worked on the later contents pages, but missed the split on the first contents pages for both years.

| Page scan | Auto result | Fix used |
|---|---|---|
| `b.1997-12.063.jpg` | no split detected | fixed two-column OCR |
| `b.1997-12.064.jpg` | no split detected | fixed two-column OCR |
| `b.1997-12.065.jpg` | split at `1241` px | auto two-column OCR accepted |
| `b.1997-12.066.jpg` | split at `1258` px | auto two-column OCR accepted |
| `b.1998-12.067.jpg` | no split detected | fixed two-column OCR |
| `b.1998-12.068.jpg` | no split detected | fixed two-column OCR |
| `b.1998-12.069.jpg` | split at `1063` px | auto two-column OCR accepted |
| `b.1998-12.070.jpg` | split at `1099` px | auto two-column OCR accepted |
| `b.1998-12.071.jpg` | split at `1098` px | auto two-column OCR accepted |

For the selected article pages I used fixed two-column OCR (`columns2`, `psm 4`, `prose` profile). Every processed article page reported `LongLines = 0`, so there were no obvious glued-column failures in this pass. When title searches missed an expected article, I downloaded neighboring scan pages and reran the same fixed two-column OCR.

## Ranked Articles Read

| Priority | Article | Source | Type | Reusable ideas |
|---:|---|---|---|---|
| 1 | A. Orlov, "УМЗЧ с однокаскадным усилением напряжения" | `Радио`, 1997 No. 12, p.14. OCR pages: `b.1997-12.015`, `b.1997-12.016`. [scan start](https://archive.radio.ru/web/img/1997/b.1997-12.015.jpg) | Discrete/hybrid transistor UMZCH, MOSFET input | One-stage voltage amplification as an alternative to common two- and three-stage VAS structures; very high open-loop gain target, folded-cascode-like input section, current mirrors/current sources, wideband feedback and high slew-rate goals. OCR reports nominal 50 W/8 ohm, 1.1 V input, distortion around `0.001%`, slew rate at least 200 V/us, and very low output resistance at audio frequencies. |
| 2 | V. Orlov, "Каскодная схема ОИ-ОБ в усилителе мощности ЗЧ" | `Радио`, 1997 No. 4, p.17. OCR page: `b.1997-04.018`. [scan](https://archive.radio.ru/web/img/1997/b.1997-04.018.jpg) | Discrete transistor UMZCH with FET/common-base cascode input | Symmetric input stage built as common-source/common-base cascodes, transistor drivers and a conventional output stage. Useful for reducing input-stage Miller effects and for comparing cascode front ends against simpler differential inputs. OCR also shows modest global feedback depth and explicit supply/output-stage setup notes. |
| 3 | A. Syritso, "Критерии выбора УМЗЧ на биполярных транзисторах" | `Радио`, 1997 No. 8, p.14. OCR pages: `b.1997-08.015`, `b.1997-08.016`. [scan start](https://archive.radio.ru/web/img/1997/b.1997-08.015.jpg) | Theory, BJT output-stage selection | A good checklist for choosing or designing BJT amplifiers: judge power under stated load/supply/temperature conditions, compare distortion over both power and frequency, account for IMD being several times more revealing than simple harmonic distortion, check phase response, slew rate, output-stage current reserve, protection behavior, and the effect of local feedback/output topology. |
| 4 | A. Kiselev, "Питание УМЗЧ с широкополосной ООС" | `Радио`, 1997 No. 2, p.15. OCR page: `b.1997-02.016`. [scan](https://archive.radio.ru/web/img/1997/b.1997-02.016.jpg) | Power/bias adaptation for a wideband feedback UMZCH | Shows how supply arrangement and input-stage biasing affect output-stage idle-current stability. The useful warning is that a direct supply conversion can move output DC enough to change output transistor current substantially; tying the relevant bias reference to the amplifier output and stabilizing the IC supply reduces this drift. |
| 5 | O. Russi, "УМЗЧ с обратной связью по вычитанию искажений" | `Радио`, 1997 No. 3, p.12. OCR pages: `b.1997-03.014`, `b.1997-03.015`. [nearby scan](https://archive.radio.ru/web/img/1997/b.1997-03.014.jpg) | Hybrid, discrete output with op-amp error path | Distortion-subtraction feedback (`ОСВИ`) is treated as a compromise between shallow global feedback and deep wideband OOS. The key idea is to subtract the useful signal so the auxiliary amplifier mostly handles a smaller distortion/error component; this reduces demands on op-amp slew rate but requires careful balance, HF correction, and load-stability checks. |
| 6 | M. Korzinin, "Схемотехника усилителей мощности звуковой частоты высокой верности. Мостовые УМЗЧ" | `Радио`, 1997 continuation around No. 8. OCR pages: `b.1997-08.013`, `b.1997-08.014`. [scan](https://archive.radio.ru/web/img/1997/b.1997-08.013.jpg) | Theory, bridge UMZCH/output stages | Useful for bridge amplifier reasoning: each half-amplifier and each output transistor bias path must remain controlled independently, and bridge designs trade more output voltage for tougher offset, protection, and balance requirements. Lower priority than the direct 1997 articles above because this OCR pass caught a continuation rather than a clean article start. |
| 7 | S. Ageev, "Должен ли УМЗЧ иметь малое выходное сопротивление?" | `Радио`, 1997 No. 4, p.14. OCR pages: `b.1997-04.016`, `b.1997-04.017`. [nearby scan](https://archive.radio.ru/web/img/1997/b.1997-04.016.jpg) | Theory: amplifier-load interaction | Important for simulation loads. The article argues that loudspeaker current, coil resistance/inductance, cone motion and resonance make the amplifier output resistance part of the acoustic result; very low output resistance is not the only possible design goal, especially when considering IMD around loudspeaker resonance and multiway systems. |
| 8 | M. Sapozhnikov, "УМЗЧ автомобильного радиокомплекса" | `Радио`, 1997 No. 10, p.16. OCR pages: `b.1997-10.017`, `b.1997-10.018`. [scan start](https://archive.radio.ru/web/img/1997/b.1997-10.017.jpg) | Automotive, mixed/IC-heavy | Useful mainly as system design: low-voltage car supply, 3D/low-frequency shared channel idea, filtering, turn-on behavior, and protection. Lower priority for pure transistor work because the core is not a clean discrete BJT UMZCH reference. |
| 9 | A. Zyzyuk, "Предварительный усилитель с темброблоком" | `Радио`, 1998 No. 8, p.20. OCR pages: `b.1998-08.019`, `b.1998-08.020`. [scan start](https://archive.radio.ru/web/img/1998/b.1998-08.019.jpg) | Preamp/tone control, op-amp plus FET buffers | Useful for front-end ergonomics rather than power stage design: source followers isolate the tone network, one op-amp voltage-gain stage avoids cascaded distortion buildup, and the text emphasizes stability and subjective comparison of buffer stages. |
| 10 | A. Sokolov, "Есть ли в России усилители для XXI века?" | `Радио`, 1998 No. 8, p.22. OCR pages: `b.1998-08.021`, `b.1998-08.022`. [scan start](https://archive.radio.ru/web/img/1998/b.1998-08.021.jpg) | Survey/review | Mostly market and listening context, not a schematic source. Still useful as historical context: the period had competing schools around feedback depth, tube/transistor choices, transformer coupling, class A, and subjective evaluation. |
| 11 | S. Buryak, "УМЗЧ автомобильного радиокомплекса" | `Радио`, 1998 No. 10, p.21. OCR pages: `b.1998-10.020`, `b.1998-10.021`. [scan start](https://archive.radio.ru/web/img/1998/b.1998-10.020.jpg) | Automotive IC amplifier | Low priority for transistor-only work. Useful notes: bridge IC outputs, car-supply constraints, multi-band/multi-speaker routing, power supply headroom, and protection against automotive electrical noise. |
| 12 | G. Dubrovin, "Доработка УМЗЧ 'Вега 50У-122С'" | `Радио`, 1998 No. 10, p.23. OCR page: `b.1998-10.022`. [scan](https://archive.radio.ru/web/img/1998/b.1998-10.022.jpg) | Modification/protection | Not a new amplifier topology; useful only as a practical example of protection/control modifications around an existing domestic amplifier. |
| 13 | M. Naumov, "Предусилитель с разделенной коррекцией АЧХ" | `Радио`, 1998 No. 12, p.19. OCR page: `b.1998-12.018`. [nearby scan](https://archive.radio.ru/web/img/1998/b.1998-12.018.jpg) | Preamp/equalization | Peripheral to power-amplifier work. Useful for thinking about staged correction and buffer isolation, but not a candidate for BJT power-stage reuse. |

## Engineering Takeaways

- The strongest new reusable source from this pass is Orlov 1997 No. 12: it is a serious high-performance topology discussion, with one-stage voltage gain, current-source/cascode thinking and explicit output-stage performance targets.
- The second Orlov article, 1997 No. 4, is valuable for front-end design: cascode input stages can reduce Miller-capacitance modulation and raise input-stage linearity, but they cost voltage headroom and require careful biasing.
- Syritso 1997 No. 8 is not a schematic to copy; it is a measurement discipline note. For future reports and simulations, distortion should be plotted versus both frequency and output power, with IMD and phase/slew behavior considered alongside simple THD.
- The Kiselev supply article reinforces a practical point we already saw in single-supply designs: bias references must move with the right node. A bias reference fixed to the wrong rail can turn temperature drift or DC offset into a large output-stage idle-current error.
- The Russi distortion-subtraction article is conceptually interesting but less pure: an auxiliary op-amp path subtracts distortion/error rather than making one deep global loop do all correction. This may be useful as a comparison topology, not as the first no-IC target.
- The Ageev output-resistance article argues for realistic loudspeaker simulation. Do not judge amplifier behavior only on an 8 ohm resistor; add loudspeaker impedance, resonance and cable/reactive effects when comparing output-stage choices.
- The 1998 amplifier material found in the annual contents was mostly preamp, automotive IC, modification or survey material, so 1998 adds less pure transistor UMZCH knowledge than 1997.

## Reuse Candidates

1. Build a normalized SPICE model from Orlov 1997 No. 12 as a high-performance reference, even if the final project keeps a stricter BJT-only target.
2. Extract the cascode input idea from Orlov 1997 No. 4 and compare it with a simpler differential BJT input in the same output-stage environment.
3. Add Syritso-style evaluation checks to generated plots: THD versus frequency, THD versus power, phase/slew notes, and a realistic load case.
4. Keep Kiselev's bias-reference lesson in single-supply amplifiers: when a node should track the output midpoint, simulate temperature/beta variation and verify idle current drift.

## Open Follow-Ups

- The Korzinin bridge article was read from a continuation page; if bridge UMZCH becomes a priority, revisit its clean start page.
- The 1998 automotive IC articles are intentionally left low priority unless car-audio supply/protection behavior becomes relevant.
- For a future deeper pass, continue backward to 1996 using the same method: December contents first, high-quality `b.*.jpg` scans, auto-column audit, fixed two-column OCR fallback.
