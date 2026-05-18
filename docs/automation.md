# Automation

This project should keep repeatable work in scripts instead of relying on the current chat context. Use [scripts/project_tasks.py](../scripts/project_tasks.py) as the main entry point for local maintenance.

## Common Commands

```powershell
npm run symbols
npm test
npm run check
npm run layout:frequency -- --image .tmp\layout_candidate_pages\b.2000-09.011.jpg
npm run layout:calibrate -- --images-dir .tmp\layout_candidate_pages --layouts-dir .tmp\layout_frequency_calibration_layouts
npm run spellcheck
npm run build
```

- `npm run symbols`: regenerates `part_symbols`, renders PNG previews, and runs the SVG linter with warnings treated as failures.
- `npm test`: runs the Python unit tests for project scripts.
- `npm run check`: runs tests, the SVG linter, and `git diff --check`.
- `npm run layout:frequency -- --image ...`: generates FFT/autocorrelation-style page layout hints, JSON, and PNG preview.
- `npm run layout:calibrate -- --images-dir ... --layouts-dir ...`: measures frequency features on reviewed page blocks and refreshes `study/layout_frequency_calibration.md`.
- `npm run spellcheck`: checks OCR text under `.tmp` with Hunspell when available, otherwise with OCR-focused heuristics.
- `npm run build`: runs the symbols workflow and then project checks.

Run `.\init.ps1 -InstallHunspell` to install the optional local Hunspell backend and `ru_RU`/`en_US` dictionaries under `local_tools/`.

## Direct Python Commands

```powershell
python scripts\project_tasks.py symbols --force-png
python scripts\project_tasks.py test
python scripts\project_tasks.py render part_symbols results\003_radiostorage_shema_1804_6 --force-png
python scripts\project_tasks.py result results\003_radiostorage_shema_1804_6\variants\bootstrap.py
python scripts\project_tasks.py spellcheck .tmp --out .tmp\spellcheck_report.tsv
python scripts\lint_svg.py --fail-on-warning
python scripts\analyze_page_frequency.py --image .tmp\layout_candidate_pages\b.2000-09.011.jpg --layout .tmp\layout_frequency_integrated_check\b.2000-09.011\layout.json
python scripts\project_tasks.py layout-calibrate --images-dir .tmp\layout_candidate_pages --layouts-dir .tmp\layout_frequency_calibration_layouts
python scripts\benchmark_layout_detector.py .tmp\layout_candidate_pages\b.2000-02.036.jpg .tmp\layout_candidate_pages\b.2000-10.014.jpg
```

The layout detector supports `--accelerator cpu` and `--accelerator opencl`. CPU remains the default because the local benchmark on 2026-05-18 was faster overall than OpenCL on the cached magazine pages.
The layout detector also supports `--frequency-hints off|validate|hints`. The default `validate` mode keeps OpenCV geometry unchanged and records frequency-based hints and mismatch warnings in `layout.json`; `hints` is an experimental mode that adds conservative line-art hints as extra candidate boxes.

## Rules For Future Work

- Add a script for any repeated action before relying on memory or chat instructions.
- Prefer `scripts/project_tasks.py` subcommands for workflows that combine several steps.
- Keep single-purpose helpers small, like `scripts/lint_svg.py` and `scripts/render_svg_tree.py`.
- Add or update unit tests in `tests/` when changing script behavior.
- Make generated artifacts reproducible from files committed to the repository.
- Run `npm run check` before committing generated SVG or documentation changes.

# Автоматизация

Повторяемые действия в этом проекте нужно переносить в скрипты, а не держать в текущем контексте чата. Главная точка входа для локального обслуживания проекта: [scripts/project_tasks.py](../scripts/project_tasks.py).

## Основные Команды

```powershell
npm run symbols
npm test
npm run check
npm run layout:frequency -- --image .tmp\layout_candidate_pages\b.2000-09.011.jpg
npm run layout:calibrate -- --images-dir .tmp\layout_candidate_pages --layouts-dir .tmp\layout_frequency_calibration_layouts
npm run spellcheck
npm run build
```

- `npm run symbols`: пересоздает `part_symbols`, рендерит PNG-превью и запускает SVG-линтер с ошибкой на предупреждениях.
- `npm test`: запускает Python unit-тесты для проектных скриптов.
- `npm run check`: запускает тесты, SVG-линтер и `git diff --check`.
- `npm run layout:frequency -- --image ...`: создает частотные подсказки макета страницы, JSON и PNG-превью.
- `npm run layout:calibrate -- --images-dir ... --layouts-dir ...`: измеряет частотные признаки на проверенных блоках страниц и обновляет `study/layout_frequency_calibration.md`.
- `npm run spellcheck`: проверяет OCR-текст в `.tmp`, используя Hunspell при наличии или OCR-эвристики без внешних зависимостей.
- `npm run build`: выполняет workflow символов и затем проверки проекта.

Для установки локального Hunspell backend и словарей `ru_RU`/`en_US` в `local_tools/` запустите `.\init.ps1 -InstallHunspell`.

## Прямые Python-Команды

```powershell
python scripts\project_tasks.py symbols --force-png
python scripts\project_tasks.py test
python scripts\project_tasks.py render part_symbols results\003_radiostorage_shema_1804_6 --force-png
python scripts\project_tasks.py result results\003_radiostorage_shema_1804_6\variants\bootstrap.py
python scripts\project_tasks.py spellcheck .tmp --out .tmp\spellcheck_report.tsv
python scripts\lint_svg.py --fail-on-warning
python scripts\analyze_page_frequency.py --image .tmp\layout_candidate_pages\b.2000-09.011.jpg --layout .tmp\layout_frequency_integrated_check\b.2000-09.011\layout.json
python scripts\project_tasks.py layout-calibrate --images-dir .tmp\layout_candidate_pages --layouts-dir .tmp\layout_frequency_calibration_layouts
python scripts\benchmark_layout_detector.py .tmp\layout_candidate_pages\b.2000-02.036.jpg .tmp\layout_candidate_pages\b.2000-10.014.jpg
```

Детектор макета поддерживает `--accelerator cpu` и `--accelerator opencl`. CPU остается режимом по умолчанию, потому что локальный benchmark от 2026-05-18 на сохраненных страницах журнала оказался быстрее OpenCL.
Детектор макета также поддерживает `--frequency-hints off|validate|hints`. По умолчанию используется `validate`: геометрия OpenCV не меняется, а частотные подсказки и предупреждения о несовпадениях записываются в `layout.json`; режим `hints` экспериментально добавляет осторожные line-art подсказки как дополнительные блоки-кандидаты.

## Правила На Будущее

- Для любого повторяемого действия добавлять скрипт, прежде чем полагаться на память или инструкции из чата.
- Для workflow из нескольких шагов предпочитать подкоманды `scripts/project_tasks.py`.
- Одноцелевые helper-скрипты держать маленькими, как `scripts/lint_svg.py` и `scripts/render_svg_tree.py`.
- При изменении поведения скриптов добавлять или обновлять unit-тесты в `tests/`.
- Сгенерированные артефакты должны воспроизводиться из файлов, сохраненных в репозитории.
- Перед коммитом SVG или документации запускать `npm run check`.
