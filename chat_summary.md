# Power Amp Project Context

Last updated: 2026-05-16.

This repository is a working notebook and generator/simulation workspace for audio power amplifier schematics, mostly transistor-based designs, with Codex helping to research, redraw, simulate, document, and publish results.

## How To Continue Later

Start by reading this file, then:

- `AGENTS.md` for project-specific working rules.
- `README.md` for the public project description and generated result links.
- `amp_no_feedback_study/radio_ru_bjt_amplifier_knowledge.md` for distilled Radio magazine amplifier knowledge.
- `amp_no_feedback_study/archive_radio_ru_umzch_20_article_study.md` for the newest OCR-backed archive.radio.ru study of 20 UMZCH publications.
- `results/001_rogov_triple_ef_amplifier/README.md` for the current first full schematic/result package.

## Project Rules Already Established

- Work in Russian by default unless the user asks otherwise.
- Ordinary non-destructive local commands in this project can be run without asking.
- Do not revert user changes.
- Save meaningful progress to git periodically; `AGENTS.md` says to check after every fifth user prompt.
- Temporary OCR/downloaded magazine scans stay under `_tmp_radio_ru/`, which is ignored by git.
- Do not store copyrighted scans as permanent project knowledge; store links and distilled notes only.

## Current Main Result

The active schematic/result package is:

- `results/001_rogov_triple_ef_amplifier/`

It contains the first Rogov-style amplifier schematic and generated outputs:

- `schematic/rogov_triple_ef_amplifier.svg`
- `schematic/rogov_triple_ef_amplifier.png`
- `source/generate_radio_ru_5_study.py`
- `README.md`

Recent fixes there:

- Added/kept the official source pointer to I. Rogov, "Выходной каскад УМЗЧ - две или три ступени повторителя?", `Радио`, 2018 №12, p.27.
- Fixed several floating transistor-base connections in the generated schematic.
- The schematic drawing rules should avoid part/wire/text overlaps, avoid unnecessary bends, prefer horizontal/vertical wiring, and show junction dots only where three or more conductors meet.

## Radio.ru Research State

I studied and saved a new archive-focused knowledge pass:

- `amp_no_feedback_study/archive_radio_ru_umzch_20_article_study.md`

Method:

- Used official `archive.radio.ru` scans and issue contents pages.
- Started with newer archive years and moved backward.
- Preferred transistor-only or transistor-dominant UMZCH articles over IC-only articles.
- Used local Tesseract OCR with Russian and English models.

Best reusable candidates from that pass:

1. `1989 №9` - Khoroshev/Shadrov, "УМЗЧ без общей ООС".
2. `1999 №10` - Levitsky, "УМЗЧ с индуктивной коррекцией".
3. `1994 №8` - Maltsev, "УМЗЧ с параллельной обратной связью".
4. `2000 №10` - Petrov, "Два усилителя мощности ЗЧ".
5. `1995 №4` - Vinokurov, "УМЗЧ с питанием от низковольтного источника".

Related older knowledge:

- `amp_no_feedback_study/radio_ru_bjt_amplifier_knowledge.md`
- `amp_no_feedback_study/musicforums_amplifier_distortion_notes.md`
- `amp_no_feedback_study/best_practices.md`

## Design Direction

For the no-overall-feedback study, the favored conceptual architecture remains:

```text
input pair or buffer
  -> low-voltage folded/cascoded transistor voltage amplifier
  -> thermally tracked Class AB bias network
  -> CFP/Sziklai or double complementary emitter-follower output
  -> output relay, Zobel, output inductor, and protection
```

Important constraints from earlier work:

- Class AB.
- Low rails are important; `+15 V / 0 / -15 V` was used in the no-global-feedback comparison.
- Load target was typically `8 ohm`.
- Avoid any overall/global `OUT` to input/VAS feedback path when the goal is explicitly no-global-feedback.
- Local feedback and linearization are allowed: emitter degeneration, CFP/Sziklai action, emitter resistors, base stoppers, current sources, and local compensation.

## Tools Already Present

- Local Tesseract OCR:
  - `local_tools/Tesseract-extracted/tesseract.exe`
  - Russian language data exists in `local_tools/Tesseract-extracted/tessdata/rus.traineddata`
  - Helper script: `ocr_tools/ocr_image.ps1`
- Local ngspice exists under:
  - `local_tools/ngspice/Spice64/`
- Node tooling is present for SVG/PNG generation:
  - `tools/render_svg_png.js`
- Generated project docs are under:
  - `docs/`
  - `scripts/`

## Current Git State Reminder

At the time this context was saved, there were meaningful uncommitted changes from recent schematic fixes, Radio/MusicForums research notes, and this context update. Before starting a new larger task, run:

```powershell
git status --short
```

Then decide whether to commit the current progress before making unrelated changes.

## Good Next Steps

- Commit the current research/context/schematic progress when ready.
- Extract normalized SPICE netlists for the top archive.radio.ru transistor-only candidates.
- Simulate each candidate with `8R`, `4R`, speaker-cable capacitance, Zobel, output inductor, and a simple RLC loudspeaker equivalent.
- Compare gain, clipping, THD spectrum, IMD, output power, square-wave response, and stability with capacitive loads.
- Keep generated result packages under `results/NNN_short_name/` with PNG schematic, plots, simulation files, and a local README.
