# Archive.radio.ru Latest Available Amplifier Articles, 1999-2000

`archive.radio.ru/web/` currently exposes magazine years through 2000, so the latest two available years on that site are 1999 and 2000. This note summarizes amplifier-related articles found from the December annual contents pages and a local OCR pass over selected article pages.

## Local Evidence

- Annual contents OCR: `_tmp_radio_ru/latest_available_two_years/hits.tsv`
- Annual contents report: `_tmp_radio_ru/latest_available_two_years/hits.md`
- Downloaded article scans: `_tmp_radio_ru/latest_available_two_years/article_pages/`
- Column OCR of selected articles: `_tmp_radio_ru/latest_available_two_years/article_ocr/`

Primary archive entry points:

- https://archive.radio.ru/web/
- https://archive.radio.ru/web/1999/
- https://archive.radio.ru/web/2000/
- https://archive.radio.ru/web/1999/12/
- https://archive.radio.ru/web/2000/12/

## High-Priority Articles

| Priority | Article | Source | Type | Why it matters |
|---:|---|---|---|---|
| 1 | S. Ageev, "Сверхлинейный УМЗЧ с глубокой ООС" | 1999 No. 10 p.15; continuations noted in 1999 No. 11 p.13 and No. 12 p.16; follow-up in 2000 No. 9 p.39 | Hybrid: op-amps plus discrete power stage | Very ambitious wideband feedback design. OCR confirms loop bandwidth around several MHz, very deep OOS in the audio band, full-power bandwidth above hundreds of kHz, soft limiting and distortion indication. Useful as a high-performance reference, but not a pure transistor design. |
| 2 | V. Levitsky, "УМЗЧ с индуктивной коррекцией" | 1999 No. 10 p.18 | Mostly discrete power amplifier | Practical construction notes include output-stage idle-current setup, separate rectifiers per channel, large reservoir capacitance, and an optional op-amp input alternative. Worth studying for local correction and output-stage behavior. |
| 3 | A. Pyatrov, "Два усилителя мощности ЗЧ" | 2000 No. 10 p.14 | Discrete / BSIT output | Strongest conceptual article from 2000. It explicitly discusses interaction between amplifier output impedance and loudspeaker impedance, separate low-frequency and mid/high-frequency amplification, two feedback loops, DC servo/integrator, BSIT current stage, local OOS, soft overload behavior, and dual-mono supplies. |
| 4 | N. Rekunov, "Мостовой УМЗЧ с БСИТ" | 2000 No. 12 p.12 per annual contents | Discrete / BSIT bridge amplifier | Likely important for bridge topology and transistor output stages. Needs a corrected page-offset OCR pass because the initial direct scan at `b.2000-12.012.jpg` was an acoustic-system page, not the article start. |
| 5 | S. Sakevich, "Простой эстрадный усилитель мощности" | 2000 No. 11 p.12 per annual contents | PA / practical power amp | Promising practical high-power article, but the first guessed scan was an equalizer article; needs page-offset verification before extracting topology. |
| 6 | A. Levashov, "УМЗЧ для автомобильной аппаратуры" | 2000 No. 8 p.14 | Car audio amplifier | Relevant for low-voltage supply constraints and automotive load/power goals. Needs a second OCR pass over neighboring pages for full schematic extraction. |

## Other Useful Articles

| Article | Source | Type | Notes |
|---|---|---|---|
| M. Sapozhnikov, "УМЗЧ с однополярным источником питания" | 1999 No. 6 p.16 | Single-supply audio power amplifier | OCR shows tuning around half supply, buffer stages and output power around tens of watts. Useful for single-rail biasing and setup procedures. |
| E. Karnaukhov, "Усилители мощности звуковой частоты" | 1999 No. 6 p.18 | General AF power amplifiers | Candidate for theory/background; page OCR was weaker and should be rerun with better column settings. |
| N. Boyko, "Разделительные LC-фильтры в многополосных УМЗЧ" | 1999 No. 8 p.30 | Multiway amplifier filters | Not a power stage, but important for active/multiband systems. Discusses LC split filters and coil construction constraints. |
| A. Syritso, "УМЗЧ на микросхеме TDA7294" | 2000 No. 9 p.19 | IC amplifier | Useful as an IC baseline, but lower priority for transistor-only work. |
| M. Sirazetdinov, "Устройство мягкого включения УМЗЧ" | 2000 No. 9 p.16 | Support/protection | Power sequencing and speaker/load safety; not an amplifier topology. |
| A. Kolganov, "Импульсный блок питания мощного УМЗЧ" | 2000 No. 2 p.36 | SMPS for audio amp | OCR confirms push-pull switching supply, gate-drive timing, reduced ripple with bridge rectifiers, and transistor substitution notes. Useful for complete amplifier system design. |
| "Доработка УМЗЧ с нестандартным включением ОУ" | 2000 No. 8 p.17 | Follow-up/modification | Needs article-level OCR, but likely useful for op-amp feedback topology caveats. |
| "О взаимодействии УМЗЧ с нагрузкой" | 2000 contents line, page uncertain | Theory | The Pyatrov/BSIT article itself contains this theme heavily; this may be a separate title or OCR/column merge around the same section. |

## Technical Takeaways

1. The late `archive.radio.ru` amplifier material is very feedback-conscious: authors repeatedly focus on OOS depth, bandwidth before feedback, overload recovery, and distortion spectrum rather than only nominal THD.
2. The most interesting transistor path is not simply "more gain"; it is output-stage control: local OOS, emitter/source ballast, bias thermal stabilization, and controlled overload.
3. Several articles treat the loudspeaker as an active part of the system. Pyatrov's article is especially explicit: low output impedance is not automatically ideal for every band of a multiway speaker.
4. High-performance designs often combine a precision/fast voltage stage with a discrete current stage. For our preference toward pure transistor designs, those articles should be mined for output-stage and compensation ideas while replacing IC voltage stages where possible.
5. Practical construction details matter: separate rectifiers per channel, dual-mono power supplies, large reservoir capacitors, soft start, DC protection, and safe speaker relay logic appear alongside the amplifier circuits.
6. For simulation candidates, the best next targets are Pyatrov 2000 No. 10 p.14, Levitsky 1999 No. 10 p.18, and the verified pages of Rekunov's 2000 No. 12 bridge BSIT amplifier.

## OCR Notes

The December contents pages were OCRed from high-quality `b.*.jpg` scans. Article pages were downloaded directly as `b.YYYY-MM.PPP.jpg` and processed by the column OCR script with `-AutoColumns -AutoOnly -PsmModes 6 -OcrProfiles prose`.

Important caveat: archive scan numbers can differ from printed page numbers by about two pages in some issues. For the exact article start, verify the sidebar printed page number in the scan before relying on a direct `PPP` page number from the annual contents.
