# Analog Circuit Simulation With Codex

This project is a local workspace for reconstructing, drawing, simulating, and documenting analog circuits with Codex. The current focus is on transistor audio amplifiers inspired by Russian radio articles and scanned schematics, but the structure is intentionally general enough for filters, power supplies, test circuits, and other analog blocks. Codex helps turn source images and article notes into editable SVG schematics, SPICE netlists, ngspice runs, PNG plots, and Markdown reports. Each result is kept in its own folder so the schematic, simulation data, plots, source scripts, and assumptions stay together. The project prefers reproducible local tools: ngspice for circuit simulation, generated SVG as the editable drawing source, and PNG exports for quick inspection. The drawing rules are collected in [docs/schematic_drawing_rules.md](docs/schematic_drawing_rules.md), including the local GOST/ESKD conventions used for radio-style schematics, and generated plot conventions are collected in [docs/plot_drawing_rules.md](docs/plot_drawing_rules.md). The goal is not to replace bench testing, but to make the design loop faster and better documented before hardware is built.

## Tested Circuits

| Result | What was tested | Main links |
| --- | --- | --- |
| [001 Rogov Triple EF Amplifier](results/001_rogov_triple_ef_amplifier/README.md) | BJT audio amplifier topology with a Rogov-style triple emitter-follower output stage, simulated for gain, THD, and output power. | [schematic PNG](results/001_rogov_triple_ef_amplifier/schematic/rogov_triple_ef_amplifier.png), [netlist](results/001_rogov_triple_ef_amplifier/netlists/variant_02_rogov_triple_ef.cir), [plots](results/001_rogov_triple_ef_amplifier/plots/) |
| [002 ngspice RC Low-Pass](results/002_ngspice_rc_lowpass/README.md) | Simple RC low-pass filter used to verify the local ngspice backend, AC sweep, transient run, and PNG/SVG report generation. | [schematic PNG](results/002_ngspice_rc_lowpass/schematic/rc_lowpass.png), [netlist](spice_examples/001_rc_lowpass/rc_lowpass.cir), [plots](results/002_ngspice_rc_lowpass/plots/) |
| [003 RadioStorage shema-1804-6 Bootstrap Reconstruction](results/003_radiostorage_shema_1804_6/README.md) | Single-supply BJT audio amplifier reconstructed from a RadioStorage image, with only the bootstrap/voltage-addition variant retained as the working design. | [HTML report](results/003_radiostorage_shema_1804_6/index.html), [schematic PNG](results/003_radiostorage_shema_1804_6/schematic/reconstructed_amplifier_bootstrap.png), [netlist](results/003_radiostorage_shema_1804_6/netlists/radiostorage_amp_bootstrap.cir), [plots](results/003_radiostorage_shema_1804_6/plots/) |

## Local Workflow

Generated circuit work should go into `results/NNN_short_name/`. Each result folder should keep a `README.md`, schematic images, plots, simulation data, SPICE netlists, and the source scripts needed to reproduce the artifacts. Use [scripts/generate_result_html.py](scripts/generate_result_html.py) to create a simple local HTML report when a result folder has images and a Markdown description.

Use [scripts/generate_html_from_markdown.py](scripts/generate_html_from_markdown.py) when you need a standalone HTML file from any Markdown document:

```powershell
python scripts\generate_html_from_markdown.py results\003_radiostorage_shema_1804_6\README.md --output results\003_radiostorage_shema_1804_6\report.html --title "RadioStorage shema-1804-6 Bootstrap"
```

For new circuit variants, prefer the reusable runner instead of embedding all logic in one result-local script. Put the concrete topology, component values, schematic drawing, and measurement recipe into `results/NNN_short_name/variants/name.py`; the shared SVG, ngspice, CSV, and plotting helpers live in [scripts/circuitlib](scripts/circuitlib/). A variant must expose `RESULT_DIR` and `run()`. From the repository root, run a variant like this:

```powershell
python scripts\run_circuit_result.py results\003_radiostorage_shema_1804_6\variants\bootstrap.py
```

Before committing generated SVG schematics or symbol files, run the local SVG linter:

```powershell
npm run lint:svg
```

# Симуляция аналоговых схем с помощью Codex

Этот проект является локальным рабочим пространством для восстановления, отрисовки, моделирования и документирования аналоговых схем вместе с Codex. Сейчас основной фокус сделан на транзисторных звуковых усилителях по мотивам русскоязычных радиотехнических статей и отсканированных схем, но структура проекта подходит и для фильтров, блоков питания, тестовых цепей и других аналоговых узлов. Codex помогает превращать исходные изображения и заметки из статей в редактируемые SVG-схемы, SPICE-netlist’ы, расчеты ngspice, PNG-графики и Markdown-отчеты. Каждый результат хранится в отдельной папке, чтобы схема, данные моделирования, графики, исходные скрипты и принятые допущения не разъезжались. В проекте предпочтительны воспроизводимые локальные инструменты: ngspice для моделирования, SVG как редактируемый источник рисунка и PNG для удобного просмотра. Правила отрисовки схем собраны в [docs/schematic_drawing_rules.md](docs/schematic_drawing_rules.md), включая локальные соглашения по ГОСТ/ЕСКД для радиосхем, а правила генерации графиков собраны в [docs/plot_drawing_rules.md](docs/plot_drawing_rules.md). Цель проекта не заменить проверку на макете, а ускорить и лучше задокументировать цикл проектирования до сборки железа.

## Испытанные схемы

| Результат | Что проверялось | Основные ссылки |
| --- | --- | --- |
| [001 Усилитель Rogov Triple EF](results/001_rogov_triple_ef_amplifier/README.md) | Транзисторный звуковой усилитель с выходным каскадом на тройном эмиттерном повторителе; рассчитаны АЧХ, КНИ и выходная мощность. | [схема PNG](results/001_rogov_triple_ef_amplifier/schematic/rogov_triple_ef_amplifier.png), [netlist](results/001_rogov_triple_ef_amplifier/netlists/variant_02_rogov_triple_ef.cir), [графики](results/001_rogov_triple_ef_amplifier/plots/) |
| [002 RC-фильтр в ngspice](results/002_ngspice_rc_lowpass/README.md) | Простой RC-фильтр нижних частот для проверки локального backend’а ngspice, AC-анализа, transient-анализа и генерации SVG/PNG. | [схема PNG](results/002_ngspice_rc_lowpass/schematic/rc_lowpass.png), [netlist](spice_examples/001_rc_lowpass/rc_lowpass.cir), [графики](results/002_ngspice_rc_lowpass/plots/) |
| [003 RadioStorage shema-1804-6 с вольтодобавкой](results/003_radiostorage_shema_1804_6/README.md) | Однополярный транзисторный усилитель, восстановленный по изображению RadioStorage; оставлен только вариант с вольтодобавкой как рабочая схема. | [HTML-отчет](results/003_radiostorage_shema_1804_6/index.html), [схема PNG](results/003_radiostorage_shema_1804_6/schematic/reconstructed_amplifier_bootstrap.png), [netlist](results/003_radiostorage_shema_1804_6/netlists/radiostorage_amp_bootstrap.cir), [графики](results/003_radiostorage_shema_1804_6/plots/) |

## Локальный порядок работы

Новые схемы и расчеты стоит складывать в `results/NNN_short_name/`. Внутри каждой папки результата нужно держать `README.md`, изображения схемы, графики, данные моделирования, SPICE-netlist’ы и исходные скрипты, которыми можно воспроизвести артефакты. Для простой HTML-страницы результата используйте [scripts/generate_result_html.py](scripts/generate_result_html.py), когда в папке уже есть изображения и Markdown-описание.

Если нужен отдельный HTML-файл из любого Markdown-документа, используйте [scripts/generate_html_from_markdown.py](scripts/generate_html_from_markdown.py):

```powershell
python scripts\generate_html_from_markdown.py results\003_radiostorage_shema_1804_6\README.md --output results\003_radiostorage_shema_1804_6\report.html --title "RadioStorage shema-1804-6 Bootstrap"
```

Для новых вариантов схем лучше использовать общий запускатель, а не держать всю логику в одном локальном скрипте результата. Конкретную топологию, номиналы, отрисовку схемы и набор измерений кладите в `results/NNN_short_name/variants/name.py`; общие SVG-примитивы, запуск ngspice, чтение CSV и построение графиков находятся в [scripts/circuitlib](scripts/circuitlib/). Вариант должен экспортировать `RESULT_DIR` и `run()`. Запуск из корня репозитория:

```powershell
python scripts\run_circuit_result.py results\003_radiostorage_shema_1804_6\variants\bootstrap.py
```

Перед коммитом сгенерированных SVG-схем или файлов условных обозначений запускайте локальный SVG-линтер:

```powershell
npm run lint:svg
```
