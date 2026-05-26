# Оглавления журнала Радио

Эта папка хранит нормализованные CSV-выгрузки статей журнала `Радио`,
полученные из OCR годовых оглавлений.

Формат CSV:

- `year` - год журнала.
- `article_title` - название статьи из OCR-оглавления.
- `issue` - номер журнала.
- `journal_page` - печатная страница журнала из оглавления.
- `archive_image_url` - прямая ссылка на JPG-скан предполагаемой страницы
  статьи на `archive.radio.ru`.
- `archive_image_page` - номер скана, использованный в ссылке.
- `section` - раздел годового оглавления.
- `source_contents_page` - страница декабрьского годового оглавления, откуда
  взята строка.
- `needs_review` - флаги OCR extractor, если строка требует ручной сверки.

Текущие файлы:

- `radio_contents_1990_1995.csv` - статьи из распознанных годовых оглавлений
  за 1990-1995 годы.
- `radio_contents_1995_2000.csv` - статьи из распознанных годовых оглавлений
  за 1995-2000 годы.
- `radio_contents_all.csv` - объединенная таблица всех доступных
  структурированных источников.
- `issue_toc_refinement_report.csv` - отчет уточняющего сопоставления с
  оглавлениями на первых страницах отдельных номеров, если этот шаг запускался.
- `index.html` - статическая таблица из `radio_contents_all.csv` с поиском,
  фильтрами и ссылками на сканы.

Ссылки `archive_image_url` строятся по шаблону прямых JPG-сканов
`https://archive.radio.ru/web/img/<year>/b.<year>-<issue>.<page>.jpg`.
Важная деталь: годовые оглавления дают печатный номер страницы, а сайт в имени
JPG использует номер скана. Эти номера часто совпадают, но в некоторых выпусках
сдвинуты из-за обложек, вклеек или страниц без печатной нумерации. Поэтому
экспортер сначала ищет уже скачанный соседний скан в `.tmp/archive_radio_ru/`,
а если его нет, использует печатную страницу как воспроизводимый guess. Для
строго точных ссылок нужен отдельный map `год/номер/печатная страница -> скан`.

Для дополнительной проверки ссылок есть уточняющий шаг:

```powershell
python scripts\refine_radio_ru_contents_with_issue_toc.py `
  --input study\radio_ru_contents\radio_contents_all.csv `
  --output study\radio_ru_contents\radio_contents_all.csv
```

Он ищет статью в OCR оглавления первых страниц того номера, на который
указывает годовое оглавление. Если найдено уверенное совпадение, скрипт
обновляет `journal_page`, `archive_image_page` и `archive_image_url`, а решение
пишет в `issue_toc_refinement_report.csv`. OCR первых страниц хранится вне Git в
`.tmp/radio_ru_issue_contents_ocr/`. Если OCR еще нет, его можно подготовить тем
же скриптом через существующие загрузчик и OCR-пайплайн проекта:

```powershell
python scripts\refine_radio_ru_contents_with_issue_toc.py --prepare-ocr
```

Для пробного ограниченного прогона:

```powershell
python scripts\refine_radio_ru_contents_with_issue_toc.py --prepare-ocr --prepare-limit 12
```

Альтернативно через npm wrapper:

```powershell
npm run radio:contents-refine
```

Пересобрать CSV можно командой:

```powershell
python scripts\export_radio_ru_contents_index.py
```

Пересобрать HTML-страницу:

```powershell
python scripts\generate_radio_ru_contents_html.py
```

или через npm wrapper:

```powershell
npm run radio:contents-html
```

Если появится новый структурированный CSV годового оглавления, его можно
передать явно:

```powershell
python scripts\export_radio_ru_contents_index.py `
  --input study\radio_ru_annual_contents_1990_1995\radio_annual_contents_1990_1995.csv `
  --input study\radio_ru_annual_contents_1995_2000\radio_annual_contents_1995_2000.csv
```
