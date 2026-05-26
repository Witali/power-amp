# Годовые оглавления Радио за 1990-1995 годы

В этой папке лежит OCR-таблица статей журнала `Радио` за 1990-1995 годы,
полученная из декабрьских годовых оглавлений на `archive.radio.ru`.

Страницы годовых оглавлений:

- 1990: `b.1990-12.084` through `b.1990-12.091`
- 1991: `b.1991-12.083` through `b.1991-12.089`
- 1992: `b.1992-12.054` through `b.1992-12.058`
- 1993: `b.1993-12.043` through `b.1993-12.046`
- 1994: `b.1994-12.047` through `b.1994-12.048`
- 1995: `b.1995-12.059` through `b.1995-12.061`

Сгенерированные файлы:

- `radio_annual_contents_1990_1995.csv` - нормализованные записи с разделом,
  типом строки, номером выпуска, страницей, исходной страницей оглавления,
  сырым OCR-текстом и флагами проверки.
- `radio_annual_contents_1990_1995.md` - читаемая Markdown-таблица.
- `radio_annual_contents_1990_1995_raw_ocr.md` - сырые OCR-фрагменты,
  сгруппированные по странице и колонке.

Сводка текущего распознавания:

- Всего записей: 2133
- Строк статей с номером выпуска и страницей: 1661
- Строк, отмеченных для ручной проверки: 294

Промежуточные данные хранятся вне Git:

- сканы: `.tmp/archive_radio_ru/<year>/12/`
- OpenCV layout JSON/preview: `.tmp/annual_contents_1990_1995/layout/`
- Tesseract OCR по OpenCV-блокам: `.tmp/annual_contents_1990_1995/layout_ocr/`

Для OCR использовался основной OpenCV pipeline:
`ocr_radio_ru_page_columns.ps1 -LayoutOnly`. В этом режиме скрипт запускает
`scripts/detect_page_layout.py`, режет OCR-кропы по горизонтальным
`text`/`heading` блокам из `layout.json` и распознает их локальным Tesseract.

Команда сборки OCR по уже скачанным страницам:

```powershell
$env:PATH = 'C:\Users\rudol\.cache\codex-runtimes\codex-primary-runtime\dependencies\python;' + $env:PATH
$ranges = @(
  @{Year=1990; Start=84; End=91},
  @{Year=1991; Start=83; End=89},
  @{Year=1992; Start=54; End=58},
  @{Year=1993; Start=43; End=46},
  @{Year=1994; Start=47; End=48},
  @{Year=1995; Start=59; End=61}
)
foreach ($range in $ranges) {
  for ($page = $range.Start; $page -le $range.End; $page++) {
    $pageId = '{0:D3}' -f $page
    $year = $range.Year
    .\scripts\ocr_radio_ru_page_columns.ps1 `
      -InputPath ".tmp\archive_radio_ru\$year\12\b.$year-12.$pageId.jpg" `
      -OutDir .tmp\annual_contents_1990_1995\layout_ocr `
      -LayoutOnly `
      -LayoutOutDir .tmp\annual_contents_1990_1995\layout `
      -MaxParallelOcr 8 `
      -TesseractThreadLimit 1 `
      -OcrProfiles prose `
      -PsmModes 6 `
      -NoProgress
  }
}
```

После OCR таблица собирается так:

```powershell
python scripts\extract_radio_ru_annual_contents.py `
  --ocr-root .tmp\annual_contents_1990_1995\layout_ocr `
  --out-dir study\radio_ru_annual_contents_1990_1995 `
  --page-ranges 1990:084-091,1991:083-089,1992:054-058,1993:043-046,1994:047-048,1995:059-061 `
  --output-prefix radio_annual_contents_1990_1995
```

Таблица является OCR-результатом, а не ручной вычиткой. Строки с флагами в
`needs_review` нужно сверять с исходными сканами или OpenCV preview.
