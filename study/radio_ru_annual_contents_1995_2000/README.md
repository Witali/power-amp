# Годовые оглавления Радио за 1995-2000 годы

В этой папке лежит OCR-таблица статей журнала `Радио` за 1995-2000 годы,
полученная из декабрьских годовых оглавлений на `archive.radio.ru`.

Страницы годовых оглавлений:

- 1995: `b.1995-12.059` through `b.1995-12.061`
- 1996: `b.1996-12.085` through `b.1996-12.088`
- 1997: `b.1997-12.063` through `b.1997-12.066`
- 1998: `b.1998-12.067` through `b.1998-12.071`
- 1999: `b.1999-12.064` through `b.1999-12.067`
- 2000: `b.2000-12.063` through `b.2000-12.066`

Сгенерированные файлы:

- `radio_annual_contents_1995_2000.csv` - нормализованные записи с разделом,
  типом строки, номером выпуска, страницей, исходной страницей оглавления,
  сырым OCR-текстом и флагами проверки.
- `radio_annual_contents_1995_2000.md` - читаемая Markdown-таблица.
- `radio_annual_contents_1995_2000_raw_ocr.md` - сырые OCR-фрагменты,
  сгруппированные по странице и колонке.

Сводка текущего распознавания:

- Всего записей: 1626
- Строк статей с номером выпуска и страницей: 998
- Строк, отмеченных для ручной проверки: 504

Промежуточные данные хранятся вне Git:

- сканы: `.tmp/archive_radio_ru/<year>/12/`
- поисковый OCR/маркеры: `.tmp/radio_ru_annual_contents_1995_2000/search/`
- OpenCV layout JSON/preview: `.tmp/annual_contents_1995_2000/layout/`
- Tesseract OCR по OpenCV-блокам: `.tmp/annual_contents_1995_2000/layout_ocr/`

Перегенерировать поиск и докачивание страниц можно так:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\search_radio_ru_annual_contents.ps1 `
  -FromYear 2000 `
  -ToYear 1995 `
  -TailPages 32 `
  -OutDir .tmp\radio_ru_annual_contents_1995_2000\search `
  -PageImageCacheRoot .tmp\archive_radio_ru `
  -MaxParallelOcr 8 `
  -TesseractThreadLimit 1 `
  -OcrProfile prose
```

Для страниц оглавления использовался основной OpenCV pipeline:
`ocr_radio_ru_page_columns.ps1 -LayoutOnly`. В этом режиме скрипт сначала
запускает `scripts/detect_page_layout.py`, затем режет OCR-кропы по
горизонтальным `text`/`heading` блокам из `layout.json` и распознает их
локальным Tesseract.

После первичной сборки страницы были перечитаны дополнительным режимом
Tesseract PSM 4. Для структурированной таблицы оставлен PSM 6, потому что он
дал больше извлеченных строк статей; PSM 4 сохранен в `.tmp` как
вспомогательный источник для сверки. Извлекатель также умеет разбирать
склеенные OCR-хвосты номеров вида `169`, `401` и `2 ОЗ`.

Для итоговой таблицы PSM 6 дополнительно преобразуется через Tesseract TSV:
`scripts/rebuild_annual_contents_tsv_text.py` восстанавливает строки по
координатам слов, убирает dot-leader мусор и нормализует правый числовой хвост
строки перед запуском extractor.

После OCR таблица собирается так:

```powershell
python scripts\rebuild_annual_contents_tsv_text.py `
  --ocr-root .tmp\annual_contents_1995_2000\layout_ocr `
  --page-ranges 1995:059-061,1996:085-088,1997:063-066,1998:067-071,1999:064-067,2000:063-066

python scripts\extract_radio_ru_annual_contents.py `
  --ocr-root .tmp\annual_contents_1995_2000\layout_ocr `
  --out-dir study\radio_ru_annual_contents_1995_2000 `
  --page-ranges 1995:059-061,1996:085-088,1997:063-066,1998:067-071,1999:064-067,2000:063-066 `
  --output-prefix radio_annual_contents_1995_2000
```

Таблица является OCR-результатом, а не ручной вычиткой. Строки с флагами в
`needs_review` нужно сверять с исходными сканами или OpenCV preview.
