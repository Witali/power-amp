# Годовые оглавления Радио за 1999-2000 годы

В этой папке лежит таблица статей журнала `Радио` за 1999 и 2000 годы,
полученная из декабрьских годовых оглавлений через OCR.

Исходные сканы взяты из декабрьских номеров на `archive.radio.ru`. Кэш страниц
специально хранится вне Git:

- `.tmp/archive_radio_ru/1999/12/`
- `.tmp/archive_radio_ru/2000/12/`

Страницы годовых оглавлений:

- 1999: `b.1999-12.064` through `b.1999-12.067`
- 2000: `b.2000-12.063` through `b.2000-12.066`

Сгенерированные файлы:

- `radio_annual_contents_1999_2000.csv` - нормализованные записи с разделом,
  типом строки, номером выпуска, страницей, исходным сканом, сырым OCR-текстом
  и флагами проверки.
- `radio_annual_contents_1999_2000.md` - читаемая Markdown-таблица.
- `radio_annual_contents_1999_2000_raw_ocr.md` - сырые OCR-фрагменты,
  сгруппированные по странице и колонке.

Таблица считается полной в практическом смысле: она сохраняет все OCR-строки,
которые относятся к годовому оглавлению после удаления очевидного шума полей.
Часть строк все еще требует ручной проверки, потому что в исходных сканах плотные
колонки, декоративные поля и местами поврежденное распознавание. Такие строки
помечены в колонке `needs_review`, а исходный OCR-фрагмент сохранен в CSV.

Перегенерировать файлы можно так:

```powershell
scripts\ocr_radio_ru_page_columns.ps1 `
  -InputPath .tmp\archive_radio_ru\2000\12\b.2000-12.063.jpg `
  -OutDir .tmp\annual_contents_1999_2000\layout_ocr `
  -LayoutOnly `
  -PsmModes 6 `
  -OcrProfiles prose

python scripts\extract_radio_ru_annual_contents.py `
  --ocr-root .tmp\annual_contents_1999_2000\layout_ocr `
  --out-dir study\radio_ru_annual_contents
```

Для страниц оглавления предпочтительный путь - `ocr_radio_ru_page_columns.ps1 -LayoutOnly`.
В этом режиме скрипт сначала запускает основной OpenCV-детектор
`scripts/detect_page_layout.py`, затем режет OCR-кропы по горизонтальным
блокам `text`/`heading` из `layout.json` и сохраняет их в варианте
`layout_text_blocks`. Старый вариант `columns2` остается запасным входом для
`extract_radio_ru_annual_contents.py`, если layout-кропы еще не созданы.
