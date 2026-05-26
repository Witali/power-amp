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
