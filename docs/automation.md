# Automation

This project should keep repeatable work in scripts instead of relying on the current chat context. Use [scripts/project_tasks.py](../scripts/project_tasks.py) as the main entry point for local maintenance.

## Common Commands

```powershell
npm run symbols
npm test
npm run check
npm run spellcheck
npm run build
```

- `npm run symbols`: regenerates `part_symbols`, renders PNG previews, and runs the SVG linter with warnings treated as failures.
- `npm test`: runs the Python unit tests for project scripts.
- `npm run check`: runs tests, the SVG linter, and `git diff --check`.
- `npm run spellcheck`: checks OCR text under `_tmp_radio_ru` with Hunspell when available, otherwise with OCR-focused heuristics.
- `npm run build`: runs the symbols workflow and then project checks.

## Direct Python Commands

```powershell
python scripts\project_tasks.py symbols --force-png
python scripts\project_tasks.py test
python scripts\project_tasks.py render part_symbols results\003_radiostorage_shema_1804_6 --force-png
python scripts\project_tasks.py result results\003_radiostorage_shema_1804_6\variants\bootstrap.py
python scripts\project_tasks.py spellcheck _tmp_radio_ru --out _tmp_radio_ru\spellcheck_report.tsv
python scripts\lint_svg.py --fail-on-warning
```

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
npm run spellcheck
npm run build
```

- `npm run symbols`: пересоздает `part_symbols`, рендерит PNG-превью и запускает SVG-линтер с ошибкой на предупреждениях.
- `npm test`: запускает Python unit-тесты для проектных скриптов.
- `npm run check`: запускает тесты, SVG-линтер и `git diff --check`.
- `npm run spellcheck`: проверяет OCR-текст в `_tmp_radio_ru`, используя Hunspell при наличии или OCR-эвристики без внешних зависимостей.
- `npm run build`: выполняет workflow символов и затем проверки проекта.

## Прямые Python-Команды

```powershell
python scripts\project_tasks.py symbols --force-png
python scripts\project_tasks.py test
python scripts\project_tasks.py render part_symbols results\003_radiostorage_shema_1804_6 --force-png
python scripts\project_tasks.py result results\003_radiostorage_shema_1804_6\variants\bootstrap.py
python scripts\project_tasks.py spellcheck _tmp_radio_ru --out _tmp_radio_ru\spellcheck_report.tsv
python scripts\lint_svg.py --fail-on-warning
```

## Правила На Будущее

- Для любого повторяемого действия добавлять скрипт, прежде чем полагаться на память или инструкции из чата.
- Для workflow из нескольких шагов предпочитать подкоманды `scripts/project_tasks.py`.
- Одноцелевые helper-скрипты держать маленькими, как `scripts/lint_svg.py` и `scripts/render_svg_tree.py`.
- При изменении поведения скриптов добавлять или обновлять unit-тесты в `tests/`.
- Сгенерированные артефакты должны воспроизводиться из файлов, сохраненных в репозитории.
- Перед коммитом SVG или документации запускать `npm run check`.
